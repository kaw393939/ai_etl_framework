from pathlib import Path

from ai_etl_framework.config.settings import (
    Environment,
    ServiceConfig,
    DirectoryConfig,
    AppConfig,
    MinIOConfig, TranscriptionConfig, DownloadConfig, LoggingConfig, WorkerConfig
)

from unittest.mock import patch, MagicMock, AsyncMock

from prometheus_client import CollectorRegistry, Counter, Histogram, Gauge
from fastapi.testclient import TestClient





import pytest
import asyncio
from typing import Generator, Dict
from ai_etl_framework.common.minio_service import MinioStorageService
from ai_etl_framework.config.settings import config
from minio import Minio
import httpx


@pytest.fixture(scope="function")
def mock_groq_api(mocker):
    """Mock only the Groq API calls."""
    mock_response = {
        "text": "This is a test transcription result that will be saved to MinIO.",
        "language": "en",
        "confidence": 0.95,
        "segments": [
            {
                "start": 0,
                "end": 3.2,
                "text": "This is a test transcription result."
            }
        ]
    }

    # Create a synchronous mock response object
    async def mock_post(*args, **kwargs):
        class MockResponse:
            status_code = 200

            def raise_for_status(self):
                pass

            # Make this a regular method, not an async method
            def json(self):
                return mock_response

        return MockResponse()

    # Patch the httpx client post
    mocker.patch('httpx.AsyncClient.post', side_effect=mock_post)
@pytest.fixture(scope="session")
def test_video_url():
    """A real, short YouTube video URL for testing."""
    # Choose a very short (5-10 second) Creative Commons video
    return "https://www.youtube.com/watch?v=3RoDXg2rAkY"


@pytest.fixture(scope="function")
async def test_minio():
    """Setup MinIO connection for testing."""
    # Use the actual MinIO service - no mocking
    minio_service = MinioStorageService()
    return minio_service

@pytest.fixture
def test_service_config() -> ServiceConfig:
    """Create test service configuration"""
    return ServiceConfig(
        environment=Environment.TEST,
        debug=True,
        app_title="Transcription Service API",
        app_description="Service to process and transcribe audio/video content.",
        app_version="1.0.0",
        app_host="localhost",
        app_port=8000
    )




@pytest.fixture
def test_directory_config(tmp_path: Path) -> DirectoryConfig:
    """Create test directory configuration using temporary path."""
    return DirectoryConfig(
        base_dir=tmp_path,
        temp_dir=tmp_path / "temp",
        downloaded_videos_dir=tmp_path / "downloaded_videos",
        output_dir=tmp_path / "transcripts",
        logs_dir=tmp_path / "logs"
    )


@pytest.fixture
def test_service_config() -> ServiceConfig:
    """Create test service configuration."""
    return ServiceConfig(
        environment=Environment.TEST,
        debug=True,
        minio_root_user="test_user",
        minio_root_password="test_password",
        minio_endpoint="localhost:9001",
        grafana_admin_user="test_admin",
        grafana_admin_password="test_admin_pass",
        grafana_port=3001,
        prometheus_port=9091,
        app_title="Test Transcription API",
        app_description="Test Service",
        app_version="0.0.1",
        app_host="127.0.0.1",
        app_port=8001
    )


@pytest.fixture
def test_minio_config() -> MinIOConfig:
    """Create test MinIO configuration."""
    storage_paths: Dict[str, str] = {
        "audio": "test_audio",
        "chunks": "test_chunks",
        "transcripts": "test_transcripts",
        "metadata": "test_metadata",
        "temp": "test_temp"
    }

    return MinIOConfig(
        endpoint="minio:9000",
        access_key="test_access_key",
        secret_key="test_secret_key",
        bucket="test-bucket",
        secure=False,
        storage_paths=storage_paths
    )
@pytest.fixture
def test_app_config(
        test_directory_config: DirectoryConfig,
        test_service_config: ServiceConfig,
        test_minio_config: MinIOConfig,
) -> AppConfig:
    """Create complete test application configuration"""
    return AppConfig(
        directory=test_directory_config,
        service=test_service_config,
        minio=test_minio_config,
        transcription=TranscriptionConfig(
            api_key="test_api_key",
            api_url="http://test-api-url",
            model="test-model"
        ),
        worker=WorkerConfig(max_workers=2, max_queue_size=10),
        logging=LoggingConfig(level="DEBUG"),
        download=DownloadConfig(max_retries=1, retry_delay=1)
    )

@pytest.fixture
def clean_registry():
    """Provide a clean Prometheus registry for each test."""
    registry = CollectorRegistry()
    Counter('transcription_service_requests_total', 'Total requests', ['endpoint'], registry=registry)
    Histogram('transcription_service_duration_seconds', 'Request duration', ['endpoint'], registry=registry)
    Gauge('transcription_service_memory_usage_bytes', 'Memory usage', registry=registry)
    Gauge('transcription_service_disk_usage_bytes', 'Disk usage', registry=registry)
    Gauge('transcription_service_cpu_usage_percent', 'CPU usage', registry=registry)
    Counter('transcription_service_errors_total', 'Processing errors', ['endpoint'], registry=registry)
    yield registry

@pytest.fixture
def app_client(clean_registry, test_app_config):
    """Create a TestClient with properly mocked dependencies"""
    with patch('ai_etl_framework.config.settings.config', test_app_config), \
            patch('prometheus_client.REGISTRY', clean_registry), \
            patch('ai_etl_framework.extractor.app.TranscriptionService') as mock_transcription_service:
        import ai_etl_framework.extractor.app
        import importlib
        importlib.reload(ai_etl_framework.extractor.app)
        from ai_etl_framework.extractor.app import app

        mock_service = MagicMock()
        mock_transcription_service.return_value = mock_service

        client = TestClient(app)
        client.mock_transcription_service = mock_service
        yield client