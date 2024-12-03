import pytest
from pathlib import Path
from ai_etl_framework.config.settings import (
    Environment,
    ServiceConfig,
    DirectoryConfig,
    AppConfig,
    MinIOConfig, TranscriptionConfig, DownloadConfig, LoggingConfig, WorkerConfig
)
import sys
from pathlib import Path

from unittest.mock import patch, MagicMock
import pytest
from prometheus_client import CollectorRegistry, Counter, Histogram, Gauge
from fastapi.testclient import TestClient
@pytest.fixture
def test_base_dir(tmp_path: Path) -> Path:
    """Create a temporary base directory for testing"""
    return tmp_path

@pytest.fixture
def test_directory_config(test_base_dir: Path) -> DirectoryConfig:
    """Create test directory configuration"""
    return DirectoryConfig(
        base_dir=test_base_dir,
        temp_dir=test_base_dir / 'temp',
        downloaded_videos_dir=test_base_dir / 'downloaded_videos',
        output_dir=test_base_dir / 'transcripts',
        logs_dir=test_base_dir / 'logs'
    )

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
def test_minio_config() -> MinIOConfig:
    """Create test MinIO configuration"""
    return MinIOConfig(
        endpoint="minio:9000",
        access_key="minioadmin",
        secret_key="minioadmin",
        bucket="test-bucket",
        secure=False
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