"""
Unified annotation system for Chronicle.

Supports annotations for memories, transcripts, and future content types.
Enables both user edits and AI-powered suggestions.
"""

from enum import Enum
from typing import Optional
from datetime import datetime, timezone
import uuid

from beanie import Document, Indexed
from pydantic import BaseModel, Field


class AnnotationType(str, Enum):
    """Type of content being annotated."""
    MEMORY = "memory"
    TRANSCRIPT = "transcript"


class AnnotationSource(str, Enum):
    """Origin of the annotation."""
    USER = "user"  # User-created edit
    MODEL_SUGGESTION = "model_suggestion"  # AI-generated suggestion


class AnnotationStatus(str, Enum):
    """Lifecycle status of annotation."""
    PENDING = "pending"  # Waiting for user review (suggestions)
    ACCEPTED = "accepted"  # Applied to content
    REJECTED = "rejected"  # User dismissed suggestion


class Annotation(Document):
    """
    Unified annotation model for all content types.

    Supports both user edits and AI-powered suggestions across
    memories, transcripts, and future content types (chat, action items, etc.).

    Design: Polymorphic model with type-specific fields based on annotation_type.
    """

    # Identity
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))

    # Classification
    annotation_type: AnnotationType
    user_id: Indexed(str)
    source: AnnotationSource = Field(default=AnnotationSource.USER)
    status: AnnotationStatus = Field(default=AnnotationStatus.ACCEPTED)

    # Content
    original_text: str  # Text before correction
    corrected_text: str  # Text after correction

    # Polymorphic References (based on annotation_type)
    # For MEMORY annotations:
    memory_id: Optional[str] = None

    # For TRANSCRIPT annotations:
    conversation_id: Optional[str] = None
    segment_index: Optional[int] = None

    # Timestamps (Python 3.12+ compatible)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    class Settings:
        name = "annotations"
        # Create indexes on commonly queried fields
        # Note: Enum fields and Optional fields don't use Indexed() wrapper
        indexes = [
            "annotation_type",  # Query by type (memory vs transcript)
            "user_id",  # User-scoped queries
            "status",  # Filter by status (pending/accepted/rejected)
            "memory_id",  # Lookup annotations for specific memory
            "conversation_id",  # Lookup annotations for specific conversation
        ]

    def is_memory_annotation(self) -> bool:
        """Check if this is a memory annotation."""
        return self.annotation_type == AnnotationType.MEMORY

    def is_transcript_annotation(self) -> bool:
        """Check if this is a transcript annotation."""
        return self.annotation_type == AnnotationType.TRANSCRIPT

    def is_pending_suggestion(self) -> bool:
        """Check if this is a pending AI suggestion."""
        return (
            self.source == AnnotationSource.MODEL_SUGGESTION
            and self.status == AnnotationStatus.PENDING
        )


# Pydantic Request/Response Models


class AnnotationCreateBase(BaseModel):
    """Base model for annotation creation."""
    original_text: str
    corrected_text: str
    status: AnnotationStatus = AnnotationStatus.ACCEPTED


class MemoryAnnotationCreate(AnnotationCreateBase):
    """Create memory annotation request."""
    memory_id: str


class TranscriptAnnotationCreate(AnnotationCreateBase):
    """Create transcript annotation request."""
    conversation_id: str
    segment_index: int


class AnnotationResponse(BaseModel):
    """Annotation response for API."""
    id: str
    annotation_type: AnnotationType
    user_id: str
    memory_id: Optional[str] = None
    conversation_id: Optional[str] = None
    segment_index: Optional[int] = None
    original_text: str
    corrected_text: str
    status: AnnotationStatus
    source: AnnotationSource
    created_at: datetime

    class Config:
        from_attributes = True  # Pydantic v2 compatibility
