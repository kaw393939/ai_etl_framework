from prometheus_client import Counter, Histogram, Gauge

# Document Processing Core Metrics
DOCUMENTS_PROCESSED = Counter(
    'transcription_documents_processed_total',
    'Total number of documents processed',
    ['status']  # success, failure
)

DOCUMENT_PROCESSING_TIME = Histogram(
    'transcription_document_processing_seconds',
    'Time taken to process each document',
    buckets=(1, 5, 10, 30, 60, 120, 300, 600)
)

DOCUMENT_SIZE = Histogram(
    'transcription_document_size_bytes',
    'Size of documents being processed',
    buckets=(1000, 10000, 100000, 1000000, 10000000)
)

# Token Processing Metrics
TOKENS_PROCESSED = Counter(
    'transcription_tokens_processed_total',
    'Total number of tokens processed',
    ['type']  # input, output
)

TOKENS_PER_DOCUMENT = Histogram(
    'transcription_tokens_per_document',
    'Number of tokens per document',
    ['type'],  # input, output
    buckets=(100, 500, 1000, 2000, 5000, 10000, 20000)
)

# Task Status Metrics
TASK_STATUS = Counter(
    'transcription_task_status_total',
    'Count of tasks by status',
    ['status']  # pending, processing, completed, failed
)

# Processing Quality Metrics
PROCESSING_QUALITY = Histogram(
    'transcription_processing_quality',
    'Quality metrics for document processing',
    ['metric_type'],  # confidence_score, error_rate
    buckets=(0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0)
)

# Language Detection Metrics
DOCUMENT_LANGUAGES = Counter(
    'transcription_document_languages_total',
    'Count of documents by detected language',
    ['language']
)

# Chunk Processing Metrics
CHUNK_PROCESSING = Histogram(
    'transcription_chunk_processing_seconds',
    'Time taken to process individual chunks',
    buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0)
)

CHUNKS_PER_DOCUMENT = Histogram(
    'transcription_chunks_per_document',
    'Number of chunks per document processed',
    buckets=(1, 2, 5, 10, 20, 50)
)

# API Integration Metrics
API_REQUESTS = Counter(
    'transcription_api_requests_total',
    'Total API requests made',
    ['endpoint', 'status_code']
)

API_LATENCY = Histogram(
    'transcription_api_latency_seconds',
    'API request latency',
    ['endpoint'],
    buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0)
)

# Error Tracking
ERROR_COUNTER = Counter(
    'transcription_errors_total',
    'Count of errors by type',
    ['error_type', 'stage']  # validation, processing, api
)

# Batch Processing Metrics
BATCH_STATISTICS = Histogram(
    'transcription_batch_statistics',
    'Statistics for batch processing',
    ['metric_type'],  # batch_size, avg_tokens_per_doc, processing_time
    buckets=(1, 5, 10, 20, 50, 100)
)

# Queue Metrics (Essential ones only)
QUEUE_DEPTH = Gauge(
    'transcription_queue_current_depth',
    'Current number of documents in processing queue'
)

# Worker Pool Metrics
WORKER_STATUS = Gauge(
    'transcription_worker_status',
    'Current worker pool status',
    ['state']  # active, idle, total
)

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
