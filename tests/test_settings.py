import pytest

from src.ai_etl_framework.config.settings import Environment, ServiceConfig

def test_service_config_default_values():
    """
    Test that the ServiceConfig class initializes with correct default values
    """
    config = ServiceConfig()
    
    # Test environment settings
    assert config.environment == Environment.DEV
    assert config.debug is False
    
    # Test MinIO settings
    assert config.minio_root_user == "minioadmin"
    assert config.minio_root_password == "minioadmin"
    assert config.minio_endpoint == "localhost:9000"
    
    # Test Grafana settings
    assert config.grafana_admin_user == "admin"
    assert config.grafana_admin_password == "admin"
    assert config.grafana_port == 3000
    
    # Test Prometheus settings
    assert config.prometheus_port == 9090
    
    # Test FastAPI settings
    assert config.app_title == "ETL Extractor Service"
    assert config.app_description == "Service to process data for the ETL pipeline."
    assert config.app_version == "1.0.0"
    assert config.app_host == "0.0.0.0"
    assert config.app_port == 8000

def test_service_config_environment_validation():
    """
    Test environment enum validation
    """
    # Test valid environment values
    for env in Environment:
        config = ServiceConfig(environment=env)
        assert config.environment == env

def test_service_config_port_constraints():
    """
    Test port number constraints
    """
    # Test valid port numbers
    ServiceConfig(grafana_port=1)
    ServiceConfig(grafana_port=65535)
    ServiceConfig(prometheus_port=1)
    ServiceConfig(prometheus_port=65535)
    ServiceConfig(app_port=1)
    ServiceConfig(app_port=65535)
    
    # Test invalid port numbers
    with pytest.raises(ValueError):
        ServiceConfig(grafana_port=0)
    with pytest.raises(ValueError):
        ServiceConfig(grafana_port=65536)
    
    with pytest.raises(ValueError):
        ServiceConfig(prometheus_port=0)
    with pytest.raises(ValueError):
        ServiceConfig(prometheus_port=65536)
    
    with pytest.raises(ValueError):
        ServiceConfig(app_port=0)
    with pytest.raises(ValueError):
        ServiceConfig(app_port=65536)