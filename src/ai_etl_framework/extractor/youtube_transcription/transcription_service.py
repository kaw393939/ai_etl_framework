import asyncio
import json
import time
from datetime import datetime
from fastapi import HTTPException
from json import JSONEncoder
import psutil

from ai_etl_framework.extractor.models.tasks import TranscriptionTask, TaskStatus
from ai_etl_framework.extractor.models.api_models import TaskResponse, TaskStats, TranscriptionMetadataResponse, \
    StreamingTaskResponse
from ai_etl_framework.extractor.youtube_transcription.manager import TranscriptionManager
from ai_etl_framework.common.metrics import (
    DOCUMENTS_PROCESSED,
    DOCUMENT_PROCESSING_TIME,
    DOCUMENT_SIZE,
    TOKENS_PROCESSED,
    TOKENS_PER_DOCUMENT,
    TASK_STATUS,
    QUEUE_DEPTH,
    WORKER_STATUS,
    ERROR_COUNTER,
)


class DateTimeEncoder(JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)


class TranscriptionService:
    def __init__(self):
        self._manager = TranscriptionManager()
        self._update_worker_metrics()

        # Define stage weights for overall progress calculation
        self.stage_weights = {
            TaskStatus.DOWNLOADING: 0.2,
            TaskStatus.SPLITTING: 0.1,
            TaskStatus.TRANSCRIBING: 0.6,
            TaskStatus.MERGING: 0.1
        }

        # Track progress for each stage
        self.stage_progress = {
            TaskStatus.DOWNLOADING: 0.0,
            TaskStatus.SPLITTING: 0.0,
            TaskStatus.TRANSCRIBING: 0.0,
            TaskStatus.MERGING: 0.0
        }

    def calculate_overall_progress(self, task: TranscriptionTask) -> float:
        """Calculate weighted overall progress across all stages."""
        if task.status == TaskStatus.COMPLETED:
            return 100.0
        elif task.status == TaskStatus.FAILED:
            return self.stage_progress[task.status] if task.status in self.stage_progress else 0.0

        current_stage_weight = self.stage_weights.get(task.status, 0.0)
        if current_stage_weight == 0.0:
            return 0.0

        # Calculate completed stages progress
        completed_progress = 0.0
        for stage, weight in self.stage_weights.items():
            if self.stage_progress[stage] >= 100.0:
                completed_progress += weight

        # Add current stage progress
        current_progress = (self.stage_progress[task.status] / 100.0) * current_stage_weight

        # Convert to percentage
        total_progress = (completed_progress + current_progress) * 100.0
        return min(99.9, total_progress)  # Cap at 99.9% until fully complete

    def update_stage_progress(self, task: TranscriptionTask, progress: float):
        """Update progress for the current stage."""
        if task.status in self.stage_progress:
            self.stage_progress[task.status] = progress

    async def stream_status(self, task: TranscriptionTask):
        """Stream task status with continuous progress tracking."""
        start_time = time.time()
        previous_status = None
        previous_progress = 0.0

        while True:
            try:
                current_status = task.status

                # Track status transitions
                if current_status != previous_status:
                    if previous_status:
                        # Mark previous stage as complete
                        self.stage_progress[previous_status] = 100.0
                        TASK_STATUS.labels(status=previous_status.value).inc()
                    previous_status = current_status
                    previous_progress = 0.0

                # Update current stage progress based on task stats
                if task.stats and current_status in self.stage_progress:
                    self.stage_progress[current_status] = task.stats.progress

                # Calculate overall progress
                overall_progress = self.calculate_overall_progress(task)

                # Only yield if there's a meaningful change in progress or status
                if (overall_progress - previous_progress >= 0.1 or
                        current_status != previous_status):

                    # Update task stats with overall progress
                    if task.stats:
                        task.stats.progress = overall_progress
                        if task.stats.total_bytes > 0:
                            elapsed_time = time.time() - start_time
                            remaining_progress = 100.0 - overall_progress
                            if remaining_progress > 0:
                                task.stats.eta = (elapsed_time / overall_progress) * remaining_progress

                    # Generate response
                    response = self._task_to_response(task)
                    streaming_response = StreamingTaskResponse.from_task(response)
                    yield f"data: {streaming_response.model_dump_json()}\n\n"

                    previous_progress = overall_progress

                # Handle completion states
                if current_status in [TaskStatus.COMPLETED, TaskStatus.FAILED]:
                    processing_time = time.time() - start_time
                    DOCUMENT_PROCESSING_TIME.observe(processing_time)

                    if current_status == TaskStatus.COMPLETED:
                        DOCUMENTS_PROCESSED.labels(status="success").inc()
                        if hasattr(task, 'transcription_metadata'):
                            input_tokens = task.transcription_metadata.word_count
                            TOKENS_PROCESSED.labels(type="input").inc(input_tokens)
                            TOKENS_PER_DOCUMENT.labels(type="input").observe(input_tokens)
                    else:
                        DOCUMENTS_PROCESSED.labels(status="failure").inc()
                        ERROR_COUNTER.labels(
                            error_type="processing_failed",
                            stage="document_processing"
                        ).inc()
                    break

                # Update metrics
                QUEUE_DEPTH.set(self._manager.task_queue.qsize())
                if hasattr(task, 'file_size'):
                    DOCUMENT_SIZE.observe(task.file_size)

                await asyncio.sleep(0.5)

            except Exception as e:
                ERROR_COUNTER.labels(
                    error_type="stream_status_error",
                    stage="status_streaming"
                ).inc()
                print(f"Error in stream_status: {e}")
                break


    def _update_worker_metrics(self):
        """Update worker pool metrics."""
        active_workers = len([w for w in self._manager.workers if w.is_alive()])
        total_workers = len(self._manager.workers)

        WORKER_STATUS.labels(state="active").set(active_workers)
        WORKER_STATUS.labels(state="idle").set(total_workers - active_workers)
        WORKER_STATUS.labels(state="total").set(total_workers)


    def add_task(self, url: str) -> TranscriptionTask:
        """Add a new task with metrics tracking."""
        success = self._manager.add_task(url)
        if not success:
            ERROR_COUNTER.labels(
                error_type="queue_full",
                stage="task_creation"
            ).inc()
            raise HTTPException(
                status_code=400,
                detail="Failed to add task. Queue might be full or URL already exists."
            )

        # Update queue metrics
        QUEUE_DEPTH.set(self._manager.task_queue.qsize())
        TASK_STATUS.labels(status="pending").inc()

        task = self._manager.get_tasks()[-1]
        task.metrics_start_time = time.time()
        return task



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
        """Shutdown service with final metric updates."""
        try:
            self._manager.shutdown()
            # Final worker metrics update
            self._update_worker_metrics()
        except Exception as e:
            ERROR_COUNTER.labels(
                error_type="shutdown_error",
                stage="service_shutdown"
            ).inc()
            print(f"Error during shutdown: {e}")
