# tests/test_config/test_settings.py

import pytest
import os
from pathlib import Path
import tempfile
import shutil
from src.ai_etl_framework.config.settings import (
    get_config,
    validate_config,
    BASE_DIR,
    create_directories
)

@pytest.fixture
def temp_base_dir():
    """Create temporary base directory for tests"""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)

@pytest.fixture
def mock_env(monkeypatch):
    """Setup test environment variables"""
    env_vars = {
        'ENVIRONMENT': 'production',
        'SERVICE_NAME': 'test-service',
        'MAX_WORKERS': '5',
        'MAX_QUEUE_SIZE': '30',
        'MINIO_ENDPOINT': 'test-minio:9000',
        'MINIO_ACCESS_KEY': 'test-access',
        'MINIO_SECRET_KEY': 'test-secret',
        'MINIO_SECURE': 'true',
        'API_HOST': 'test-host',
        'API_PORT': '8080',
        'GROQ_API_KEY': 'test-api-key',
        'CHUNK_DURATION_SEC': '600',
        'MAX_RETRIES': '5',
        'TRANSCRIPTION_MODEL': 'test-model',
        'TRANSCRIPTION_LANGUAGE': 'en',
        'TRANSCRIPTION_TEMPERATURE': '0.5',
        'TIMESTAMP_GRANULARITIES': 'word,segment',
    }
    
    for key, value in env_vars.items():
        monkeypatch.setenv(key, value)
    
    return env_vars

@pytest.fixture
def config():
    """Provide clean config for each test without validation"""
    return get_config(validate=False)

def test_base_directory():
    """Test BASE_DIR is set correctly"""
    assert isinstance(BASE_DIR, Path)
    assert BASE_DIR.exists()
    assert BASE_DIR.is_dir()

def test_default_config(config):
    """Test default configuration values"""
    assert config['service_name'] == 'youtube-extractor'
    assert config['environment'] == 'dev'  # Updated to match config default
    assert config['max_workers'] == 3
    assert config['max_queue_size'] == 20

def test_minio_defaults(config):
    """Test MinIO default settings"""
    assert config['minio']['endpoint'] == 'localhost:9000'
    assert config['minio']['access_key'] == 'minioadmin'
    assert config['minio']['secret_key'] == 'minioadmin'
    assert config['minio']['secure'] is False
    assert set(config['minio']['buckets'].keys()) == {'audio', 'chunks', 'transcripts'}

def test_api_defaults(config):
    """Test API default settings"""
    assert config['api']['host'] == '0.0.0.0'
    assert config['api']['port'] == 8000
    assert config['api']['cors_origins'] == ['*']

def test_directories_creation(temp_base_dir):
    """Test directory creation"""
    test_config = {
        'directories': {
            'temp': temp_base_dir / 'temp',
            'downloads': temp_base_dir / 'downloads',
            'output': temp_base_dir / 'transcripts',
            'logs': temp_base_dir / 'logs'
        }
    }
    
    create_directories(test_config)
    
    for dir_path in test_config['directories'].values():
        assert dir_path.exists()
        assert dir_path.is_dir()

def test_validation_without_groq_key():
    """Test validation fails without GROQ API key"""
    config = get_config(validate=False)
    config['groq_api_key'] = None
    
    with pytest.raises(ValueError, match="GROQ_API_KEY must be set in environment variables"):
        validate_config(config)

def test_env_override(mock_env):
    """Test environment variable overrides"""
    config = get_config(validate=False)
    
    assert config['service_name'] == 'test-service'
    assert config['environment'] == 'production'
    assert config['max_workers'] == 5
    assert config['max_queue_size'] == 30
    assert config['minio']['endpoint'] == 'test-minio:9000'
    assert config['minio']['secure'] is True
    assert config['api']['port'] == 8080
    assert config['chunk_duration_sec'] == 600

def test_file_limits(config):
    """Test file size limits"""
    assert config['max_file_size'] == 25 * 1024 * 1024  # 25MB
    assert config['chunk_max_size_bytes'] == config['max_file_size']
    assert config['chunk_duration_sec'] == 300  # 5 minutes default

def test_supported_formats(config):
    """Test supported audio/video formats"""
    formats = config['supported_formats']
    required_formats = {'mp3', 'wav', 'mp4'}
    assert required_formats.issubset(set(formats))

def test_transcription_settings(config):
    """Test transcription settings"""
    transcription = config['transcription']
    assert transcription['model'] == 'whisper-large-v3'
    assert transcription['response_format'] == 'json'
    assert isinstance(transcription['timestamp_granularities'], list)
    assert isinstance(transcription['temperature'], float)
    assert 0 <= transcription['temperature'] <= 1

@pytest.mark.parametrize("port_setting", ['api.port'])
def test_port_ranges(config, port_setting):
    """Test port number validation"""
    parts = port_setting.split('.')
    value = config
    for part in parts:
        value = value[part]
    assert 1 <= value <= 65535

def test_invalid_port(mock_env):
    """Test validation fails with invalid port"""
    config = get_config(validate=False)
    config['api']['port'] = 70000
    
    with pytest.raises(ValueError, match="API port must be between 1 and 65535"):
        validate_config(config)