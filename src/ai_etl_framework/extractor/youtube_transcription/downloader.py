from __future__ import annotations

import asyncio
from pathlib import Path
from datetime import datetime
import yt_dlp
import io
import re
import unicodedata
import tempfile
import shutil
from typing import Dict, Optional, Tuple, BinaryIO

from ai_etl_framework.extractor.models.tasks import TranscriptionTask, TaskStatus
from ai_etl_framework.config.settings import config
from ai_etl_framework.common.logger import setup_logger
from ai_etl_framework.common.minio_service import MinioStorageService

logger = setup_logger(__name__)


class VideoDownloader:
    """Handles downloading of videos and extraction of metadata using yt-dlp with MinIO storage."""

    def __init__(self):
        """Initialize the VideoDownloader with MinIO storage configuration."""
        self.max_retries = config.download.max_retries
        self.retry_delay = config.download.retry_delay
        self.download_timeout = config.download.timeout
        self.verify_timeout = config.download.verify_timeout
        self.storage = MinioStorageService()

    def sanitize_filename(self, filename: str) -> str:
        """Create a clean, storage-safe filename."""
        if not filename:
            return "untitled"

        filename = unicodedata.normalize('NFKD', filename)
        filename = filename.encode('ASCII', 'ignore').decode()
        filename = re.sub(r'[^\w\s-]', '', filename)
        filename = re.sub(r'[-\s]+', '-', filename).strip('-')

        if len(filename) > 100:
            filename = filename[:100]

        return filename.lower() or "untitled"

    async def save_metadata(self, task: TranscriptionTask, info: Dict) -> None:
        """Save video metadata to MinIO storage."""
        try:
            # Update task's video metadata
            with task.atomic() as t:
                t.metadata.video.title = info.get('title', '')
                t.metadata.video.description = info.get('description')
                t.metadata.video.duration = info.get('duration')
                t.metadata.video.upload_date = info.get('upload_date')
                t.metadata.video.uploader = info.get('uploader')
                t.metadata.video.channel_id = info.get('channel_id')
                t.metadata.video.view_count = info.get('view_count')
                t.metadata.video.like_count = info.get('like_count')
                t.metadata.video.comment_count = info.get('comment_count')
                t.metadata.video.tags = info.get('tags', [])
                t.metadata.video.categories = info.get('categories', [])
                t.metadata.video.language = info.get('language')
                t.metadata.video.format_id = info.get('format_id')
                t.metadata.video.ext = info.get('ext')
                t.metadata.video.audio_channels = info.get('audio_channels')
                t.metadata.video.filesize_approx = info.get('filesize_approx')
                t.metadata.video.duration_string = info.get('duration_string')
                t.metadata.video.processed_title = self.sanitize_filename(info.get('title', ''))

                # Add additional processing metadata
                t.metadata.processing.update({
                    'automatic_captions': bool(info.get('automatic_captions')),
                    'subtitles': bool(info.get('subtitles')),
                    'video_url': info.get('webpage_url'),
                    'download_started_at': datetime.now().isoformat()
                })

            # Save complete metadata to MinIO for reference
            await self.storage.save_json(
                task.id,
                "metadata",
                "video_metadata.json",
                info
            )
            logger.info(f"Task {task.id}: Metadata saved to MinIO")

        except Exception as e:
            error_msg = f"Failed to save metadata: {str(e)}"
            logger.error(f"Task {task.id}: {error_msg}")
            task.add_error(error_msg)
            raise

    def verify_wav_file(self, wav_data: BinaryIO) -> bool:
        """Verify that the WAV data is valid."""
        try:
            header = wav_data.read(44)  # WAV header is 44 bytes
            wav_data.seek(0)  # Reset position
            return len(header) == 44 and header.startswith(b'RIFF') and b'WAVE' in header
        except Exception as e:
            logger.error(f"Error verifying WAV data: {str(e)}")
            return False

    def _create_progress_hook(self, task: TranscriptionTask):
        """Create a progress hook closure for tracking download progress."""

        def progress_hook(d):
            try:
                if d['status'] == 'downloading':
                    total = d.get('total_bytes', 0) or d.get('total_bytes_estimate', 0)
                    downloaded = d.get('downloaded_bytes', 0)
                    speed = d.get('speed', 0)

                    with task.atomic() as t:
                        t.stats.total_bytes = total
                        t.stats.downloaded_bytes = downloaded
                        t.stats.speed = speed

                        if total > 0:
                            progress = (downloaded / total) * 100
                            t.update_progress(progress)

                            # Update processing metadata
                            t.metadata.processing.update({
                                'download_speed': f"{speed / 1024 / 1024:.2f} MB/s" if speed else "N/A",
                                'downloaded_size': f"{downloaded / 1024 / 1024:.1f}MB",
                                'total_size': f"{total / 1024 / 1024:.1f}MB",
                                'total_size_bytes': total  # Store raw value for metrics
                            })

                elif d['status'] == 'finished':
                    with task.atomic() as t:
                        t.update_progress(100.0)
                        t.metadata.download_completed_at = datetime.now()
                        if filename := d.get('filename', ''):
                            logger.debug(f"Finished downloading file: {filename}")
                            t.metadata.processing['downloaded_filename'] = filename

            except Exception as e:
                error_msg = f"Error in progress hook: {str(e)}"
                logger.error(f"Task {task.id}: {error_msg}")
                task.add_error(error_msg)

        return progress_hook

    def _prepare_download_options(self, temp_dir: str, task: TranscriptionTask) -> Dict:
        """Prepare yt-dlp options with progress tracking."""
        output_template = str(Path(temp_dir) / "%(id)s.%(ext)s")

        return {
            'format': 'bestaudio/best',
            'outtmpl': output_template,
            'progress_hooks': [self._create_progress_hook(task)],
            'quiet': True,
            'noplaylist': True,
            'extract_flat': False,
            'writesubtitles': False,
            'writeautomaticsub': False,
            'retries': self.max_retries,
            'retry_sleep': self.retry_delay,
            'socket_timeout': self.download_timeout,
            'fragment_retries': 10,
            'extractor_retries': 5,
            'file_access_retries': 5,
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'wav',
                'preferredquality': '192',
                'nopostoverwrites': False,
            }],
            'postprocessor_args': [
                '-af', 'aformat=sample_fmts=s16:sample_rates=16000:channel_layouts=mono',
            ],
        }

    async def download_video(self, task: TranscriptionTask) -> Tuple[bool, Optional[str]]:
        """Download video and extract audio using MinIO storage."""
        logger.info(f"Task {task.id}: Starting download for URL: {task.url}")
        temp_dir = None

        try:
            if not task.url or not task.url.strip():
                raise ValueError("Invalid or empty URL")

            # Extract video info first
            with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
                try:
                    info = ydl.extract_info(task.url, download=False)
                except Exception as e:
                    raise RuntimeError(f"Failed to fetch video info: {str(e)}")

            if not (video_id := info.get('id')):
                raise ValueError("Could not retrieve video ID")

            # Save metadata to MinIO
            await self.save_metadata(task, info)

            # Create temporary directory and prepare options
            temp_dir = tempfile.mkdtemp()
            ydl_opts = self._prepare_download_options(temp_dir, task)

            # Download with retry logic
            download_success = False
            error_msg = None
            for attempt in range(self.max_retries):
                try:
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        ydl.download([task.url])
                    download_success = True
                    break
                except Exception as e:
                    error_msg = str(e)
                    logger.warning(f"Download attempt {attempt + 1} failed: {error_msg}")
                    if attempt < self.max_retries - 1:
                        await asyncio.sleep(self.retry_delay)

            if not download_success:
                raise RuntimeError(f"Failed to download after {self.max_retries} attempts: {error_msg}")

            # Find and verify the WAV file
            wav_files = list(Path(temp_dir).glob("*.wav"))
            if not wav_files:
                raise FileNotFoundError("WAV file not found after download and conversion")

            wav_path = wav_files[0]
            if not wav_path.exists():
                raise FileNotFoundError("WAV file does not exist after conversion")

            # Read and verify the WAV file
            with open(wav_path, 'rb') as f:
                wav_data = io.BytesIO(f.read())

            if not self.verify_wav_file(wav_data):
                raise ValueError("Failed to verify WAV file")

            # Upload to MinIO
            wav_filename = f"{video_id}.wav"
            wav_data.seek(0)
            await self.storage.save_file(
                task.id,
                "audio",
                wav_data,
                wav_filename,
                metadata={'content-type': 'audio/wav'}
            )

            # Update task metadata
            with task.atomic() as t:
                t.temp_video_path = f"{task.id}/audio/{wav_filename}"
                t.metadata.processing['audio_path'] = t.temp_video_path

            logger.info(f"Task {task.id}: Audio file uploaded to MinIO")
            return True, None

        except Exception as e:
            error_msg = str(e)
            logger.exception(f"Task {task.id}: {error_msg}")
            task.add_error(error_msg)
            return False, error_msg

        finally:
            # Clean up temporary directory
            if temp_dir and Path(temp_dir).exists():
                try:
                    shutil.rmtree(temp_dir)
                except Exception as e:
                    logger.error(f"Error cleaning up temp directory: {e}")

    async def cleanup_task(self, task: TranscriptionTask) -> None:
        """Clean up any temporary files for a task in MinIO storage."""
        try:
            temp_files = await self.storage.list_files(task.id, "temp")
            for temp_file in temp_files:
                await self.storage.delete_file(task.id, "temp", temp_file)
            logger.info(f"Task {task.id}: Temporary files cleaned up")
        except Exception as e:
            error_msg = f"Error cleaning up temporary files: {str(e)}"
            logger.error(f"Task {task.id}: {error_msg}")
            task.add_error(error_msg)