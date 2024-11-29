import pytest
from ai_etl_framework.config.settings import ServiceConfig, Environment

def test_service_config_default():
    config = ServiceConfig()
    assert config.environment == Environment.DEV
    assert config.debug is False

def test_service_config_from_env(test_env):
    config = ServiceConfig()
    assert config.environment == Environment.TEST
