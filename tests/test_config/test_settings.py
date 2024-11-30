# tests/test_config/test_settings.py

import pytest
from pydantic import ValidationError
from ai_etl_framework.config.settings import ServiceConfig, Environment


def test_service_config_default():
    config = ServiceConfig()
    # Test environment settings
    assert config.environment == Environment.DEV
    assert config.debug is False
    
    # Test MinIO defaults
    assert config.minio_root_user == "minioadmin"
    assert config.minio_root_password == "minioadmin"
    assert config.minio_endpoint == "localhost:9000"
    
    # Test Grafana defaults
    assert config.grafana_admin_user == "admin"
    assert config.grafana_admin_password == "admin"
    assert config.grafana_port == 3000
    
    # Test Prometheus defaults
    assert config.prometheus_port == 9090


@pytest.fixture
def test_env(monkeypatch):
    # Set up test environment variables
    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.setenv("MINIO_ROOT_USER", "test_user")
    monkeypatch.setenv("MINIO_ROOT_PASSWORD", "test_password")
    monkeypatch.setenv("GRAFANA_ADMIN_USER", "test_admin")
    monkeypatch.setenv("GRAFANA_ADMIN_PASSWORD", "test_admin_pass")
    monkeypatch.setenv("GRAFANA_PORT", "4000")      # Optional: Set custom port
    monkeypatch.setenv("PROMETHEUS_PORT", "9191")  # Optional: Set custom port


def test_service_config_from_env(test_env):
    config = ServiceConfig()
    assert config.environment == Environment.TEST
    assert config.minio_root_user == "test_user"
    assert config.minio_root_password == "test_password"
    assert config.grafana_admin_user == "test_admin"
    assert config.grafana_admin_password == "test_admin_pass"
    assert config.grafana_port == 4000          # Verify custom port from env
    assert config.prometheus_port == 9191       # Verify custom port from env


def test_service_config_validation():
    # Test with invalid environment
    with pytest.raises(ValidationError) as exc_info:
        ServiceConfig(environment="invalid")
    # Assert that the error message contains information about the invalid environment
    assert "environment" in exc_info.value.errors()[0]['loc']
    assert "Input should be 'dev', 'test', 'staging' or 'prod'" in exc_info.value.errors()[0]['msg']
    
    # Test with invalid Grafana port number (negative)
    with pytest.raises(ValidationError) as exc_info:
        ServiceConfig(grafana_port=-1)
    assert "grafana_port" in exc_info.value.errors()[0]['loc']
    assert "Input should be greater than 0" in exc_info.value.errors()[0]['msg']
    
    # Test with invalid Prometheus port number (zero)
    with pytest.raises(ValidationError) as exc_info:
        ServiceConfig(prometheus_port=0)
    assert "prometheus_port" in exc_info.value.errors()[0]['loc']
    assert "Input should be greater than 0" in exc_info.value.errors()[0]['msg']
    
    # Test with invalid Grafana port number (too large)
    with pytest.raises(ValidationError) as exc_info:
        ServiceConfig(grafana_port=70000)
    assert "grafana_port" in exc_info.value.errors()[0]['loc']
    assert "Input should be less than 65536" in exc_info.value.errors()[0]['msg']
    
    # Test with invalid Prometheus port number (too large)
    with pytest.raises(ValidationError) as exc_info:
        ServiceConfig(prometheus_port=70000)
    assert "prometheus_port" in exc_info.value.errors()[0]['loc']
    assert "Input should be less than 65536" in exc_info.value.errors()[0]['msg']
