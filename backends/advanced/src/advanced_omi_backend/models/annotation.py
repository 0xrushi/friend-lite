from datetime import datetime
from typing import Optional, List
from pydantic import Field
from beanie import Document, Indexed
from enum import Enum
import uuid

class TranscriptAnnotation(Document):
    """Model for transcript annotations/corrections."""
    
    class AnnotationStatus(str, Enum):
        PENDING = "pending"
        ACCEPTED = "accepted"
        REJECTED = "rejected"

    class AnnotationSource(str, Enum):
        USER = "user"
        MODEL_SUGGESTION = "model_suggestion"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    conversation_id: Indexed(str)
    segment_index: int
    original_text: str
    corrected_text: str
    user_id: Indexed(str)
    
    status: AnnotationStatus = Field(default=AnnotationStatus.ACCEPTED) # User edits are accepted by default
    source: AnnotationSource = Field(default=AnnotationSource.USER)
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "transcript_annotations"
        indexes = [
            "conversation_id",
            "user_id",
            "status"
        ]
