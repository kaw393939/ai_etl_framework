from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
from prometheus_fastapi_instrumentator import Instrumentator
from prometheus_client import Counter, Histogram, Gauge
import time
import os
import tempfile
import string
import random
import multiprocessing
import logging

# Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Mock configuration for demonstration purposes
class ServiceConfig:
    app_title = "ETL Extractor Service"
    app_description = "Service responsible for extracting and processing data."
    app_version = "1.0.0"
    debug = True
    environment = "production"
    minio_endpoint = "http://localhost:9000"

config = ServiceConfig()

# Initialize Prometheus metrics before Instrumentator to ensure they're registered
etl_processed_documents_total = Counter(
    'etl_processed_documents_total',
    'Total number of documents processed',
    ['job']
)

etl_processing_errors_total = Counter(
    'etl_processing_errors_total',
    'Total number of processing errors',
    ['job']
)

etl_processing_duration_seconds_sum = Counter(
    'etl_processing_duration_seconds_sum',
    'Sum of processing durations in seconds',
    ['job']
)

etl_processing_duration_seconds_count = Counter(
    'etl_processing_duration_seconds_count',
    'Count of processing durations',
    ['job']
)

# Additional metrics
REQUEST_COUNT = Counter(
    'etl_processed_documents_total',
    'Total number of documents processed',
    ['job']
)

PROCESSING_ERRORS = Counter(
    'etl_processing_errors_total',
    'Total number of processing errors',
    ['job']
)

PROCESSING_TIME = Histogram(
    'etl_processing_duration_seconds',
    'Duration of document processing in seconds',
    ['job']
)

MEMORY_USAGE = Gauge(
    'etl_memory_usage_bytes',
    'Current memory usage in bytes',
    ['job']
)

DISK_USAGE = Gauge(
    'etl_disk_usage_bytes',
    'Current disk usage in bytes',
    ['job']
)

CPU_USAGE = Gauge(
    'etl_cpu_usage_percent',
    'Current CPU usage in percent during stress operations',
    ['job']
)

# Initialize FastAPI app with dynamic settings
app = FastAPI(
    title=config.app_title,
    description=config.app_description,
    version=config.app_version,
    debug=config.debug
)

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
    logger.info(f"Starting CPU stress: {load_percent}% load for {duration_sec} seconds.")
    while time.time() < end_time:
        # Perform CPU-bound operations
        [x**2 for x in range(10000)]
        # Sleep to achieve desired load
        time.sleep((100 - load_percent) / 100.0)
    logger.info("CPU stress completed.")
    CPU_USAGE.labels(job="extractor").set(0)  # Reset CPU usage after stress

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
    allocated_memory = None
    temp_file_path = None
    cpu_process = None
    
    try:
        # Optional: Stress Memory
        if stress_memory:
            logger.info(f"Starting memory stress: Allocating {memory_size_mb} MB.")
            allocated_memory = generate_large_string(memory_size_mb)
            MEMORY_USAGE.labels(job="extractor").set(len(allocated_memory.encode('utf-8')))
            logger.info(f"Memory stress completed: Allocated {memory_size_mb} MB.")
        
        # Optional: Stress Disk
        if stress_disk:
            logger.info(f"Starting disk stress: Allocating {disk_size_mb} MB.")
            temp_dir = tempfile.gettempdir()
            temp_file = tempfile.NamedTemporaryFile(delete=False, dir=temp_dir, suffix='.tmp')
            temp_file_path = temp_file.name
            # Write random data to the file
            data = generate_large_string(disk_size_mb)
            temp_file.write(data.encode('utf-8'))
            temp_file.close()
            # Update disk usage metric
            disk_usage_bytes = os.path.getsize(temp_file_path)
            DISK_USAGE.labels(job="extractor").set(disk_usage_bytes)
            logger.info(f"Disk stress completed: Allocated {disk_size_mb} MB at {temp_file_path}.")
        
        # Optional: Stress CPU
        if stress_cpu:
            logger.info(f"Starting CPU stress: {cpu_load_percent}% load for {cpu_duration_sec} seconds.")
            CPU_USAGE.labels(job="extractor").set(cpu_load_percent)
            cpu_process = multiprocessing.Process(target=cpu_stress, args=(cpu_load_percent, cpu_duration_sec))
            cpu_process.start()
        
        # Placeholder for actual processing logic
        # Simulate processing with a sleep
        logger.info(f"Processing URL: {url}")
        time.sleep(0.5)  # Simulate processing time
        
        # Update metrics
        etl_processed_documents_total.labels(job="extractor").inc()
        PROCESSING_TIME.labels(job="extractor").observe(time.time() - start_time)
        logger.info(f"Processed URL: {url} in {time.time() - start_time:.2f} seconds.")
        
        # Wait for CPU stress to complete
        if cpu_process:
            cpu_process.join()
        
        # Cleanup allocated resources to prevent memory leaks
        if stress_memory:
            del allocated_memory
            MEMORY_USAGE.labels(job="extractor").set(0)
            logger.info("Memory stress cleanup completed.")
        
        if stress_disk:
            os.remove(temp_file_path)
            DISK_USAGE.labels(job="extractor").set(0)
            logger.info("Disk stress cleanup completed.")
        
        return {
            "message": f"Processing URL: {url}",
            "minio_endpoint": config.minio_endpoint,
            "stress_memory": stress_memory,
            "stress_disk": stress_disk,
            "stress_cpu": stress_cpu
        }
    
    except Exception as e:
        etl_processing_errors_total.labels(job="extractor").inc()
        logger.error(f"Error processing URL: {e}")
        # Ensure cleanup in case of exception
        if cpu_process and cpu_process.is_alive():
            cpu_process.terminate()
            CPU_USAGE.labels(job="extractor").set(0)
            logger.info("CPU stress terminated due to error.")
        if stress_memory and allocated_memory:
            del allocated_memory
            MEMORY_USAGE.labels(job="extractor").set(0)
            logger.info("Memory stress cleanup after error completed.")
        if stress_disk and temp_file_path and os.path.exists(temp_file_path):
            os.remove(temp_file_path)
            DISK_USAGE.labels(job="extractor").set(0)
            logger.info("Disk stress cleanup after error completed.")
        raise HTTPException(status_code=500, detail=str(e))

# Initialize Prometheus Instrumentator after defining custom metrics
instrumentator = Instrumentator()

# Optionally, include additional metrics or customization here
instrumentator.instrument(app).expose(app)
