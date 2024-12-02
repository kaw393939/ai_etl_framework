import asyncio
import json
import time
from datetime import datetime
from fastapi import HTTPException
from json import JSONEncoder
import psutil

from ai_etl_framework.extractor.models.tasks import TranscriptionTask, TaskStatus
from ai_etl_framework.extractor.models.api_models import TaskResponse, TaskStats, TranscriptionMetadataResponse
from ai_etl_framework.extractor.youtube_transcription.manager import TranscriptionManager
from ai_etl_framework.common.metrics import (
    TASK_COUNTER,
    TASK_STATUS_COUNTER,
    TASK_PROCESSING_TIME,
    DOWNLOAD_SPEED_GAUGE,
    DOWNLOAD_PROGRESS_GAUGE,
    MEMORY_USAGE,
    CPU_USAGE,
    DISK_IO,
    NETWORK_IO,
    STAGE_COUNTER,
    STAGE_PROCESSING_TIME,
    STAGE_MEMORY_USAGE,
    STAGE_CPU_USAGE,
    QUEUE_SIZE,
    QUEUE_LATENCY,
    FILE_SIZE,
    CHUNK_COUNT,
    API_REQUESTS,
    API_LATENCY,
    ERROR_COUNTER,
    TRANSCRIPTION_QUALITY,
    WORKER_POOL,
    BATCH_PROCESSING
)

class DateTimeEncoder(JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)

class TranscriptionService:
    def __init__(self):
        self._manager = TranscriptionManager()
        self._update_system_metrics()

    def _update_system_metrics(self):
        # Update system metrics
        process = psutil.Process()

        # Memory metrics
        mem_info = process.memory_info()
        MEMORY_USAGE.labels(type="rss").set(mem_info.rss)
        MEMORY_USAGE.labels(type="vms").set(mem_info.vms)

        # CPU metrics
        CPU_USAGE.set(process.cpu_percent())

        # Disk I/O metrics
        io_counters = process.io_counters()
        DISK_IO.labels(operation="read").inc(io_counters.read_bytes)
        DISK_IO.labels(operation="write").inc(io_counters.write_bytes)

        # Network I/O metrics
        net_io = psutil.net_io_counters()
        NETWORK_IO.labels(direction="in").inc(net_io.bytes_recv)
        NETWORK_IO.labels(direction="out").inc(net_io.bytes_sent)

        # Update worker pool metrics (only total workers available)
        WORKER_POOL.labels(state="total").set(len(self._manager.workers))

    def add_task(self, url: str) -> TranscriptionTask:
        success = self._manager.add_task(url)
        if not success:
            raise HTTPException(
                status_code=400,
                detail="Failed to add task. Queue might be full or URL already exists."
            )
        TASK_COUNTER.inc()

        # Get the recently added task
        task = self._manager.get_tasks()[-1]
        # Record queue latency start time
        task.queue_start_time = time.time()
        return task

    async def stream_status(self, task: TranscriptionTask):
        """Stream task status updates with enhanced metrics tracking"""
        start_time = datetime.now()
        stage_start_time = time.time()
        current_stage = None
        last_status = None
        last_progress = None

        while True:
            try:
                current_status = task.status

                # Track stage transitions
                if current_status != current_stage:
                    if current_stage:
                        # Record previous stage duration
                        duration = time.time() - stage_start_time
                        STAGE_PROCESSING_TIME.labels(stage=current_stage.value).observe(duration)

                    # Start timing new stage
                    current_stage = current_status
                    stage_start_time = time.time()
                    STAGE_COUNTER.labels(
                        stage=current_stage.value,
                        status="start"
                    ).inc()

                # Update system metrics
                self._update_system_metrics()

                # Resource usage per stage
                process = psutil.Process()
                STAGE_MEMORY_USAGE.labels(stage=current_stage.value).set(
                    process.memory_info().rss
                )
                STAGE_CPU_USAGE.labels(stage=current_stage.value).set(
                    process.cpu_percent()
                )

                # Queue metrics
                QUEUE_SIZE.set(self._manager.task_queue.qsize())

                # Calculate queue latency
                if current_status != TaskStatus.PENDING and hasattr(task, 'queue_start_time'):
                    queue_latency = time.time() - task.queue_start_time
                    QUEUE_LATENCY.observe(queue_latency)
                    del task.queue_start_time  # Remove attribute after recording latency

                # Update task status counter
                if current_status != last_status:
                    TASK_STATUS_COUNTER.labels(status=current_status.value).inc()

                # Existing metrics...
                if task.stats:
                    DOWNLOAD_SPEED_GAUGE.set(task.stats.speed)
                    DOWNLOAD_PROGRESS_GAUGE.set(task.stats.progress)

                    # File size metrics
                    if task.stats.total_bytes > 0:
                        FILE_SIZE.observe(task.stats.total_bytes)

                # Update chunk count if available
                if hasattr(task, 'chunk_count'):
                    CHUNK_COUNT.observe(task.chunk_count)

                # Update youtube_transcription quality metrics if available
                if hasattr(task, 'transcription_quality'):
                    TRANSCRIPTION_QUALITY.labels(metric_type="confidence").observe(
                        task.transcription_quality.confidence
                    )
                    TRANSCRIPTION_QUALITY.labels(metric_type="word_error_rate").observe(
                        task.transcription_quality.word_error_rate
                    )

                # Check if status or progress has changed
                current_progress = task.stats.progress if task.stats else 0
                if (current_status != last_status or
                    abs(current_progress - (last_progress or 0)) >= 1.0):
                    response = self._task_to_response(task)
                    yield f"data: {json.dumps(response.model_dump(), cls=DateTimeEncoder)}\n\n"

                    last_status = current_status
                    last_progress = current_progress

                # Exit conditions with final metrics
                if current_status in [TaskStatus.COMPLETED, TaskStatus.FAILED]:
                    processing_time = (datetime.now() - start_time).total_seconds()
                    TASK_PROCESSING_TIME.observe(processing_time)

                    STAGE_COUNTER.labels(
                        stage=current_stage.value,
                        status="success" if current_status == TaskStatus.COMPLETED else "failure"
                    ).inc()
                    break

                await asyncio.sleep(0.5)

            except Exception as e:
                ERROR_COUNTER.labels(
                    type="processing",
                    stage=current_stage.value if current_stage else "unknown"
                ).inc()
                print(f"Error in stream_status: {e}")
                break

    def _task_to_response(self, task: TranscriptionTask) -> TaskResponse:
        try:
            stats = None
            if task.stats:
                stats = TaskStats(
                    progress=task.stats.progress,
                    total_bytes=task.stats.total_bytes,
                    downloaded_bytes=task.stats.downloaded_bytes,
                    speed=task.stats.speed,
                    eta=task.stats.eta
                )

            transcription_metadata = None
            if task.transcription_metadata:
                transcription_metadata = TranscriptionMetadataResponse(
                    word_count=task.transcription_metadata.word_count,
                    detected_language=task.transcription_metadata.detected_language,
                    language_probability=task.transcription_metadata.language_probability,
                    merged_transcript_path=task.transcription_metadata.merged_transcript_path
                )

            return TaskResponse(
                id=task.id,
                url=task.url,
                title=task.title or "",
                status=task.status.value,
                error=task.error,
                created_at=task.created_at,
                stats=stats,
                metadata=task.metadata or {},
                video_metadata=task.video_metadata or {},
                transcription_metadata=transcription_metadata
            )
        except Exception as e:
            ERROR_COUNTER.labels(type="response", stage="unknown").inc()
            print(f"Error in _task_to_response: {e}")
            raise

    def shutdown(self):
        self._manager.shutdown()
