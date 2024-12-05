import subprocess
import tempfile
from pathlib import Path
import json
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import math
import io

from ai_etl_framework.extractor.models.tasks import TranscriptionTask
from ai_etl_framework.common.logger import setup_logger
from ai_etl_framework.config.settings import config
from ai_etl_framework.common.minio_service import MinioStorageService

logger = setup_logger(__name__)


class AudioSplitter:
    """Splits audio files into smaller chunks using ffmpeg, storing in MinIO."""

    def __init__(self):
        """Initialize AudioSplitter with configuration and MinIO storage."""
        self.chunk_max_size_bytes = config.transcription.chunk_max_size_bytes
        self.chunk_duration_sec = config.transcription.chunk_duration_sec
        self.audio_format = config.transcription.audio_format
        self.sample_rate = config.transcription.audio_settings.sample_rate
        self.channels = config.transcription.audio_settings.channels
        self.storage = MinioStorageService()

    async def get_audio_duration(self, audio_data: io.BytesIO) -> Optional[float]:
        """Get the duration of audio data using ffprobe."""
        try:
            with tempfile.NamedTemporaryFile(suffix='.wav') as temp_file:
                temp_file.write(audio_data.getvalue())
                temp_file.flush()

                cmd = [
                    'ffprobe',
                    '-v', 'error',
                    '-show_entries', 'format=duration',
                    '-of', 'default=noprint_wrappers=1:nokey=1',
                    temp_file.name
                ]

                result = subprocess.run(cmd, capture_output=True, text=True, check=True)
                duration_str = result.stdout.strip()
                logger.debug(f"Duration output from ffprobe: {duration_str}")

                if duration_str == 'N/A' or not duration_str:
                    raise ValueError("Duration not available")

                return float(duration_str)

        except Exception as e:
            logger.error(f"Error getting audio duration: {str(e)}")
            return None

    async def split_audio(self, task: TranscriptionTask) -> Optional[List[Dict]]:
        """Split audio file into chunks and store in MinIO."""
        try:
            if not task.temp_video_path:
                raise ValueError("No audio file path specified")

            # Get audio file from MinIO
            audio_data = await self.storage.get_file(
                task.id,
                "audio",
                Path(task.temp_video_path).name
            )

            if not audio_data:
                error_msg = "Audio file not found in storage"
                logger.error(error_msg)
                task.add_error(error_msg)
                return None

            # Get audio duration
            total_duration = await self.get_audio_duration(audio_data)
            if total_duration is None:
                error_msg = "Failed to get audio duration"
                logger.error(error_msg)
                task.add_error(error_msg)
                return None

            with task.atomic() as t:
                t.metadata.processing['total_duration'] = total_duration
                t.metadata.transcription.total_duration = total_duration

            # Calculate number of chunks
            chunk_duration = task.metadata.processing.get('chunk_duration', self.chunk_duration_sec)
            num_chunks = max(1, math.ceil(total_duration / chunk_duration))
            logger.info(f"Splitting audio into {num_chunks} chunks of {chunk_duration} seconds")

            chunks_info = []

            # Process each chunk
            for i in range(num_chunks):
                start_time = i * chunk_duration
                end_time = min((i + 1) * chunk_duration, total_duration)
                duration = end_time - start_time

                # Format timestamps for filename
                start_timestamp = self.format_timestamp_for_filename(start_time)
                end_timestamp = self.format_timestamp_for_filename(end_time)
                chunk_filename = f"chunk_{i:03d}_{start_timestamp}_{end_timestamp}.{self.audio_format}"

                # Create chunk using ffmpeg
                chunk_data = await self.create_chunk(
                    audio_data,
                    start_time,
                    duration
                )

                if not chunk_data:
                    error_msg = f"Failed to create chunk {i}"
                    logger.error(error_msg)
                    task.add_error(error_msg)
                    continue

                # Save chunk to MinIO
                await self.storage.save_file(
                    task.id,
                    "chunks",
                    chunk_data,
                    chunk_filename,
                    metadata={
                        'content-type': f'audio/{self.audio_format}',
                        'chunk-index': str(i)
                    }
                )

                # Create chunk metadata
                chunk_info = self.create_chunk_metadata(
                    chunk_filename,
                    start_time * 1000,
                    end_time * 1000,
                    i
                )
                chunks_info.append(chunk_info)

                # Update progress
                progress = min((i + 1) / num_chunks * 100, 99.9)
                task.update_progress(progress)

                logger.info(f"Created and uploaded chunk {i + 1}/{num_chunks}")

            if not chunks_info:
                error_msg = "No chunks were created during audio splitting"
                logger.error(error_msg)
                task.add_error(error_msg)
                return None

            # Create and save manifest
            manifest = {
                "total_chunks": len(chunks_info),
                "total_duration_ms": total_duration * 1000,
                "chunk_duration": chunk_duration,
                "audio_format": self.audio_format,
                "sample_rate": self.sample_rate,
                "channels": self.channels,
                "chunks": chunks_info,
                "created_at": datetime.now().isoformat()
            }

            await self.storage.save_json(
                task.id,
                "chunks",
                "chunks_manifest.json",
                manifest
            )

            with task.atomic() as t:
                t.metadata.processing['chunks_info'] = manifest
                t.metadata.transcription.chunk_count = len(chunks_info)

            logger.info(f"Successfully split audio into {len(chunks_info)} chunks")
            return chunks_info

        except Exception as e:
            error_msg = f"Error splitting audio: {str(e)}"
            logger.exception(f"Task {task.id}: {error_msg}")
            task.add_error(error_msg)
            return None

    async def create_chunk(self, audio_data: io.BytesIO, start_time: float, duration: float) -> Optional[io.BytesIO]:
        """Create an audio chunk using ffmpeg."""
        try:
            with tempfile.NamedTemporaryFile(suffix='.wav') as input_file, \
                    tempfile.NamedTemporaryFile(suffix=f'.{self.audio_format}') as output_file:

                input_file.write(audio_data.getvalue())
                input_file.flush()

                cmd = [
                    'ffmpeg', '-y',
                    '-i', input_file.name,
                    '-ss', str(start_time),
                    '-t', str(duration),
                    '-ar', str(self.sample_rate),
                    '-ac', str(self.channels),
                    '-map', '0:a',
                    output_file.name
                ]

                result = subprocess.run(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )

                if result.returncode != 0:
                    logger.error(f"FFmpeg error: {result.stderr}")
                    return None

                with open(output_file.name, 'rb') as f:
                    return io.BytesIO(f.read())

        except Exception as e:
            logger.error(f"Error creating chunk: {str(e)}")
            return None

    def format_timestamp_for_filename(self, seconds: float) -> str:
        """Convert seconds to a filename-safe formatted timestamp."""
        try:
            time = timedelta(seconds=seconds)
            total_seconds = int(time.total_seconds())
            hours, remainder = divmod(total_seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            milliseconds = int((time.total_seconds() - total_seconds) * 1000)
            return f"{hours:02d}_{minutes:02d}_{seconds:02d}_{milliseconds:03d}"
        except Exception as e:
            logger.exception(f"Error formatting timestamp for {seconds}s: {e}")
            return "00_00_00_000"

    def create_chunk_metadata(self, chunk_filename: str, start_ms: float,
                              end_ms: float, chunk_index: int) -> Dict:
        """Create metadata for an audio chunk."""
        try:
            metadata = {
                "chunk_index": chunk_index,
                "filename": chunk_filename,
                "relative_path": chunk_filename,
                "start_time": self.format_timestamp_for_metadata(start_ms),
                "end_time": self.format_timestamp_for_metadata(end_ms),
                "duration_ms": end_ms - start_ms,
                "start_ms": start_ms,
                "end_ms": end_ms,
                "audio_format": self.audio_format,
                "sample_rate": self.sample_rate,
                "channels": self.channels,
                "created_at": datetime.now().isoformat()
            }
            logger.debug(f"Created metadata for chunk {chunk_index}: {metadata}")
            return metadata
        except Exception as e:
            logger.exception(f"Error creating metadata for chunk {chunk_index}: {e}")
            return {}

    def format_timestamp_for_metadata(self, ms: float) -> str:
        """Convert milliseconds to a formatted timestamp for metadata display."""
        try:
            time = timedelta(milliseconds=ms)
            total_seconds = int(time.total_seconds())
            hours, remainder = divmod(total_seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            milliseconds = int(ms % 1000)
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}.{milliseconds:03d}"
        except Exception as e:
            logger.exception(f"Error formatting timestamp for {ms}ms: {e}")
            return "00:00:00.000"