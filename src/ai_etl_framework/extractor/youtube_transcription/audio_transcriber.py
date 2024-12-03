import subprocess
import tempfile
import time

import httpx
import json
import io
from pathlib import Path
from typing import Optional, Dict, List, Tuple
from threading import Lock
from datetime import datetime
import backoff
import asyncio
from concurrent.futures import ThreadPoolExecutor

from ai_etl_framework.common.metrics import CHUNKS_PER_DOCUMENT, BATCH_STATISTICS, ERROR_COUNTER
from ai_etl_framework.config.settings import config
from ai_etl_framework.extractor.models.tasks import TranscriptionTask
from ai_etl_framework.common.logger import setup_logger
from ai_etl_framework.common.minio_service import MinioStorageService

logger = setup_logger(__name__)


class RateLimit:
    """Rate limit tracker."""

    def __init__(self, window_seconds: int, max_requests: int):
        self.window_seconds = window_seconds
        self.max_requests = max_requests
        self.requests: List[datetime] = []
        self.lock = Lock()

    def can_request(self) -> Tuple[bool, float]:
        """Check if request is allowed and return wait time if not."""
        now = datetime.now()
        with self.lock:
            self.requests = [t for t in self.requests
                             if (now - t).total_seconds() < self.window_seconds]

            if len(self.requests) < self.max_requests:
                self.requests.append(now)
                return True, 0

            oldest = self.requests[0]
            wait_time = self.window_seconds - (now - oldest).total_seconds()
            return False, max(0, wait_time)


class AudioTranscriber:
    """Enhanced audio youtube_transcription using Groq API with MinIO storage."""

    def __init__(self):
        self.api_key = config.transcription.api_key
        self.api_url = config.transcription.api_url
        self.model = config.transcription.model
        self.language = config.transcription.language
        self.max_retries = config.download.max_retries
        self.retry_delay = config.download.retry_delay
        self.api_timeout = config.transcription.api_timeout
        self.max_workers = config.worker.max_workers
        self.max_chunk_size = config.transcription.chunk_max_size_bytes

        # Initialize MinIO storage
        self.storage = MinioStorageService()

        # Rate limiting
        self.rate_limiter = RateLimit(
            window_seconds=50,
            max_requests=60
        )

        self.lock = Lock()
        self.executor = ThreadPoolExecutor(max_workers=self.max_workers)

    async def verify_audio(self, audio_data: io.BytesIO) -> Dict:
        """Verify audio data format and get metadata using ffprobe."""
        with tempfile.NamedTemporaryFile(suffix='.wav') as temp_file:
            # Write audio data to temporary file
            temp_file.write(audio_data.getvalue())
            temp_file.flush()

            cmd = [
                'ffprobe',
                '-v', 'quiet',
                '-print_format', 'json',
                '-show_format',
                '-show_streams',
                temp_file.name
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                raise RuntimeError(f"FFprobe failed: {result.stderr}")
            return json.loads(result.stdout)

    async def preprocess_audio(self, audio_data: io.BytesIO, task: TranscriptionTask) -> Optional[io.BytesIO]:
        """Preprocess audio data using ffmpeg."""
        try:
            with tempfile.NamedTemporaryFile(suffix='.wav') as input_file, \
                    tempfile.NamedTemporaryFile(suffix='.mp3') as output_file:

                # Write input audio to temporary file
                input_file.write(audio_data.getvalue())
                input_file.flush()

                # Enhanced FFmpeg settings
                cmd = [
                    'ffmpeg', '-y',
                    '-i', input_file.name,
                    '-vn',
                    '-acodec', 'libmp3lame',
                    '-ar', '16000',
                    '-ac', '1',
                    '-b:a', '128k',
                    '-filter:a', 'volume=1.0,highpass=f=40,lowpass=f=7000',
                    '-map_metadata', '-1',
                    output_file.name
                ]

                result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
                if result.returncode != 0:
                    raise RuntimeError(f"FFmpeg failed: {result.stderr}")

                # Read processed audio into memory
                output_file.seek(0)
                processed_audio = io.BytesIO(output_file.read())

                # Verify the processed audio
                audio_info = await self.verify_audio(processed_audio)
                logger.debug(f"Processed audio info: {audio_info}")

                if processed_audio.getbuffer().nbytes <= self.max_chunk_size:
                    return processed_audio
                else:
                    raise ValueError("Processed audio file too large")

        except Exception as e:
            logger.error(f"Task {task.id}: Audio preprocessing failed: {str(e)}")
            return None

    @backoff.on_exception(
        backoff.expo,
        (httpx.HTTPError, RuntimeError),
        max_tries=3,
        max_time=300
    )
    async def transcribe_chunk_async(self, chunk_path: str, task: TranscriptionTask) -> bool:
        """Async youtube_transcription of audio chunk using MinIO storage."""
        try:
            # Check rate limit
            can_request, wait_time = self.rate_limiter.can_request()
            if not can_request:
                logger.info(f"Rate limit - waiting {wait_time}s")
                await asyncio.sleep(wait_time)

            # Get chunk from MinIO
            chunk_data = await self.storage.get_file(
                task.id,
                "chunks",
                chunk_path
            )

            if not chunk_data:
                raise ValueError(f"Could not retrieve chunk: {chunk_path}")

            # Preprocess audio
            processed_audio = await self.preprocess_audio(chunk_data, task)
            if not processed_audio:
                return False

            headers = {'Authorization': f"Bearer {self.api_key}"}

            async with httpx.AsyncClient() as client:
                files = [
                    ('file', ('audio.mp3', processed_audio, 'application/octet-stream')),
                    ('model', (None, self.model)),
                    ('response_format', (None, 'json'))
                ]

                if self.language:
                    files.append(('language', (None, self.language)))

                response = await client.post(
                    self.api_url,
                    headers=headers,
                    files=files,
                    timeout=self.api_timeout
                )

                if response.status_code == 429:
                    retry_after = int(response.headers.get('Retry-After', self.retry_delay))
                    raise RuntimeError(f"Rate limit exceeded - retry after {retry_after}s")

                response.raise_for_status()
                result = response.json()

                # Save youtube_transcription results to MinIO under 'chunks' folder
                transcription_data = {
                    'youtube_transcription': result,
                    'metadata': {
                        'chunk_path': chunk_path,
                        'processed_at': datetime.now().isoformat(),
                        'model': self.model,
                        'language': result.get('language', self.language),
                        'confidence': result.get('confidence', None)
                    }
                }

                # Save JSON result under 'chunks' folder
                base_name = Path(chunk_path).stem
                await self.storage.save_json(
                    task.id,
                    "chunks",
                    f"{base_name}.json",
                    transcription_data
                )

                # Save text result under 'chunks' folder
                text_content = result.get('text', '')
                text_bytes = io.BytesIO(text_content.encode('utf-8'))
                await self.storage.save_file(
                    task.id,
                    "chunks",
                    text_bytes,
                    f"{base_name}.txt"
                )

                # Update task metadata
                with task._lock:
                    task.transcription_metadata.word_count += len(text_content.split())
                    task.transcription_metadata.detected_language = result.get('language', self.language)
                    if 'confidence' in result:
                        if not hasattr(task.transcription_metadata, 'confidence_scores'):
                            task.transcription_metadata.confidence_scores = []
                        task.transcription_metadata.confidence_scores.append(result['confidence'])

                logger.info(f"Task {task.id}: Transcribed {chunk_path}")
                return True

        except Exception as e:
            logger.error(f"Transcription error: {str(e)}")
            return False

    async def transcribe_chunks_async(self, task: TranscriptionTask) -> bool:
        """Async batch processing of chunks using MinIO storage."""
        try:
            chunks_info = task.metadata.get("chunks_info", {}).get("chunks", [])
            if not chunks_info:
                raise ValueError("No chunks found")

            # Process chunks concurrently
            tasks = []
            for chunk_info in chunks_info:
                chunk_path = chunk_info["relative_path"]
                tasks.append(self.transcribe_chunk_async(chunk_path, task))

            results = await asyncio.gather(*tasks)

            failed_chunks = [
                chunk_info["relative_path"]
                for chunk_info, success in zip(chunks_info, results)
                if not success
            ]

            if failed_chunks:
                task.metadata['failed_chunks'] = failed_chunks
                return False

            return True

        except Exception as e:
            logger.error(f"Task {task.id}: Transcription failed: {str(e)}")
            task.set_error(str(e))
            return False

    async def transcribe_all_chunks(self, task: TranscriptionTask)-> bool:
        """Process all chunks with batch metrics tracking."""
        try:
            chunks_info = task.metadata.get("chunks_info", {}).get("chunks", [])

            # Track chunks per document
            CHUNKS_PER_DOCUMENT.observe(len(chunks_info))

            batch_start_time = time.time()
            results = await self.transcribe_chunks_async(task)

            # Track batch processing statistics
            BATCH_STATISTICS.labels(
                metric_type="processing_time"
            ).observe(time.time() - batch_start_time)

            BATCH_STATISTICS.labels(
                metric_type="batch_size"
            ).observe(len(chunks_info))

            return results

        except Exception as e:
            ERROR_COUNTER.labels(
                error_type="batch_processing_error",
                stage="transcription"
            ).inc()
            return False

    async def merge_transcripts(self, task: TranscriptionTask) -> bool:
        """Merge individual chunk transcriptions using MinIO storage."""
        try:
            # List all chunk youtube_transcription files in 'chunks' folder
            chunk_files = await self.storage.list_files(task.id, "chunks")
            json_files = [f for f in chunk_files if f.endswith('.json')]

            if not json_files:
                raise ValueError("No transcripts found to merge")

            merged_text = []
            merged_metadata = {
                'chunks': [],
                'task_id': task.id,
                'processed_at': datetime.now().isoformat(),
            }

            for json_file in sorted(json_files):
                chunk_data = await self.storage.get_json(
                    task.id,
                    "chunks",
                    Path(json_file).name
                )

                if chunk_data:
                    merged_text.append(chunk_data.get('youtube_transcription', {}).get('text', ''))
                    merged_metadata['chunks'].append(chunk_data.get('metadata', {}))

            # Save merged transcript and metadata to 'transcripts' folder
            merged_text_content = "\n".join(merged_text)
            text_bytes = io.BytesIO(merged_text_content.encode('utf-8'))

            await self.storage.save_file(
                task.id,
                "transcripts",
                text_bytes,
                "merged_transcript.txt"
            )

            await self.storage.save_json(
                task.id,
                "transcripts",
                "merged_metadata.json",
                merged_metadata
            )

            logger.info(f"Task {task.id}: Successfully merged transcripts")
            return True

        except Exception as e:
            logger.error(f"Task {task.id}: Failed to merge transcripts: {str(e)}")
            return False
    async def merge_transcripts_async(self, task: TranscriptionTask) -> bool:
        """Asynchronous wrapper for transcript merging."""
        return await self.merge_transcripts(task)
