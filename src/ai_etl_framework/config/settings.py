# config/settings.py

from enum import Enum
from typing import List, Optional, Dict, Annotated
from pathlib import Path
from pydantic import Field, HttpUrl, BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(str, Enum):
    DEV = 'dev'
    TEST = 'test'
    STAGING = 'staging'
    PROD = 'prod'


class AudioSettings(BaseModel):
    sample_rate: int = Field(default=16000, ge=8000, le=48000,
                             description="Audio sample rate in Hz")
    channels: int = Field(default=1, ge=1, le=2,
                          description="Number of audio channels (1 for mono, 2 for stereo)")
    format: str = Field(default="wav",
                        description="Audio format for processed files")


class TranscriptionConfig(BaseSettings):
    # Existing fields...

    # Audio processing settings
    audio_settings: AudioSettings = Field(
        default_factory=AudioSettings,
        description="Audio processing configuration"
    )
    api_url: str = Field(
        default="https://api.groq.com/openai/v1/audio/transcriptions",
        description="API endpoint for youtube_transcription service"
    )
    model: str = Field(default="whisper-large-v3")
    response_format: str = Field(default="json")
    language: Optional[str] = Field(default=None)
    temperature: float = Field(default=0.0)
    timestamp_granularities: List[str] = Field(default=["segment"])
    max_file_size: int = Field(default=25 * 1024 * 1024)  # 25 MB
    supported_formats: List[str] = Field(
        default=["flac", "mp3", "mp4", "mpeg", "mpga", "m4a", "ogg", "wav", "webm"]
    )
    audio_format: str = Field(
        default="wav",
        description="Output audio format for chunks"
    )
    chunk_max_size_bytes: int = Field(default=25 * 1024 * 1024)  # 25 MB
    chunk_duration_sec: int = Field(default=300)
    api_timeout: int = Field(default=300)
    api_key: str = Field(...)  # Required field


class WorkerConfig(BaseSettings):
    max_workers: int = Field(default=3, gt=0)
    max_queue_size: int = Field(default=20, gt=0)


class DirectoryConfig(BaseSettings):
    base_dir: Path = Field(default=Path(__file__).resolve().parent.parent)
    temp_dir: Path = Field(default=f"{base_dir}/temp")
    downloaded_videos_dir: Path = Field(default=f"{base_dir}/downloaded_videos")
    output_dir: Path = Field(default=f"{base_dir}/transcripts")
    logs_dir: Path = Field(default=f"{base_dir}/logs")

    def model_post_init(self, *args, **kwargs):
        # Set default paths relative to base_dir if not specified
        self.temp_dir = self.temp_dir or self.base_dir / 'temp'
        self.downloaded_videos_dir = self.downloaded_videos_dir or self.base_dir / 'downloaded_videos'
        self.output_dir = self.output_dir or self.base_dir / 'transcripts'
        self.logs_dir = self.logs_dir or self.base_dir / 'logs'


class ServiceConfig(BaseSettings):
    # Environment settings
    environment: Environment = Field(default=Environment.DEV)
    debug: bool = Field(default=False)


    # MinIO settings
    minio_root_user: str = Field(default="minioadmin")
    minio_root_password: str = Field(default="minioadmin")
    minio_endpoint: str = Field(default="localhost:9000")

    # Grafana settings
    grafana_admin_user: str = Field(default="admin")
    grafana_admin_password: str = Field(default="admin")
    grafana_port: Annotated[int, Field(gt=0, lt=65536)] = Field(default=3000)

    # Prometheus settings
    prometheus_port: Annotated[int, Field(gt=0, lt=65536)] = Field(default=9090)

    # FastAPI settings
    app_title: str = Field(default="Transcription Service API")
    app_description: str = Field(default="Service to process and transcribe audio/video content.")
    app_version: str = Field(default="1.0.0")
    app_host: str = Field(default="0.0.0.0")
    app_port: Annotated[int, Field(gt=0, lt=65536)] = Field(default=8000)

    model_config = SettingsConfigDict(
        env_prefix='',
        case_sensitive=False,
        env_file='.env',
        env_file_encoding='utf-8'
    )

class LoggingConfig(BaseSettings):
    level: str = Field(
        default="INFO",
        description="Logging level"
    )
    format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="Log message format"
    )
    file_name: str = Field(
        default="app.log",
        description="Base log file name"
    )
    date_format: str = Field(
        default="%Y%m%d",
        description="Date format for log file names"
    )
    encoding: str = Field(
        default="utf-8",
        description="Log file encoding"
    )

    model_config = SettingsConfigDict(
        env_prefix="LOGGING_"
    )
class MinIOConfig(BaseSettings):
    endpoint: str = Field(
        default="minio:9000",
        description="MinIO endpoint (host:port format)"
    )
    access_key: str = Field(
        default="minioadmin",
        description="MinIO access key"
    )
    secret_key: str = Field(
        default="minioadmin",
        description="MinIO secret key"
    )
    bucket: str = Field(
        default="youtube_transcription-service",
        description="Default MinIO bucket name"
    )

    secure: bool = Field(
        default=False,
        description="Use SSL/TLS for MinIO connection"
    )
    # Add storage paths configuration
    storage_paths: Dict[str, str] = Field(
        default={
            "audio": "audio",
            "chunks": "chunks",
            "transcripts": "transcripts",
            "metadata": "metadata",
            "temp": "temp"
        },
        description="Storage path configuration for different file types"
    )

    model_config = SettingsConfigDict(
        env_prefix="MINIO_",
        case_sensitive=False,
        env_file=".env",
        env_file_encoding="utf-8"
    )
class DownloadConfig(BaseSettings):
    max_retries: int = Field(default=3, ge=0, description="Maximum number of download retry attempts")
    retry_delay: int = Field(default=5, ge=0, description="Delay in seconds between retry attempts")
    timeout: int = Field(default=3600, ge=0, description="Download timeout in seconds (default 1 hour)")
    verify_timeout: int = Field(default=300, ge=0, description="Verification timeout in seconds (default 5 minutes)")

    model_config = SettingsConfigDict(
        env_prefix='DOWNLOAD_'
    )
class AppConfig(BaseSettings):
    service: ServiceConfig = Field(default_factory=ServiceConfig)
    transcription: TranscriptionConfig = Field(default_factory=TranscriptionConfig)
    worker: WorkerConfig = Field(default_factory=WorkerConfig)
    directory: DirectoryConfig = Field(default_factory=DirectoryConfig)
    download: DownloadConfig = Field(default_factory=DownloadConfig)  # Add download config
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    minio: MinIOConfig = Field(default_factory=MinIOConfig)  # Add MinIO config

    # Logging settings
    log_file: str = Field(default="transcriber.log")

    model_config = SettingsConfigDict(
        env_prefix='',
        case_sensitive=False,
        env_file='.env',
        env_file_encoding='utf-8',
        extra='ignore'
    )

    def setup_directories(self):
        """Create necessary directories if they don't exist."""
        for directory in [
            self.directory.temp_dir,
            self.directory.downloaded_videos_dir,
            self.directory.output_dir,
            self.directory.logs_dir
        ]:
            directory.mkdir(parents=True, exist_ok=True)


# Create a global config instance
config = AppConfig()
config.setup_directories()

# Export the config instance
__all__ = ['config']