from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
from ai_etl_framework.config.settings import ServiceConfig
from prometheus_fastapi_instrumentator import Instrumentator
from prometheus_client import Counter, Histogram, Gauge
import time
import os
import tempfile
import string
import random
import multiprocessing

# Load configuration
config = ServiceConfig()

# Initialize FastAPI app with dynamic settings
app = FastAPI(
    title=config.app_title,
    description=config.app_description,
    version=config.app_version,
    debug=config.debug
)

# Initialize Prometheus metrics
REQUEST_COUNT = Counter(
    'extractor_processed_urls_total', 
    'Total number of URLs processed'
)

PROCESSING_ERRORS = Counter(
    'extractor_processing_errors_total', 
    'Total number of processing errors'
)

PROCESSING_TIME = Histogram(
    'extractor_processing_duration_seconds', 
    'Duration of URL processing in seconds'
)

MEMORY_USAGE = Gauge(
    'extractor_memory_usage_bytes',
    'Current memory usage in bytes'
)

DISK_USAGE = Gauge(
    'extractor_disk_usage_bytes',
    'Current disk usage in bytes'
)

CPU_USAGE = Gauge(
    'extractor_cpu_usage_percent',
    'Current CPU usage in percent during stress operations'
)

# Instrument FastAPI for Prometheus metrics
Instrumentator().instrument(app).expose(app)

# Define a request model for the URL input
class URLRequest(BaseModel):
    url: str

def generate_large_string(size_in_mb):
    """Generates a large string of specified size in megabytes."""
    return ''.join(random.choices(string.ascii_letters + string.digits, k=size_in_mb * 1024 * 1024))

def cpu_stress(load_percent, duration_sec):
    """
    Simulates CPU load by performing calculations to achieve the desired load percentage
    for the specified duration.
    """
    if load_percent < 0 or load_percent > 100:
        raise ValueError("load_percent must be between 0 and 100")
    
    end_time = time.time() + duration_sec
    while time.time() < end_time:
        # Perform CPU-bound operations
        [x**2 for x in range(10000)]
        # Sleep to achieve desired load
        time.sleep((100 - load_percent) / 100.0)

@app.get("/")
def root():
    """
    Root endpoint for service health check.
    """
    return {
        "message": "ETL Extractor Service is running.",
        "environment": config.environment,
        "debug": config.debug
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
    """
    Processes the given URL and returns a response.
    Optionally consumes memory, disk, and CPU to stress the system.
    """
    url = request.url
    if not url:
        raise HTTPException(status_code=400, detail="URL must not be empty.")
    
    start_time = time.time()
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
            # Write random data to the file
            data = generate_large_string(disk_size_mb)
            temp_file.write(data.encode('utf-8'))
            temp_file.close()
            # Update disk usage metric
            disk_usage_bytes = os.path.getsize(temp_file_path)
            DISK_USAGE.set(disk_usage_bytes)
        
        # Optional: Stress CPU
        cpu_process = None
        if stress_cpu:
            CPU_USAGE.set(cpu_load_percent)
            cpu_process = multiprocessing.Process(target=cpu_stress, args=(cpu_load_percent, cpu_duration_sec))
            cpu_process.start()
        
        # Placeholder for actual processing logic
        # Simulate processing with a sleep
        time.sleep(0.5)  # Simulate processing time
        
        REQUEST_COUNT.inc()
        processing_duration = time.time() - start_time
        PROCESSING_TIME.observe(processing_duration)
        
        # Wait for CPU stress to complete
        if cpu_process:
            cpu_process.join()
            CPU_USAGE.set(0)
        
        # Cleanup allocated resources to prevent memory leaks
        if stress_memory:
            del allocated_memory
            MEMORY_USAGE.set(0)
        
        if stress_disk:
            os.remove(temp_file_path)
            DISK_USAGE.set(0)
        
        return {
            "message": f"Processing URL: {url}",
            "minio_endpoint": config.minio_endpoint,
            "stress_memory": stress_memory,
            "stress_disk": stress_disk,
            "stress_cpu": stress_cpu
        }
    except Exception as e:
        PROCESSING_ERRORS.inc()
        # Ensure cleanup in case of exception
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