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
from ai_etl_framework.extractor.models.tasks import TranscriptionTask, TaskStatus
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
    """Enhanced audio transcription using API with MinIO storage."""

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

        self.storage = MinioStorageService()
        self.rate_limiter = RateLimit(window_seconds=50, max_requests=60)
        self.executor = ThreadPoolExecutor(max_workers=self.max_workers)

    async def verify_audio(self, audio_data: io.BytesIO) -> Dict:
        """Verify audio data format and get metadata using ffprobe."""
        with tempfile.NamedTemporaryFile(suffix='.wav') as temp_file:
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

                input_file.write(audio_data.getvalue())
                input_file.flush()

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

                output_file.seek(0)
                processed_audio = io.BytesIO(output_file.read())

                audio_info = await self.verify_audio(processed_audio)
                logger.debug(f"Processed audio info: {audio_info}")

                if processed_audio.getbuffer().nbytes <= self.max_chunk_size:
                    return processed_audio
                else:
                    raise ValueError("Processed audio file too large")

        except Exception as e:
            error_msg = f"Audio preprocessing failed: {str(e)}"
            logger.error(f"Task {task.id}: {error_msg}")
            task.add_error(error_msg)
            return None

    @backoff.on_exception(
        backoff.expo,
        (httpx.HTTPError, RuntimeError),
        max_tries=3,
        max_time=300
    )
    async def transcribe_chunk_async(self, chunk_path: str, task: TranscriptionTask) -> bool:
        """Async transcription of audio chunk using MinIO storage."""
        try:
            can_request, wait_time = self.rate_limiter.can_request()
            if not can_request:
                logger.info(f"Rate limit - waiting {wait_time}s")
                await asyncio.sleep(wait_time)

            chunk_data = await self.storage.get_file(
                task.id,
                "chunks",
                chunk_path
            )

            if not chunk_data:
                raise ValueError(f"Could not retrieve chunk: {chunk_path}")

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

                transcription_data = {
                    'transcription': result,
                    'metadata': {
                        'chunk_path': chunk_path,
                        'processed_at': datetime.now().isoformat(),
                        'model': self.model,
                        'language': result.get('language', self.language),
                        'confidence': result.get('confidence', None)
                    }
                }

                base_name = Path(chunk_path).stem
                await self.storage.save_json(
                    task.id,
                    "chunks",
                    f"{base_name}.json",
                    transcription_data
                )

                text_content = result.get('text', '')
                text_bytes = io.BytesIO(text_content.encode('utf-8'))
                await self.storage.save_file(
                    task.id,
                    "chunks",
                    text_bytes,
                    f"{base_name}.txt"
                )

                with task.atomic() as t:
                    t.metadata.transcription.word_count = (t.metadata.transcription.word_count or 0) + len(
                        text_content.split())
                    t.metadata.transcription.detected_language = result.get('language', self.language)
                    if 'confidence' in result:
                        t.metadata.transcription.confidence_scores.append(result['confidence'])
                        # Update average confidence
                        scores = t.metadata.transcription.confidence_scores
                        t.metadata.transcription.average_confidence = sum(scores) / len(scores)

                logger.info(f"Task {task.id}: Transcribed {chunk_path}")
                return True

        except Exception as e:
            error_msg = f"Transcription error: {str(e)}"
            logger.error(error_msg)
            task.add_error(error_msg)
            return False

    async def transcribe_chunks_async(self, task: TranscriptionTask) -> bool:
        try:
            chunks_info = task.metadata.processing.get("chunks_info", {}).get("chunks", [])
            if not chunks_info:
                raise ValueError("No chunks found")

            batch_size = 5
            total_chunks = len(chunks_info)
            failed_chunks = []
            error_messages = []
            ordered_results = []

            for i in range(0, total_chunks, batch_size):
                batch = chunks_info[i:i + batch_size]
                batch_tasks = []

                for chunk_info in batch:
                    chunk_path = chunk_info["relative_path"]
                    batch_tasks.append((chunk_info, self.transcribe_chunk_async(chunk_path, task)))

                for chunk_info, task_coroutine in batch_tasks:
                    try:
                        result = await task_coroutine
                        ordered_results.append((chunk_info["relative_path"], result))
                        if not result:
                            failed_chunks.append(chunk_info["relative_path"])
                    except Exception as e:
                        error_msg = f"Chunk {chunk_info['relative_path']}: {str(e)}"
                        error_messages.append(error_msg)
                        failed_chunks.append(chunk_info["relative_path"])

                progress = min(((i + len(batch)) / total_chunks) * 100, 99.9)
                task.update_progress(progress)

                if i + batch_size < total_chunks:
                    await asyncio.sleep(1)

            if failed_chunks:
                error_msg = f"Failed to transcribe chunks: {', '.join(error_messages)}"
                task.add_error(error_msg)
                task.metadata.processing.update({
                    'failed_chunks': failed_chunks,
                    'ordered_results': ordered_results
                })
                return False

            task.metadata.processing['ordered_results'] = ordered_results
            return True

        except Exception as e:
            error_msg = f"Task {task.id}: Transcription failed: {str(e)}"
            logger.error(error_msg)
            task.add_error(error_msg)
            task.metadata.processing['failed_chunks'] = task.metadata.processing.get('failed_chunks', [])
            return False

    async def transcribe_all_chunks(self, task: TranscriptionTask) -> bool:
        """Process all chunks with batch metrics tracking."""
        try:
            chunks_info = task.metadata.processing.get("chunks_info", {}).get("chunks", [])
            CHUNKS_PER_DOCUMENT.observe(len(chunks_info))

            batch_start_time = time.time()
            results = await self.transcribe_chunks_async(task)

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
            error_msg = f"Batch processing error: {str(e)}"
            task.add_error(error_msg)
            return False

    async def merge_transcripts(self, task: TranscriptionTask) -> bool:
        """Merge individual chunk transcriptions using MinIO storage."""
        try:
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
                    merged_text.append(chunk_data.get('transcription', {}).get('text', ''))
                    merged_metadata['chunks'].append(chunk_data.get('metadata', {}))

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

            with task.atomic() as t:
                t.metadata.transcription.merged_transcript_path = f"{task.id}/transcripts/merged_transcript.txt"

            logger.info(f"Task {task.id}: Successfully merged transcripts")
            return True

        except Exception as e:
            error_msg = f"Failed to merge transcripts: {str(e)}"
            logger.error(f"Task {task.id}: {error_msg}")
            task.add_error(error_msg)
            return False

    async def merge_transcripts_async(self, task: TranscriptionTask) -> bool:
        """Asynchronous wrapper for transcript merging."""
        return await self.merge_transcripts(task)