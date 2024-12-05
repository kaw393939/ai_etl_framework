import pytest
import asyncio
import time
from pathlib import Path

from ai_etl_framework.extractor.youtube_transcription.manager import TranscriptionManager
from ai_etl_framework.extractor.models.tasks import TaskStatus
from ai_etl_framework.common.minio_service import MinioStorageService
from ai_etl_framework.config.settings import config


@pytest.fixture(scope="session")
def storage_service():
    return MinioStorageService()


@pytest.mark.integration
class TestTranscriptionIntegration:
    @pytest.mark.asyncio
    async def test_full_transcription_pipeline(self, test_video_url, mock_groq_api, storage_service):
        """Test the complete transcription pipeline with real services."""
        manager = TranscriptionManager()

        # Add task using real YouTube URL
        task = manager.add_task(test_video_url)
        assert task is not None

        # Wait for processing to complete
        max_wait = 300  # 5 minutes
        start_time = time.time()

        while time.time() - start_time < max_wait:
            if task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED]:
                if task.status == TaskStatus.FAILED:
                    print(f"Task failed with error: {task.latest_error}")
                break
            await asyncio.sleep(1)

        assert task.status == TaskStatus.COMPLETED
        assert task.latest_error is None

        # Verify the pipeline results
        assert task.metadata.video.title is not None
        assert task.metadata.processing.get('chunks_info') is not None

        # Verify files in MinIO
        files = await storage_service.list_files(task.id, "transcripts")
        assert len(files) > 0

        # Verify chunks exist
        chunk_files = await storage_service.list_files(task.id, "chunks")
        assert len(chunk_files) > 0

    @pytest.mark.asyncio
    async def test_error_handling(self, mock_groq_api):
        """Test error handling with invalid video URL."""
        manager = TranscriptionManager()

        task = manager.add_task("https://www.youtube.com/watch?v=invalid_video_id")
        assert task is not None

        # Wait for processing to fail
        max_wait = 60
        start_time = time.time()

        while time.time() - start_time < max_wait:
            if task.status == TaskStatus.FAILED:
                break
            await asyncio.sleep(1)

        assert task.status == TaskStatus.FAILED
        assert task.latest_error is not None


@pytest.mark.integration
class TestComponentIntegration:
    @pytest.mark.asyncio
    async def test_download_and_split(self, test_video_url, storage_service):
        """Test real video download and splitting."""
        manager = TranscriptionManager()
        task = manager.add_task(test_video_url)

        # Wait for download and split
        max_wait = 120
        start_time = time.time()

        while time.time() - start_time < max_wait:
            if task.status in [TaskStatus.TRANSCRIBING, TaskStatus.FAILED]:
                if task.status == TaskStatus.FAILED:
                    print(f"Task failed with error: {task.latest_error}")
                break
            await asyncio.sleep(1)

        assert task.status == TaskStatus.TRANSCRIBING
        assert task.metadata.video.title is not None
        assert task.metadata.processing.get('chunks_info') is not None

        # Verify chunks exist in MinIO
        chunks = task.metadata.processing['chunks_info']['chunks']
        assert len(chunks) > 0

        for chunk in chunks:
            exists = await storage_service.get_file(
                task.id,
                "chunks",
                chunk['relative_path']
            )
            assert exists is not None

    @pytest.mark.asyncio
    async def test_transcription_and_merge(self, test_video_url, mock_groq_api, storage_service):
        """Test transcription and merging with real files."""
        manager = TranscriptionManager()
        task = manager.add_task(test_video_url)

        # Wait for completion
        max_wait = 300
        start_time = time.time()

        while time.time() - start_time < max_wait:
            if task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED]:
                if task.status == TaskStatus.FAILED:
                    print(f"Task failed with error: {task.latest_error}")
                break
            await asyncio.sleep(1)

        assert task.status == TaskStatus.COMPLETED

        # Verify transcription results
        assert task.metadata.transcription.word_count > 0
        assert task.metadata.transcription.detected_language is not None

        # Verify files in MinIO
        transcript_files = await storage_service.list_files(task.id, "transcripts")
        assert len(transcript_files) > 0