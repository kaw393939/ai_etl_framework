import pytest
from pathlib import Path
from ai_etl_framework.config.settings import (
    Environment,
    ServiceConfig,
    DirectoryConfig,
    AppConfig,
    MinIOConfig
)


def test_service_config_initialization(test_service_config: ServiceConfig):
    """Test ServiceConfig initialization with test values"""
    assert test_service_config.environment == Environment.TEST
    assert test_service_config.debug is True
    assert test_service_config.app_title == "Transcription Service API"
    assert test_service_config.app_description == "Service to process and transcribe audio/video content."
    assert test_service_config.app_version == "1.0.0"
    assert test_service_config.app_host == "localhost"
    assert test_service_config.app_port == 8000


def test_directory_config_initialization(test_directory_config: DirectoryConfig, test_base_dir: Path):
    """Test DirectoryConfig initialization and directory structure"""
    assert test_directory_config.base_dir == test_base_dir
    assert test_directory_config.temp_dir == test_base_dir / 'temp'
    assert test_directory_config.downloaded_videos_dir == test_base_dir / 'downloaded_videos'
    assert test_directory_config.output_dir == test_base_dir / 'transcripts'
    assert test_directory_config.logs_dir == test_base_dir / 'logs'


def test_minio_config_initialization(test_minio_config: MinIOConfig):
    """Test MinIOConfig initialization with test values"""
    assert test_minio_config.endpoint == "minio:9000"
    assert test_minio_config.access_key == "minioadmin"
    assert test_minio_config.secret_key == "minioadmin"
    assert test_minio_config.bucket == "test-bucket"
    assert test_minio_config.secure is False


def test_app_config_initialization(test_app_config: AppConfig):
    """Test complete AppConfig initialization"""
    assert test_app_config.service.environment == Environment.TEST
    assert test_app_config.service.debug is True
    assert test_app_config.minio.endpoint == "minio:9000"
    assert test_app_config.worker.max_workers == 2
    assert test_app_config.worker.max_queue_size == 10


def test_environment_validation():
    """Test environment enum validation"""
    with pytest.raises(ValueError):
        ServiceConfig(environment="invalid")


def test_port_validation():
    """Test port number validation"""
    with pytest.raises(ValueError):
        ServiceConfig(app_port=0)

    with pytest.raises(ValueError):
        ServiceConfig(app_port=65536)


def test_directory_creation(test_app_config: AppConfig, test_base_dir: Path):
    """Test directory creation functionality"""
    test_app_config.setup_directories()

    assert test_base_dir.exists()
    assert (test_base_dir / 'temp').exists()
    assert (test_base_dir / 'downloaded_videos').exists()
    assert (test_base_dir / 'transcripts').exists()
    assert (test_base_dir / 'logs').exists()