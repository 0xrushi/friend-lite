import pytest
from datetime import datetime
from advanced_omi_backend.models.annotation import TranscriptAnnotation
from beanie import init_beanie
from mongomock_motor import AsyncMongoMockClient
import uuid

async def initialize_beanie():
    client = AsyncMongoMockClient()
    await init_beanie(database=client.db_name, document_models=[TranscriptAnnotation])

class TestAnnotationModel:
    """Test TranscriptAnnotation Pydantic/Beanie model."""

    @pytest.mark.asyncio
    async def test_create_annotation_defaults(self):
        """Test creating an annotation with default values."""
        await initialize_beanie()
        
        annotation = TranscriptAnnotation(
            conversation_id="conv-123",
            segment_index=5,
            original_text="Hello world",
            corrected_text="Hello, world!",
            user_id="user-456"
        )
        
        # Check required fields
        assert annotation.conversation_id == "conv-123"
        assert annotation.segment_index == 5
        assert annotation.original_text == "Hello world"
        assert annotation.corrected_text == "Hello, world!"
        assert annotation.user_id == "user-456"

        # Check defaults
        assert isinstance(annotation.id, str)
        assert len(annotation.id) > 0
        assert annotation.status == TranscriptAnnotation.AnnotationStatus.ACCEPTED
        assert annotation.source == TranscriptAnnotation.AnnotationSource.USER
        assert isinstance(annotation.created_at, datetime)
        assert isinstance(annotation.updated_at, datetime)

    @pytest.mark.asyncio
    async def test_annotation_status_enum(self):
        """Test that status enum works as expected."""
        await initialize_beanie()

        # Test valid statuses
        for status in ["pending", "accepted", "rejected"]:
            annotation = TranscriptAnnotation(
                conversation_id="c", segment_index=0, original_text="o", corrected_text="c", user_id="u",
                status=status
            )
            assert annotation.status == status

        # Test validation error (Pydantic validates enums)
        with pytest.raises(ValueError):
            TranscriptAnnotation(
                conversation_id="c", segment_index=0, original_text="o", corrected_text="c", user_id="u",
                status="invalid_status"
            )

    @pytest.mark.asyncio
    async def test_annotation_source_enum(self):
        """Test that source enum works as expected."""
        await initialize_beanie()

        # Test valid sources
        for source in ["user", "model_suggestion"]:
            annotation = TranscriptAnnotation(
                conversation_id="c", segment_index=0, original_text="o", corrected_text="c", user_id="u",
                source=source
            )
            assert annotation.source == source

    @pytest.mark.asyncio
    async def test_custom_id(self):
        """Test that ID can be overridden."""
        await initialize_beanie()

        custom_id = str(uuid.uuid4())
        annotation = TranscriptAnnotation(
            id=custom_id,
            conversation_id="c",
            segment_index=0,
            original_text="o",
            corrected_text="c",
            user_id="u"
        )
        assert annotation.id == custom_id
