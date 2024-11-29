from enum import Enum
from typing import Optional
from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

class Environment(str, Enum):
    DEV = 'dev'
    TEST = 'test'
    STAGING = 'staging'
    PROD = 'prod'

class ServiceConfig(BaseSettings):
    environment: Environment = Field(default=Environment.DEV)
    debug: bool = Field(default=False)
    
    model_config = SettingsConfigDict(
        env_prefix = '',
        case_sensitive = False,
        env_file = '.env',
        env_file_encoding = 'utf-8'
    )