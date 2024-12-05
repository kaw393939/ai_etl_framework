from datetime import datetime
from threading import RLock
from contextlib import contextmanager
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field, ConfigDict
import uuid

from .api_models import TaskStatus, TaskStats, TaskMetadata, TaskError, StreamingTaskResponse, TaskResponse


class TranscriptionTask(BaseModel):
    """
    Core task model for managing transcription processes with thread-safe operations.
    """
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    url: str
    status: TaskStatus = TaskStatus.PENDING
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    stats: TaskStats = Field(default_factory=TaskStats)
    metadata: TaskMetadata = Field(default_factory=TaskMetadata)
    errors: List[TaskError] = Field(default_factory=list)
    temp_video_path: Optional[str] = None

    # Private attributes for thread safety
    lock: RLock = Field(default_factory=RLock, exclude=True)

    model_config = ConfigDict(arbitrary_types_allowed=True)

    @contextmanager
    def atomic(self):
        """Context manager for thread-safe operations"""
        with self.lock:
            yield self
            self.updated_at = datetime.now()

    def update_status(self, new_status: TaskStatus) -> bool:
        """
        Thread-safe status update with validation
        Returns True if status was updated, False if invalid transition
        """
        with self.atomic() as task:
            if task.status.can_transition_to(new_status):
                task.status = new_status
                return True
            return False

    def add_error(self, message: str, details: Optional[Dict[str, Any]] = None) -> None:
        """Add an error for the current processing stage"""
        with self.atomic() as task:
            error = TaskError(
                stage=task.status.value,
                message=message,
                details=details
            )
            task.errors.append(error)

    def update_progress(self, progress: float) -> None:
        """Update task progress in a thread-safe manner"""
        with self.atomic() as task:
            task.stats.progress = min(max(progress, 0.0), 100.0)

    def update_metadata(self, **kwargs) -> None:
        """Update task metadata fields"""
        with self.atomic() as task:
            for key, value in kwargs.items():
                if hasattr(task.metadata, key):
                    setattr(task.metadata, key, value)

    def can_resume(self) -> bool:
        """Check if task can be resumed"""
        return self.status in {
            TaskStatus.FAILED,
            TaskStatus.CANCELLED,
            TaskStatus.PAUSED
        }

    @property
    def latest_error(self) -> Optional[TaskError]:
        """Get the most recent error if any exist"""
        return self.errors[-1] if self.errors else None

    @property
    def title(self) -> str:
        """Get the processed title from video metadata"""
        return self.metadata.video.processed_title

    @property
    def duration(self) -> Optional[float]:
        """Get video duration from metadata"""
        return self.metadata.video.duration

    def to_response(self) -> 'TaskResponse':
        """Convert task to API response model"""
        from .api_models import TaskResponse
        return TaskResponse(
            id=self.id,
            url=self.url,
            status=self.status,
            created_at=self.created_at,
            updated_at=self.updated_at,
            metadata=self.metadata,
            stats=self.stats,
            errors=self.errors
        )

    def to_streaming_response(self) -> 'StreamingTaskResponse':
        """Convert task to streaming response model"""
        from .api_models import StreamingTaskResponse
        return StreamingTaskResponse.from_task(self.to_response())