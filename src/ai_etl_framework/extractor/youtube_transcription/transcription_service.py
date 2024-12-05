import asyncio
import time
from datetime import datetime
from fastapi import HTTPException

from ai_etl_framework.common.logger import setup_logger
from ai_etl_framework.extractor.models.api_models import (
    TaskRequest, TaskResponse, TaskStatus, StreamingTaskResponse
)
from ai_etl_framework.extractor.youtube_transcription.manager import TranscriptionManager
from ai_etl_framework.extractor.models.tasks import TranscriptionTask
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

logger = setup_logger(__name__)


class TranscriptionService:
    def __init__(self):
        logger.info("[TranscriptionService] Initializing TranscriptionService")
        self._manager = TranscriptionManager()
        self._update_worker_metrics()

        # Stage weights for progress calculation
        self.stage_weights = {
            TaskStatus.DOWNLOADING: 0.2,
            TaskStatus.SPLITTING: 0.1,
            TaskStatus.TRANSCRIBING: 0.6,
            TaskStatus.MERGING: 0.1
        }

        logger.info("[TranscriptionService] Service initialized with stage weights")

    def _sanitize_status(self, status: TaskStatus) -> str:
        """Convert status to metric-safe format."""
        return status.value.lower().replace(" ", "_")

    def calculate_overall_progress(self, task: TranscriptionTask) -> float:
        """Calculate weighted overall progress across all stages."""
        logger.debug(
            f"[TranscriptionService] Calculating overall progress for task {task.id}, current status: {task.status}"
        )

        if task.status == TaskStatus.COMPLETED:
            return 100.0
        elif task.status == TaskStatus.FAILED:
            return task.stats.progress

        current_stage_weight = self.stage_weights.get(task.status, 0.0)
        if current_stage_weight == 0.0:
            return 0.0

        # Calculate completed stages
        completed_progress = sum(
            weight for stage, weight in self.stage_weights.items()
            if stage.value < task.status.value and stage != TaskStatus.FAILED
        )

        # Add current stage progress
        current_progress = (task.stats.progress / 100.0) * current_stage_weight
        total_progress = (completed_progress + current_progress) * 100.0

        return min(99.9, total_progress)

    async def stream_status(self, task: TranscriptionTask):
        """Stream task status with continuous progress tracking."""
        logger.info(f"[TranscriptionService] Starting status streaming for task {task.id}")
        start_time = time.time()
        previous_status = None
        previous_progress = 0.0

        while True:
            try:
                current_status = task.status

                # Handle status changes
                if current_status != previous_status:
                    logger.info(f"[TranscriptionService] Task {task.id} status changed: "
                                f"{previous_status} -> {current_status}")
                    if previous_status:
                        TASK_STATUS.labels(
                            status=self._sanitize_status(previous_status)
                        ).inc()
                    previous_status = current_status
                    previous_progress = 0.0

                overall_progress = self.calculate_overall_progress(task)

                # Determine if update should be sent
                should_update = (
                        overall_progress - previous_progress >= 0.1 or
                        current_status != previous_status or
                        current_status in (TaskStatus.FAILED, TaskStatus.COMPLETED)
                )

                if should_update:


                    # Create and send response
                    streaming_response = task.to_streaming_response()
                    response_data = f"data: {streaming_response.model_dump_json()}\n\n"

                    logger.debug(
                        f"[TranscriptionService] Status update for task {task.id}: "
                        f"status={current_status}, progress={overall_progress:.1f}%, "
                        f"error={task.latest_error.message if task.latest_error else 'None'}"
                    )
                    yield response_data

                    previous_progress = overall_progress

                    # Handle completion states
                    if current_status == TaskStatus.FAILED:
                        processing_time = time.time() - start_time
                        logger.error(
                            f"[TranscriptionService] Task {task.id} failed after {processing_time:.2f}s "
                            f"with error: {task.latest_error.message if task.latest_error else 'Unknown error'}"
                        )
                        DOCUMENTS_PROCESSED.labels(status="failure").inc()
                        ERROR_COUNTER.labels(
                            error_type="task_failure",
                            stage=self._sanitize_status(current_status)
                        ).inc()
                        break

                    elif current_status == TaskStatus.COMPLETED:
                        processing_time = time.time() - start_time
                        DOCUMENT_PROCESSING_TIME.observe(processing_time)
                        logger.info(
                            f"[TranscriptionService] Task {task.id} completed in {processing_time:.2f}s"
                        )
                        DOCUMENTS_PROCESSED.labels(status="success").inc()

                        # Track word count metrics
                        word_count = task.metadata.transcription.word_count
                        if word_count:
                            TOKENS_PROCESSED.labels(type="input").inc(word_count)
                            TOKENS_PER_DOCUMENT.labels(type="input").observe(word_count)
                            logger.info(f"[TranscriptionService] Task {task.id} processed {word_count} tokens")
                        break

                    # Update queue metrics
                    QUEUE_DEPTH.set(self._manager.task_queue.qsize())

                    # Track document size if available
                    if 'total_size' in task.metadata.processing:
                        try:
                            # Convert size string to bytes if it's a string
                            size_str = task.metadata.processing['total_size']
                            if isinstance(size_str, str):
                                # Parse size like "11.49MB" to bytes
                                value = float(size_str.replace("MB", ""))
                                size_in_bytes = value * 1024 * 1024  # Convert MB to bytes
                                DOCUMENT_SIZE.observe(size_in_bytes)
                            else:
                                # If it's already a number, use it directly
                                DOCUMENT_SIZE.observe(task.metadata.processing['total_size'])
                        except (ValueError, TypeError) as e:
                            logger.warning(f"Could not process document size metric: {e}")

                await asyncio.sleep(0.5)

            except Exception as e:
                logger.exception(
                    f"[TranscriptionService] Error in stream_status for task {task.id}: {str(e)}"
                )
                task.add_error(f"Status streaming error: {str(e)}")
                streaming_response = task.to_streaming_response()
                yield f"data: {streaming_response.model_dump_json()}\n\n"
                break

    def _update_worker_metrics(self):
        """Update worker pool metrics."""
        active_workers = len([w for w in self._manager.workers if w.is_alive()])
        total_workers = len(self._manager.workers)

        logger.debug(
            f"[TranscriptionService] Worker metrics - Active: {active_workers}, "
            f"Idle: {total_workers - active_workers}, Total: {total_workers}"
        )

        WORKER_STATUS.labels(state="active").set(active_workers)
        WORKER_STATUS.labels(state="idle").set(total_workers - active_workers)
        WORKER_STATUS.labels(state="total").set(total_workers)

    def add_task(self, url: str) -> TranscriptionTask:
        """Add a new task with metrics tracking."""
        logger.info(f"[TranscriptionService] Adding new task for URL: {url}")

        task = self._manager.add_task(url)
        if not task:
            logger.error(f"[TranscriptionService] Failed to add task for URL: {url}")
            ERROR_COUNTER.labels(
                error_type="queue_full",
                stage="task_creation"
            ).inc()
            raise HTTPException(
                status_code=400,
                detail="Failed to add task. Queue might be full or URL already exists."
            )

        QUEUE_DEPTH.set(self._manager.task_queue.qsize())
        TASK_STATUS.labels(status="pending").inc()

        logger.info(f"[TranscriptionService] Added task {task.id} for URL: {url}")
        return task

    def shutdown(self):
        """Shutdown service with final metric updates."""
        logger.info("[TranscriptionService] Initiating shutdown")
        try:
            self._manager.shutdown()
            self._update_worker_metrics()
            logger.info("[TranscriptionService] Shutdown completed successfully")
        except Exception as e:
            logger.exception(f"[TranscriptionService] Error during shutdown: {str(e)}")
            ERROR_COUNTER.labels(
                error_type="shutdown_error",
                stage="service_shutdown"
            ).inc()