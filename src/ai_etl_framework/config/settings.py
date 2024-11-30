# src/ai_etl_framework/config/settings.py

from enum import Enum
from pydantic import Field, conint
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
    minio_endpoint: str = Field(default="localhost:9000")
    
    # Grafana settings with constrained port
    grafana_admin_user: str = Field(default="admin")
    grafana_admin_password: str = Field(default="admin")
    grafana_port: conint(gt=0, lt=65536) = Field(default=3000)
    
    # Prometheus settings with constrained port
    prometheus_port: conint(gt=0, lt=65536) = Field(default=9090)
    
    model_config = SettingsConfigDict(
        env_prefix='',
        case_sensitive=False,
        env_file='.env',
        env_file_encoding='utf-8'
    )
