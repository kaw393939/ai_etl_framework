from enum import Enum
from typing import Optional
from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings

class Environment(str, Enum):
    DEV = 'dev'
    TEST = 'test'
    STAGING = 'staging'
    PROD = 'prod'

class ServiceConfig(BaseSettings):
    environment: Environment = Field(default=Environment.DEV)
    debug: bool = Field(default=False)
    
    class Config:
        env_prefix = ''
        case_sensitive = False
