from prometheus_client import Counter, Histogram, Gauge

# Existing metrics
TASK_COUNTER = Counter(
    'transcription_tasks_total',
    'Total number of youtube_transcription tasks created'
)

TASK_STATUS_COUNTER = Counter(
    'transcription_task_status_total',
    'Total number of task status changes',
    ['status']
)

TASK_PROCESSING_TIME = Histogram(
    'transcription_processing_duration_seconds',
    'Duration of youtube_transcription processing in seconds'
)

DOWNLOAD_SPEED_GAUGE = Gauge(
    'transcription_download_speed_bytes',
    'Current download speed in bytes per second'
)

DOWNLOAD_PROGRESS_GAUGE = Gauge(
    'transcription_download_progress_percent',
    'Current download progress as percentage'
)

# System Metrics
MEMORY_USAGE = Gauge(
    'transcription_memory_usage_bytes',
    'Memory usage of the youtube_transcription service',
    ['type']  # heap, stack, etc.
)

CPU_USAGE = Gauge(
    'transcription_cpu_usage_percent',
    'CPU usage percentage of the youtube_transcription service'
)

DISK_IO = Counter(
    'transcription_disk_io_bytes',
    'Disk I/O operations',
    ['operation']  # read, write
)

NETWORK_IO = Counter(
    'transcription_network_io_bytes',
    'Network I/O operations',
    ['direction']  # in, out
)

# Processing Stage Metrics
STAGE_COUNTER = Counter(
    'transcription_stage_total',
    'Count of tasks per processing stage',
    ['stage', 'status']  # stage: download, split, transcribe, merge; status: success, failure
)

STAGE_PROCESSING_TIME = Histogram(
    'transcription_stage_duration_seconds',
    'Processing time per stage',
    ['stage'],
    buckets=(1, 5, 10, 30, 60, 120, 300, 600, 1800, 3600)
)

# Resource Usage During Processing
STAGE_MEMORY_USAGE = Gauge(
    'transcription_stage_memory_bytes',
    'Memory usage per processing stage',
    ['stage']
)

STAGE_CPU_USAGE = Gauge(
    'transcription_stage_cpu_percent',
    'CPU usage per processing stage',
    ['stage']
)

# Queue Metrics
QUEUE_SIZE = Gauge(
    'transcription_queue_size',
    'Current number of tasks in queue'
)

QUEUE_LATENCY = Histogram(
    'transcription_queue_latency_seconds',
    'Time spent in queue before processing'
)

# File Processing Metrics
FILE_SIZE = Histogram(
    'transcription_file_size_bytes',
    'Size of processed files',
    buckets=(1e6, 5e6, 10e6, 50e6, 100e6, 500e6, 1e9)  # 1MB to 1GB
)

CHUNK_COUNT = Histogram(
    'transcription_chunks_per_file',
    'Number of chunks per file processed'
)

# API Metrics
API_REQUESTS = Counter(
    'transcription_api_requests_total',
    'Total API requests',
    ['endpoint', 'method', 'status_code']
)

API_LATENCY = Histogram(
    'transcription_api_latency_seconds',
    'API endpoint latency',
    ['endpoint'],
    buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0)
)

# Error Metrics
ERROR_COUNTER = Counter(
    'transcription_errors_total',
    'Count of errors by type',
    ['type', 'stage']  # type: system, validation, processing
)

# Quality Metrics
TRANSCRIPTION_QUALITY = Histogram(
    'transcription_quality_score',
    'Quality metrics for transcriptions',
    ['metric_type']  # confidence, word_error_rate
)

# Resource Pool Metrics
WORKER_POOL = Gauge(
    'transcription_worker_pool',
    'Worker pool statistics',
    ['state']  # active, idle, total
)

# Batch Processing Metrics
BATCH_PROCESSING = Histogram(
    'transcription_batch_processing',
    'Batch processing statistics',
    ['operation']
)