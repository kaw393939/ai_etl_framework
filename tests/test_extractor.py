from unittest.mock import patch
import pytest
from fastapi.testclient import TestClient

@pytest.fixture
def mock_service_config():
    """Fixture to mock the ServiceConfig."""
    with patch("ai_etl_framework.config.settings.ServiceConfig") as mock_service_config:
        mock_service_config.return_value.app_title = "ETL Extractor"
        mock_service_config.return_value.app_description = "Mocked ETL Extractor"
        mock_service_config.return_value.app_version = "0.1.0"
        mock_service_config.return_value.debug = True
        mock_service_config.return_value.environment = "test"
        mock_service_config.return_value.minio_endpoint = "http://mock-minio"
        yield mock_service_config

def test_root_endpoint(mock_service_config):
    """Test the root endpoint."""
    from ai_etl_framework.extractor.app import app
    client = TestClient(app)

    # Test the endpoint
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "ETL Extractor Service is running."
    assert data["environment"] == "test"
    assert data["debug"] is True

def test_process_url_success(mock_service_config):
    """Test processing a URL successfully."""
    from ai_etl_framework.extractor.app import app
    client = TestClient(app)

    url = "http://example.com"
    payload = {"url": url}
    response = client.post("/process-url/", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == f"Processing URL: {url}"
    assert data["stress_memory"] is False
    assert data["stress_disk"] is False
    assert data["stress_cpu"] is False

def test_process_url_with_stress_options(mock_service_config):
    """Test processing a URL with stress options enabled."""
    from ai_etl_framework.extractor.app import app
    client = TestClient(app)

    url = "http://example.com"
    payload = {"url": url}
    query_params = {
        "stress_memory": True,
        "stress_disk": True,
        "stress_cpu": True,
        "memory_size_mb": 10,
        "disk_size_mb": 10,
        "cpu_load_percent": 50,
        "cpu_duration_sec": 5
    }
    response = client.post("/process-url/", json=payload, params=query_params)
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == f"Processing URL: {url}"
    assert data["stress_memory"] is True
    assert data["stress_disk"] is True
    assert data["stress_cpu"] is True

def test_process_url_empty_url(mock_service_config):
    """Test processing with an empty URL."""
    from ai_etl_framework.extractor.app import app
    client = TestClient(app)

    payload = {"url": ""}
    response = client.post("/process-url/", json=payload)
    assert response.status_code == 400
    data = response.json()
    assert data["detail"] == "URL must not be empty."

def test_process_url_invalid_params(mock_service_config):
    """Test processing with invalid query parameters."""
    from ai_etl_framework.extractor.app import app
    client = TestClient(app)

    url = "http://example.com"
    payload = {"url": url}
    query_params = {
        "memory_size_mb": 2000  # Invalid: exceeds limit
    }
    response = client.post("/process-url/", json=payload, params=query_params)
    assert response.status_code == 422

def test_prometheus_metrics_exposed(mock_service_config):
    """Test Prometheus metrics endpoint exposure."""
    from ai_etl_framework.extractor.app import app
    client = TestClient(app)

    response = client.get("/metrics")
    assert response.status_code == 200
    assert "extractor_processed_urls_total" in response.text
