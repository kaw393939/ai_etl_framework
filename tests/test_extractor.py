from minio import Minio


def test_root_endpoint(app_client, test_app_config):
    """Test the root endpoint functionality."""
    response = app_client.get("/")
    assert response.status_code == 200

    data = response.json()
    assert data["message"] == "Transcription Service is running"
    assert data["environment"] == test_app_config.service.environment
    assert data["debug"] == test_app_config.service.debug
import pytest
import minio
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime
from fastapi import HTTPException

from ai_etl_framework.extractor.models.tasks import TranscriptionTask, TaskStatus, TaskStats, TranscriptionMetadata
from ai_etl_framework.extractor.youtube_transcription.transcription_service import TranscriptionService
from ai_etl_framework.extractor.models.api_models import TaskResponse, StreamingTaskResponse

def test_root_endpoint(app_client, test_app_config, minio_mock):
    """Test the root endpoint functionality."""
    # The minio_mock automatically patches minio.Minio
    response = app_client.get("/")
    assert response.status_code == 200

    data = response.json()
    assert data["message"] == "ETL Extractor Service is running."
    assert data["environment"] == test_app_config.service.environment
    assert data["debug"] == test_app_config.service.debug


def test_process_url_success(app_client,minio_mock):
    """Test successful URL processing."""
    url = "http://example.com/video"
    payload = {"url": url}

    response = app_client.post("/process-url/", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert data["message"] == f"Processing URL: {url}"
    assert "minio_endpoint" in data
    assert data["stress_memory"] is False
    assert data["stress_disk"] is False
    assert data["stress_cpu"] is False


def test_process_url_with_stress_options(app_client,minio_mock):
    """Test URL processing with stress testing options."""
    url = "http://example.com/video"
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

    response = app_client.post("/process-url/", json=payload, params=query_params)
    assert response.status_code == 200

    data = response.json()
    assert data["message"] == f"Processing URL: {url}"
    assert data["stress_memory"] is True
    assert data["stress_disk"] is True
    assert data["stress_cpu"] is True


def test_process_url_empty_url(app_client,minio_mock):
    """Test handling of empty URL submission."""
    payload = {"url": ""}

    response = app_client.post("/process-url/", json=payload)
    assert response.status_code == 400

    data = response.json()
    assert data["detail"] == "URL must not be empty."


def test_process_url_invalid_params(app_client,minio_mock):
    """Test handling of invalid stress test parameters."""
    url = "http://example.com/video"
    payload = {"url": url}
    query_params = {
        "memory_size_mb": 2000  # Exceeds maximum limit
    }

    response = app_client.post("/process-url/", json=payload, params=query_params)
    assert response.status_code == 422


def test_prometheus_metrics_endpoint(app_client,minio_mock):
    """Test the Prometheus metrics endpoint."""
    response = app_client.get("/metrics")
    assert response.status_code == 200
    assert "transcription_service_requests_total" in response.text