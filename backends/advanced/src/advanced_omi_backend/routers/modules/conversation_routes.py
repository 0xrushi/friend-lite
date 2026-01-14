"""
Conversation management routes for Chronicle API.

Handles conversation CRUD operations, audio processing, and transcript management.
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, Query

from advanced_omi_backend.auth import current_active_user
from advanced_omi_backend.controllers import conversation_controller, audio_controller
from advanced_omi_backend.users import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/conversations", tags=["conversations"])


@router.post("/{client_id}/close")
async def close_current_conversation(
    client_id: str,
    current_user: User = Depends(current_active_user),
):
    """Close the current active conversation for a client. Works for both connected and disconnected clients."""
    return await conversation_controller.close_current_conversation(client_id, current_user)


@router.get("")
async def get_conversations(
    include_deleted: bool = Query(False, description="Include soft-deleted conversations"),
    current_user: User = Depends(current_active_user)
):
    """Get conversations. Admins see all conversations, users see only their own."""
    return await conversation_controller.get_conversations(current_user, include_deleted)


@router.get("/{conversation_id}")
async def get_conversation_detail(
    conversation_id: str,
    current_user: User = Depends(current_active_user)
):
    """Get a specific conversation with full transcript details."""
    return await conversation_controller.get_conversation(conversation_id, current_user)


# New reprocessing endpoints
@router.post("/{conversation_id}/reprocess-transcript")
async def reprocess_transcript(
    conversation_id: str, current_user: User = Depends(current_active_user)
):
    """Reprocess transcript for a conversation. Users can only reprocess their own conversations."""
    return await conversation_controller.reprocess_transcript(conversation_id, current_user)


@router.post("/{conversation_id}/reprocess-memory")
async def reprocess_memory(
    conversation_id: str,
    current_user: User = Depends(current_active_user),
    transcript_version_id: str = Query(default="active")
):
    """Reprocess memory extraction for a specific transcript version. Users can only reprocess their own conversations."""
    return await conversation_controller.reprocess_memory(conversation_id, transcript_version_id, current_user)


@router.post("/{conversation_id}/activate-transcript/{version_id}")
async def activate_transcript_version(
    conversation_id: str,
    version_id: str,
    current_user: User = Depends(current_active_user)
):
    """Activate a specific transcript version. Users can only modify their own conversations."""
    return await conversation_controller.activate_transcript_version(conversation_id, version_id, current_user)


@router.post("/{conversation_id}/activate-memory/{version_id}")
async def activate_memory_version(
    conversation_id: str,
    version_id: str,
    current_user: User = Depends(current_active_user)
):
    """Activate a specific memory version. Users can only modify their own conversations."""
    return await conversation_controller.activate_memory_version(conversation_id, version_id, current_user)


@router.get("/{conversation_id}/versions")
async def get_conversation_version_history(
    conversation_id: str, current_user: User = Depends(current_active_user)
):
    """Get version history for a conversation. Users can only access their own conversations."""
    return await conversation_controller.get_conversation_version_history(conversation_id, current_user)


@router.get("/{conversation_id}/waveform")
async def get_conversation_waveform(
    conversation_id: str,
    current_user: User = Depends(current_active_user)
):
    """
    Get or generate waveform visualization data for a conversation.

    This endpoint implements lazy generation:
    1. Check if waveform already exists in database
    2. If exists, return cached version immediately
    3. If not, generate synchronously and cache in database
    4. Return waveform data

    The waveform contains amplitude samples normalized to [-1.0, 1.0] range
    for visualization in the UI without needing to decode audio chunks.

    Returns:
        - samples: List[float] - Amplitude samples normalized to [-1, 1]
        - sample_rate: int - Samples per second (10)
        - duration_seconds: float - Total audio duration
    """
    from fastapi import HTTPException
    from advanced_omi_backend.models.conversation import Conversation
    from advanced_omi_backend.models.waveform import WaveformData
    from advanced_omi_backend.workers.waveform_jobs import generate_waveform_data

    # Verify conversation exists and user has access
    conversation = await Conversation.find_one(
        Conversation.conversation_id == conversation_id
    )

    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Check ownership (admins can access all)
    if not current_user.is_superuser and conversation.user_id != str(current_user.id):
        raise HTTPException(status_code=403, detail="Access denied")

    # Check for existing waveform in database
    waveform = await WaveformData.find_one(
        WaveformData.conversation_id == conversation_id
    )

    # If waveform exists, return cached version
    if waveform:
        logger.info(f"Returning cached waveform for conversation {conversation_id[:12]}")
        return waveform.model_dump(exclude={"id", "revision_id"})

    # Generate waveform on-demand
    logger.info(f"Generating waveform on-demand for conversation {conversation_id[:12]}")

    waveform_dict = await generate_waveform_data(
        conversation_id=conversation_id,
        sample_rate=3
    )

    if not waveform_dict.get("success"):
        error_msg = waveform_dict.get("error", "Unknown error")
        logger.error(f"Waveform generation failed: {error_msg}")
        raise HTTPException(
            status_code=500,
            detail=f"Waveform generation failed: {error_msg}"
        )

    # Return generated waveform (already saved to database by generator)
    return {
        "samples": waveform_dict["samples"],
        "sample_rate": waveform_dict["sample_rate"],
        "duration_seconds": waveform_dict["duration_seconds"]
    }


@router.delete("/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    permanent: bool = Query(False, description="Permanently delete (admin only)"),
    current_user: User = Depends(current_active_user)
):
    """Soft delete a conversation (or permanently delete if admin)."""
    return await conversation_controller.delete_conversation(conversation_id, current_user, permanent)


@router.post("/{conversation_id}/restore")
async def restore_conversation(
    conversation_id: str,
    current_user: User = Depends(current_active_user)
):
    """Restore a soft-deleted conversation."""
    return await conversation_controller.restore_conversation(conversation_id, current_user)
