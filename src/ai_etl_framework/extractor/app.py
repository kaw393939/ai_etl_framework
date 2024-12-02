# main.py

from fastapi import FastAPI, HTTPException, Query
from minio import S3Error, Minio
from starlette.responses import StreamingResponse
from prometheus_fastapi_instrumentator import Instrumentator
from prometheus_client import Counter, Histogram, Gauge
import time
import os
import tempfile
import string
import random
import multiprocessing
from typing import Optional
from pydantic import BaseModel, HttpUrl

from ai_etl_framework.common.logger import setup_logger
from ai_etl_framework.config.settings import config
from ai_etl_framework.extractor.youtube_transcription.transcription_service import TranscriptionService
logger = setup_logger(__name__)
# Initialize FastAPI app with dynamic settings
app = FastAPI(
    title=config.service.app_title,
    description=config.service.app_description,
    version=config.service.app_version,
    debug=config.service.debug
)

# Initialize Prometheus metrics
REQUEST_COUNT = Counter(
    'transcription_service_requests_total',
    'Total number of requests processed',
    ['endpoint']
)

PROCESSING_ERRORS = Counter(
    'transcription_service_errors_total',
    'Total number of processing errors',
    ['endpoint']
)

PROCESSING_TIME = Histogram(
    'transcription_service_duration_seconds',
    'Duration of request processing in seconds',
    ['endpoint']
)

MEMORY_USAGE = Gauge(
    'transcription_service_memory_usage_bytes',
    'Current memory usage in bytes'
)

DISK_USAGE = Gauge(
    'transcription_service_disk_usage_bytes',
    'Current disk usage in bytes'
)

CPU_USAGE = Gauge(
    'transcription_service_cpu_usage_percent',
    'Current CPU usage in percent'
)

# Instrument FastAPI for Prometheus metrics
Instrumentator().instrument(app).expose(app)

# Create global service instance
transcription_service = TranscriptionService()

# Request Models
class URLRequest(BaseModel):
    url: str


class TaskRequest(BaseModel):
    url: HttpUrl


def generate_large_string(size_in_mb):
    """Generates a large string of specified size in megabytes."""
    return ''.join(random.choices(string.ascii_letters + string.digits, k=size_in_mb * 1024 * 1024))


def cpu_stress(load_percent, duration_sec):
    """Simulates CPU load by performing calculations."""
    if load_percent < 0 or load_percent > 100:
        raise ValueError("load_percent must be between 0 and 100")

    end_time = time.time() + duration_sec
    while time.time() < end_time:
        [x ** 2 for x in range(10000)]
        time.sleep((100 - load_percent) / 100.0)


@app.get("/")
def root():
    """Root endpoint for service health check."""
    REQUEST_COUNT.labels(endpoint="root").inc()
    return {
        "message": "Transcription Service is running",
        "environment": config.service.environment,
        "debug": config.service.debug
    }


@app.post("/process-url/")
def process_url(
        request: URLRequest,
        stress_memory: bool = Query(False, description="Enable memory stress"),
        stress_disk: bool = Query(False, description="Enable disk stress"),
        stress_cpu: bool = Query(False, description="Enable CPU stress"),
        memory_size_mb: int = Query(100, ge=1, le=1000, description="Amount of memory to consume in MB"),
        disk_size_mb: int = Query(100, ge=1, le=1000, description="Amount of disk space to use in MB"),
        cpu_load_percent: int = Query(50, ge=0, le=100, description="CPU load percentage"),
        cpu_duration_sec: int = Query(10, ge=1, le=300, description="CPU stress duration in seconds")
):
    """Test endpoint for system stress testing."""
    start_time = time.time()
    url = request.url

    if not url:
        raise HTTPException(status_code=400, detail="URL must not be empty.")

    try:
        # Optional: Stress Memory
        allocated_memory = None
        if stress_memory:
            allocated_memory = generate_large_string(memory_size_mb)
            MEMORY_USAGE.set(len(allocated_memory.encode('utf-8')))

        # Optional: Stress Disk
        temp_file_path = None
        if stress_disk:
            temp_dir = tempfile.gettempdir()
            temp_file = tempfile.NamedTemporaryFile(delete=False, dir=temp_dir, suffix='.tmp')
            temp_file_path = temp_file.name
            data = generate_large_string(disk_size_mb)
            temp_file.write(data.encode('utf-8'))
            temp_file.close()
            disk_usage_bytes = os.path.getsize(temp_file_path)
            DISK_USAGE.set(disk_usage_bytes)

        # Optional: Stress CPU
        cpu_process = None
        if stress_cpu:
            CPU_USAGE.set(cpu_load_percent)
            cpu_process = multiprocessing.Process(target=cpu_stress, args=(cpu_load_percent, cpu_duration_sec))
            cpu_process.start()

        time.sleep(0.5)  # Simulate processing time

        REQUEST_COUNT.labels(endpoint="process-url").inc()
        processing_duration = time.time() - start_time
        PROCESSING_TIME.labels(endpoint="process-url").observe(processing_duration)

        # Cleanup and resource management
        if cpu_process:
            cpu_process.join()
            CPU_USAGE.set(0)

        if stress_memory:
            del allocated_memory
            MEMORY_USAGE.set(0)

        if stress_disk:
            os.remove(temp_file_path)
            DISK_USAGE.set(0)

        return {
            "message": f"Processing URL: {url}",
            "minio_endpoint": config.service.minio_endpoint,
            "stress_memory": stress_memory,
            "stress_disk": stress_disk,
            "stress_cpu": stress_cpu
        }
    except Exception as e:
        PROCESSING_ERRORS.labels(endpoint="process-url").inc()
        # Cleanup in case of exception
        if cpu_process and cpu_process.is_alive():
            cpu_process.terminate()
            CPU_USAGE.set(0)
        if stress_memory:
            del allocated_memory
            MEMORY_USAGE.set(0)
        if stress_disk and temp_file_path and os.path.exists(temp_file_path):
            os.remove(temp_file_path)
            DISK_USAGE.set(0)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/tasks/", response_class=StreamingResponse)
async def create_task(task_request: TaskRequest):
    """Submit new youtube_transcription task and stream status updates using Server-Sent Events."""
    start_time = time.time()
    try:
        task = transcription_service.add_task(str(task_request.url))
        REQUEST_COUNT.labels(endpoint="tasks").inc()
        processing_duration = time.time() - start_time
        PROCESSING_TIME.labels(endpoint="tasks").observe(processing_duration)

        return StreamingResponse(
            transcription_service.stream_status(task),
            media_type="text/event-stream"
        )
    except Exception as e:
        PROCESSING_ERRORS.labels(endpoint="tasks").inc()
        raise HTTPException(status_code=400, detail=str(e))


@app.on_event("shutdown")
def shutdown_service():
    """Cleanup on service shutdown."""
    transcription_service.shutdown()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host=config.service.app_host,
        port=config.service.app_port
    )