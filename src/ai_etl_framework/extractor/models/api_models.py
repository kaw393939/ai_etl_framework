from pydantic import BaseModel, HttpUrl
from typing import Optional, Dict
from datetime import datetime

class TaskRequest(BaseModel):
    url: str

class TaskStats(BaseModel):
    progress: float = 0.0
    total_bytes: int = 0
    downloaded_bytes: int = 0
    speed: float = 0.0
    eta: float = 0.0

class TranscriptionMetadataResponse(BaseModel):
    word_count: Optional[int] = None
    detected_language: Optional[str] = None
    language_probability: Optional[float] = None
    merged_transcript_path: Optional[str] = None

class TaskResponse(BaseModel):
    id: str
    url: str
    title: str = ""
    status: str
    error: Optional[str] = None
    created_at: datetime
    stats: Optional[TaskStats] = None
    metadata: Dict = {}
    video_metadata: Dict = {}
    transcription_metadata: Optional[TranscriptionMetadataResponse] = None

class StreamingTaskStats(BaseModel):
    """Minimal stats for streaming updates"""
    progress: float = 0.0
    eta: float = 0.0

class StreamingTaskResponse(BaseModel):
    """Streamlined response model for status updates"""
    id: str
    status: str
    progress: float = 0.0
    error: Optional[str] = None

    @classmethod
    def from_task(cls, task_response: 'TaskResponse') -> 'StreamingTaskResponse':
        """Convert full task response to streaming response"""
        return cls(
            id=task_response.id,
            status=task_response.status,
            progress=task_response.stats.progress if task_response.stats else 0.0,
            error=task_response.error
        )