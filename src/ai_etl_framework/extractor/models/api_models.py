from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, HttpUrl, Field

class TaskStatus(str, Enum):
    PENDING = 'Pending'
    DOWNLOADING = 'Downloading'
    SPLITTING = 'Splitting'
    TRANSCRIBING = 'Transcribing'
    MERGING = 'Merging'
    COMPLETED = 'Completed'
    FAILED = 'Failed'
    CANCELLED = 'Cancelled'
    PAUSED = 'Paused'

    @classmethod
    def transitions(cls) -> Dict[str, List[str]]:
        return {
            cls.PENDING.value: [cls.DOWNLOADING.value, cls.FAILED.value, cls.CANCELLED.value],
            cls.DOWNLOADING.value: [cls.SPLITTING.value, cls.FAILED.value, cls.PAUSED.value, cls.CANCELLED.value],
            cls.SPLITTING.value: [cls.TRANSCRIBING.value, cls.FAILED.value, cls.PAUSED.value, cls.CANCELLED.value],
            cls.TRANSCRIBING.value: [cls.MERGING.value, cls.FAILED.value, cls.PAUSED.value, cls.CANCELLED.value],
            cls.MERGING.value: [cls.COMPLETED.value, cls.FAILED.value, cls.PAUSED.value, cls.CANCELLED.value],
            cls.COMPLETED.value: [cls.FAILED.value],
            cls.FAILED.value: [cls.PENDING.value],
            cls.CANCELLED.value: [cls.PENDING.value],
            cls.PAUSED.value: [cls.PENDING.value, cls.FAILED.value, cls.CANCELLED.value]
        }

    def can_transition_to(self, new_status: 'TaskStatus') -> bool:
        """Check if current status can transition to new status."""
        valid_transitions = self.transitions().get(self.value, [])
        return new_status.value in valid_transitions
class TaskStats(BaseModel):
    progress: float = Field(default=0.0, ge=0.0, le=100.0)
    total_bytes: int = Field(default=0, ge=0)
    downloaded_bytes: int = Field(default=0, ge=0)
    speed: float = Field(default=0.0, ge=0.0)

    @property
    def streaming_stats(self) -> dict:
        """Get minimal stats for streaming updates"""
        return {
            "progress": self.progress,
            "eta": self.eta
        }

class VideoMetadata(BaseModel):
    title: str = ""
    description: Optional[str] = None
    duration: Optional[float] = None
    upload_date: Optional[str] = None
    uploader: Optional[str] = None
    channel_id: Optional[str] = None
    view_count: Optional[int] = None
    like_count: Optional[int] = None
    comment_count: Optional[int] = None
    tags: List[str] = Field(default_factory=list)
    categories: List[str] = Field(default_factory=list)
    language: Optional[str] = None
    format_id: Optional[str] = None
    ext: Optional[str] = None
    audio_channels: Optional[int] = None
    filesize_approx: Optional[int] = None
    duration_string: Optional[str] = None
    processed_title: str = ""

class TranscriptionMetadata(BaseModel):
    word_count: Optional[int] = None
    detected_language: Optional[str] = None
    language_probability: Optional[float] = Field(None, ge=0.0, le=1.0)
    merged_transcript_path: Optional[str] = None
    confidence_scores: List[float] = Field(default_factory=list)
    average_confidence: Optional[float] = None
    total_duration: Optional[float] = None
    chunk_count: Optional[int] = None

class TaskError(BaseModel):
    stage: str
    message: str
    timestamp: datetime = Field(default_factory=datetime.now)
    details: Optional[Dict[str, Any]] = None

class TaskMetadata(BaseModel):
    video: VideoMetadata = Field(default_factory=VideoMetadata)
    transcription: TranscriptionMetadata = Field(default_factory=TranscriptionMetadata)
    processing: Dict[str, Any] = Field(default_factory=dict)
    download_completed_at: Optional[datetime] = None
    processing_started_at: Optional[datetime] = None
    processing_completed_at: Optional[datetime] = None

class TaskRequest(BaseModel):
    url: str
    language: Optional[str] = None
    chunk_duration: Optional[int] = Field(None, gt=0)
    priority: int = Field(default=0, ge=0, le=10)

class BaseTaskResponse(BaseModel):
    id: str
    status: TaskStatus
    error: Optional[str] = None
    created_at: datetime
    updated_at: datetime

class StreamingTaskResponse(BaseTaskResponse):
    progress: float = Field(0.0, ge=0.0, le=100.0)
    eta: float = 0.0
    current_stage: Optional[str] = None

    @classmethod
    def from_task(cls, task: 'TaskResponse') -> 'StreamingTaskResponse':
        return cls(
            id=task.id,
            status=task.status,
            progress=task.stats.progress if task.stats else 0.0,
            error=task.latest_error.message if task.latest_error else None,
            created_at=task.created_at,
            updated_at=task.updated_at,
            current_stage=task.status.value
        )

class TaskResponse(BaseTaskResponse):
    url: str
    metadata: TaskMetadata = Field(default_factory=TaskMetadata)
    stats: TaskStats = Field(default_factory=TaskStats)
    errors: List[TaskError] = Field(default_factory=list)

    @property
    def latest_error(self) -> Optional[TaskError]:
        """Get the most recent error if any exist"""
        return self.errors[-1] if self.errors else None

    class Config:
        from_attributes = True