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
from ai_etl_framework.common.metrics import PROCESSING_ERRORS, PROCESSING_TIME, REQUEST_COUNT, DISK_USAGE, MEMORY_USAGE, \
    CPU_USAGE
from ai_etl_framework.config.settings import config
from ai_etl_framework.extractor.models.api_models import StreamingTaskResponse
from ai_etl_framework.extractor.models.tasks import TranscriptionTask
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

# Instrument FastAPI for Prometheus metrics
Instrumentator().instrument(app).expose(app)

# Create global service instance

# Request Models
class URLRequest(BaseModel):
    url: str


class TaskRequest(BaseModel):
    url: str


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
        "message": "ETL Extractor Service is running.",
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
    """Submit new transcription task and stream status updates."""
    start_time = time.time()
    transcription_service = TranscriptionService()

    async def status_stream_with_cleanup(task: TranscriptionTask):
        """Internal generator that ensures proper error handling and cleanup."""
        try:
            async for update in transcription_service.stream_status(task):
                yield update
        except Exception as stream_error:
            PROCESSING_ERRORS.labels(endpoint="tasks").inc()

            # Use task's error handling mechanism
            task.add_error(f"Stream error: {str(stream_error)}")
            error_response = task.to_streaming_response()
            yield f"data: {error_response.model_dump_json()}\n\n"

        finally:
            processing_duration = time.time() - start_time
            PROCESSING_TIME.labels(endpoint="tasks").observe(processing_duration)

    try:
        # Pass the full TaskRequest object instead of just the URL
        task = transcription_service.add_task(task_request.url)
        if not task:
            raise HTTPException(
                status_code=400,
                detail="Failed to create task. Queue might be full or URL already exists."
            )

        REQUEST_COUNT.labels(endpoint="tasks").inc()

        return StreamingResponse(
            status_stream_with_cleanup(task),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"
            }
        )

    except HTTPException:
        raise  # Re-raise HTTP exceptions
    except Exception as e:
        PROCESSING_ERRORS.labels(endpoint="tasks").inc()
        logger.exception(f"Error creating task: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )



if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host=config.service.app_host,
        port=config.service.app_port
    )