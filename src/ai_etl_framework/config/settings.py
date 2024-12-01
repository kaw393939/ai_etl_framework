# src/ai_etl_framework/config/settings.py

import os
from pathlib import Path
from dotenv import load_dotenv
import logging
from typing import Dict, Any

# Load environment variables from .env file
load_dotenv()

# Base directory for the project
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Valid environment values
VALID_ENVIRONMENTS = {'development', 'test', 'staging', 'production'}
DEFAULT_ENVIRONMENT = 'dev'

def create_directories(config: Dict[str, Any]) -> None:
    """Create necessary directories if they don't exist"""
    for dir_path in config['directories'].values():
        if isinstance(dir_path, Path):
            dir_path.mkdir(parents=True, exist_ok=True)

def get_config(validate: bool = False) -> Dict[str, Any]:
    """Get configuration with optional validation"""
    config = {
        # Service settings
        'service_name': os.getenv('SERVICE_NAME', 'youtube-extractor'),
        'environment': os.getenv('ENVIRONMENT', 'dev'),  # Changed to match test expectation
        
        # Worker settings
        'max_workers': int(os.getenv('MAX_WORKERS', '3')),
        'max_queue_size': int(os.getenv('MAX_QUEUE_SIZE', '20')),

        # MinIO settings
        'minio': {
            'endpoint': os.getenv('MINIO_ENDPOINT', 'localhost:9000'),
            'access_key': os.getenv('MINIO_ACCESS_KEY', 'minioadmin'),
            'secret_key': os.getenv('MINIO_SECRET_KEY', 'minioadmin'),
            'secure': os.getenv('MINIO_SECURE', 'False').lower() == 'true',
            'buckets': {
                'audio': os.getenv('MINIO_AUDIO_BUCKET', 'audio'),
                'chunks': os.getenv('MINIO_CHUNKS_BUCKET', 'chunks'),
                'transcripts': os.getenv('MINIO_TRANSCRIPTS_BUCKET', 'transcripts')
            }
        },

        # API settings
        'api': {
            'host': os.getenv('API_HOST', '0.0.0.0'),
            'port': int(os.getenv('API_PORT', '8000')),
            'cors_origins': os.getenv('CORS_ORIGINS', '*').split(','),
        },

        # Transcription settings
        'transcription': {
            'api_url': os.getenv('TRANSCRIPTION_API_URL', 'https://api.groq.com/openai/v1/audio/transcriptions'),
            'model': os.getenv('TRANSCRIPTION_MODEL', 'whisper-large-v3'),
            'response_format': os.getenv('TRANSCRIPTION_FORMAT', 'json'),
            'language': os.getenv('TRANSCRIPTION_LANGUAGE', None),
            'temperature': float(os.getenv('TRANSCRIPTION_TEMPERATURE', '0')),
            'timestamp_granularities': os.getenv('TIMESTAMP_GRANULARITIES', 'segment').split(','),
        },

        # File handling settings
        'max_file_size': 25 * 1024 * 1024,  # 25 MB
        'supported_formats': ['flac', 'mp3', 'mp4', 'mpeg', 'mpga', 'm4a', 'ogg', 'wav', 'webm'],
        'chunk_max_size_bytes': 25 * 1024 * 1024,  # 25 MB
        'chunk_duration_sec': int(os.getenv('CHUNK_DURATION_SEC', '300')),

        # Directory settings
        'directories': {
            'temp': BASE_DIR / 'temp',
            'downloads': BASE_DIR / 'downloads',
            'output': BASE_DIR / 'transcripts',
            'logs': BASE_DIR / 'logs'
        },

        # API settings
        'api_timeout': int(os.getenv('API_TIMEOUT', '300')),
        'groq_api_key': os.getenv('GROQ_API_KEY'),

        # Retry settings
        'max_retries': int(os.getenv('MAX_RETRIES', '3')),
        'retry_delay': int(os.getenv('RETRY_DELAY', '5')),
    }
    
    if validate:
        validate_config(config)
    
    return config

def validate_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """Validate required configuration settings"""
    # First validate port ranges
    if not 1 <= config['api']['port'] <= 65535:
        raise ValueError("API port must be between 1 and 65535")
    
    # Then validate required settings
    required_settings = [
        ('groq_api_key', "GROQ_API_KEY must be set in environment variables"),
        ('service_name', "SERVICE_NAME must be set"),
        ('environment', "ENVIRONMENT must be set")
    ]
    
    for setting, message in required_settings:
        if not config.get(setting):
            raise ValueError(message)
            
    return config