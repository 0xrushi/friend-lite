"""
Annotation routes for Chronicle API.

Handles annotation CRUD operations for memories and transcripts.
Supports both user edits and AI-powered suggestions.
"""

import logging
from typing import List
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse

from advanced_omi_backend.auth import current_active_user
from advanced_omi_backend.users import User
from advanced_omi_backend.models.annotation import (
    Annotation,
    AnnotationType,
    AnnotationStatus,
    MemoryAnnotationCreate,
    TranscriptAnnotationCreate,
    AnnotationResponse,
)
from advanced_omi_backend.models.conversation import Conversation
from advanced_omi_backend.services.memory import get_memory_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/annotations", tags=["annotations"])


@router.post("/memory", response_model=AnnotationResponse)
async def create_memory_annotation(
    annotation_data: MemoryAnnotationCreate,
    current_user: User = Depends(current_active_user),
):
    """
    Create annotation for memory edit.

    - Validates user owns memory
    - Creates annotation record
    - Updates memory content in vector store
    - Re-embeds if content changed
    """
    try:
        memory_service = get_memory_service()

        # Verify memory ownership
        try:
            memory = await memory_service.get_memory(
                annotation_data.memory_id, current_user.user_id
            )
            if not memory:
                raise HTTPException(status_code=404, detail="Memory not found")
        except Exception as e:
            logger.error(f"Error fetching memory: {e}")
            raise HTTPException(status_code=404, detail="Memory not found")

        # Create annotation
        annotation = Annotation(
            annotation_type=AnnotationType.MEMORY,
            user_id=current_user.user_id,
            memory_id=annotation_data.memory_id,
            original_text=annotation_data.original_text,
            corrected_text=annotation_data.corrected_text,
            status=annotation_data.status,
        )
        await annotation.save()
        logger.info(
            f"Created memory annotation {annotation.id} for memory {annotation_data.memory_id}"
        )

        # Update memory content if accepted
        if annotation.status == AnnotationStatus.ACCEPTED:
            try:
                await memory_service.update_memory(
                    memory_id=annotation_data.memory_id,
                    content=annotation_data.corrected_text,
                    user_id=current_user.user_id,
                )
                logger.info(
                    f"Updated memory {annotation_data.memory_id} with corrected text"
                )
            except Exception as e:
                logger.error(f"Error updating memory: {e}")
                # Annotation is saved, but memory update failed - log but don't fail the request
                logger.warning(
                    f"Memory annotation {annotation.id} saved but memory update failed"
                )

        return AnnotationResponse.model_validate(annotation)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating memory annotation: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create memory annotation: {str(e)}",
        )


@router.post("/transcript", response_model=AnnotationResponse)
async def create_transcript_annotation(
    annotation_data: TranscriptAnnotationCreate,
    current_user: User = Depends(current_active_user),
):
    """
    Create annotation for transcript segment edit.

    - Validates user owns conversation
    - Creates annotation record
    - Updates transcript segment
    - Triggers memory reprocessing
    """
    try:
        # Verify conversation ownership
        conversation = await Conversation.find_one(
            Conversation.conversation_id == annotation_data.conversation_id,
            Conversation.user_id == current_user.user_id,
        )
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")

        # Validate segment index
        active_transcript = conversation.get_active_transcript()
        if (
            not active_transcript
            or annotation_data.segment_index >= len(active_transcript.segments)
        ):
            raise HTTPException(status_code=400, detail="Invalid segment index")

        # Create annotation
        annotation = Annotation(
            annotation_type=AnnotationType.TRANSCRIPT,
            user_id=current_user.user_id,
            conversation_id=annotation_data.conversation_id,
            segment_index=annotation_data.segment_index,
            original_text=annotation_data.original_text,
            corrected_text=annotation_data.corrected_text,
            status=annotation_data.status,
        )
        await annotation.save()
        logger.info(
            f"Created transcript annotation {annotation.id} for conversation {annotation_data.conversation_id} segment {annotation_data.segment_index}"
        )

        # Update transcript segment if accepted
        if annotation.status == AnnotationStatus.ACCEPTED:
            segment = active_transcript.segments[annotation_data.segment_index]
            segment.text = annotation_data.corrected_text
            await conversation.save()
            logger.info(
                f"Updated transcript segment {annotation_data.segment_index} in conversation {annotation_data.conversation_id}"
            )

            # Trigger memory reprocessing
            try:
                from advanced_omi_backend.workers.queue_manager import (
                    enqueue_memory_processing,
                )
                from advanced_omi_backend.models.job import JobPriority

                await enqueue_memory_processing(
                    client_id=conversation.client_id,
                    user_id=current_user.user_id,
                    user_email=current_user.email,
                    conversation_id=conversation.conversation_id,
                    priority=JobPriority.NORMAL,
                )
                logger.info(
                    f"Enqueued memory reprocessing for conversation {annotation_data.conversation_id}"
                )
            except Exception as e:
                logger.error(f"Error enqueuing memory reprocessing: {e}")
                # Annotation and segment update succeeded, but reprocessing failed
                logger.warning(
                    f"Transcript annotation {annotation.id} saved but memory reprocessing failed"
                )

        return AnnotationResponse.model_validate(annotation)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating transcript annotation: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create transcript annotation: {str(e)}",
        )


@router.get("/memory/{memory_id}", response_model=List[AnnotationResponse])
async def get_memory_annotations(
    memory_id: str,
    current_user: User = Depends(current_active_user),
):
    """Get all annotations for a memory."""
    try:
        annotations = await Annotation.find(
            Annotation.annotation_type == AnnotationType.MEMORY,
            Annotation.memory_id == memory_id,
            Annotation.user_id == current_user.user_id,
        ).to_list()

        return [AnnotationResponse.model_validate(a) for a in annotations]

    except Exception as e:
        logger.error(f"Error fetching memory annotations: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch memory annotations: {str(e)}",
        )


@router.get("/transcript/{conversation_id}", response_model=List[AnnotationResponse])
async def get_transcript_annotations(
    conversation_id: str,
    current_user: User = Depends(current_active_user),
):
    """Get all annotations for a conversation's transcript."""
    try:
        annotations = await Annotation.find(
            Annotation.annotation_type == AnnotationType.TRANSCRIPT,
            Annotation.conversation_id == conversation_id,
            Annotation.user_id == current_user.user_id,
        ).to_list()

        return [AnnotationResponse.model_validate(a) for a in annotations]

    except Exception as e:
        logger.error(f"Error fetching transcript annotations: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch transcript annotations: {str(e)}",
        )


@router.patch("/{annotation_id}/status")
async def update_annotation_status(
    annotation_id: str,
    status: AnnotationStatus,
    current_user: User = Depends(current_active_user),
):
    """
    Accept or reject AI-generated suggestions.

    Used for pending model suggestions in the UI.
    """
    try:
        annotation = await Annotation.find_one(
            Annotation.id == annotation_id,
            Annotation.user_id == current_user.user_id,
        )
        if not annotation:
            raise HTTPException(status_code=404, detail="Annotation not found")

        old_status = annotation.status
        annotation.status = status
        annotation.updated_at = datetime.now(timezone.utc)

        # If accepting a pending suggestion, apply the correction
        if (
            status == AnnotationStatus.ACCEPTED
            and old_status == AnnotationStatus.PENDING
        ):
            if annotation.is_memory_annotation():
                # Update memory
                try:
                    memory_service = get_memory_service()
                    await memory_service.update_memory(
                        memory_id=annotation.memory_id,
                        content=annotation.corrected_text,
                        user_id=current_user.user_id,
                    )
                    logger.info(
                        f"Applied suggestion to memory {annotation.memory_id}"
                    )
                except Exception as e:
                    logger.error(f"Error applying memory suggestion: {e}")
                    # Don't fail the status update if memory update fails
            elif annotation.is_transcript_annotation():
                # Update transcript segment
                try:
                    conversation = await Conversation.find_one(
                        Conversation.conversation_id == annotation.conversation_id
                    )
                    if conversation:
                        transcript = conversation.get_active_transcript()
                        if (
                            transcript
                            and annotation.segment_index < len(transcript.segments)
                        ):
                            transcript.segments[
                                annotation.segment_index
                            ].text = annotation.corrected_text
                            await conversation.save()
                            logger.info(
                                f"Applied suggestion to transcript segment {annotation.segment_index}"
                            )
                except Exception as e:
                    logger.error(f"Error applying transcript suggestion: {e}")
                    # Don't fail the status update if segment update fails

        await annotation.save()
        logger.info(f"Updated annotation {annotation_id} status to {status}")

        return {"status": "updated", "annotation_id": annotation_id, "new_status": status}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating annotation status: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update annotation status: {str(e)}",
        )
