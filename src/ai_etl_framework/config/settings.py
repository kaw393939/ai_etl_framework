from typing import Annotated
from enum import Enum
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(str, Enum):
    DEV = 'dev'
    TEST = 'test'
    STAGING = 'staging'
    PROD = 'prod'


class ServiceConfig(BaseSettings):
    # Environment settings
    environment: Environment = Field(default=Environment.DEV)
    debug: bool = Field(default=False)
    
    # MinIO settings
    minio_root_user: str = Field(default="minioadmin")
    minio_root_password: str = Field(default="minioadmin")
    minio_endpoint: str = Field(default="minio:9000")
    
    # Grafana settings with constrained port
    grafana_admin_user: str = Field(default="admin")
    grafana_admin_password: str = Field(default="admin")
    grafana_port: Annotated[int, Field(gt=0, lt=65536)] = Field(default=3000)
    
    # Prometheus settings with constrained port
    prometheus_port: Annotated[int, Field(gt=0, lt=65536)] = Field(default=9090)
    
    # FastAPI settings
    app_title: str = Field(default="ETL Extractor Service")
    app_description: str = Field(default="Service to process data for the ETL pipeline.")
    app_version: str = Field(default="1.0.0")
    app_host: str = Field(default="0.0.0.0")
    app_port: Annotated[int, Field(gt=0, lt=65536)] = Field(default=8000)

    # Model configuration
    model_config = SettingsConfigDict(
        env_prefix='',  # No prefix for environment variables
        case_sensitive=False,  # Environment variables are case-insensitive
        env_file='.env',  # Default .env file
        env_file_encoding='utf-8'  # UTF-8 encoding for the .env file
    )
