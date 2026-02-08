"""
Memory-related RQ job functions.

This module contains jobs related to memory extraction and processing.
"""

import logging
import time
import uuid
from datetime import UTC, datetime
from typing import Any, Dict

from advanced_omi_backend.controllers.queue_controller import (
    JOB_RESULT_TTL,
    memory_queue,
)
from advanced_omi_backend.models.job import BaseRQJob, JobPriority, async_job
from advanced_omi_backend.services.memory.base import MemoryEntry
from advanced_omi_backend.controllers.queue_controller import default_queue
from advanced_omi_backend.services.plugin_service import ensure_plugin_router
from advanced_omi_backend.workers.conversation_jobs import generate_title_summary_job

logger = logging.getLogger(__name__)


MIN_CONVERSATION_LENGTH = 10

@async_job(redis=True, beanie=True)
async def process_memory_job(conversation_id: str, *, redis_client=None) -> Dict[str, Any]:
    """
    RQ job function for memory extraction and processing from conversations.

    V2 Architecture:
        1. Extracts memories from conversation transcript
        2. Checks primary speakers filter if configured
        3. Uses configured memory provider (chronicle or openmemory_mcp)
        4. Stores memory references in conversation document

    Note: Listening jobs are restarted by open_conversation_job (not here).
    This allows users to resume talking immediately after conversation closes,
    without waiting for memory processing to complete.

    Args:
        conversation_id: Conversation ID to process
        redis_client: Redis client (injected by decorator)

    Returns:
        Dict with processing results
    """
    from advanced_omi_backend.models.conversation import Conversation
    from advanced_omi_backend.services.memory import get_memory_service
    from advanced_omi_backend.users import get_user_by_id

    start_time = time.time()
    logger.info(f"🔄 Starting memory processing for conversation {conversation_id}")

    # Get conversation data
    conversation_model = await Conversation.find_one(
        Conversation.conversation_id == conversation_id
    )
    if not conversation_model:
        logger.warning(f"No conversation found for {conversation_id}")
        return {"success": False, "error": "Conversation not found"}

    # Get client_id, user_id, and user_email from conversation/user
    client_id = conversation_model.client_id
    user_id = conversation_model.user_id

    user = await get_user_by_id(user_id)
    if user:
        user_email = user.email
    else:
        logger.warning(f"Could not find user {user_id}")
        user_email = ""

    logger.info(
        f"🔄 Processing memory for conversation {conversation_id}, client={client_id}, user={user_id}"
    )

    # Extract conversation text and speakers in a single pass
    full_conversation_parts = []
    transcript_speakers = set()
    segments = conversation_model.segments or []

    for segment in segments:
        # Standardize access for both dict and object segments
        if isinstance(segment, dict):
            text = segment.get("text", "").strip()
            speaker = segment.get("speaker", "Unknown")
            identified_as = segment.get("identified_as")
        else:
            text = getattr(segment, "text", "").strip()
            speaker = getattr(segment, "speaker", "Unknown")
            identified_as = getattr(segment, "identified_as", None)

        if text:
            full_conversation_parts.append(f"{speaker}: {text}")

        if identified_as and identified_as != "Unknown":
            transcript_speakers.add(identified_as.strip().lower())

    full_conversation = "\n".join(full_conversation_parts)

    # Fallback: if segments have no text content but transcript exists, use transcript
    # This handles cases where speaker recognition fails/is disabled
    if len(full_conversation) < MIN_CONVERSATION_LENGTH and conversation_model.transcript and isinstance(conversation_model.transcript, str):
        logger.info(f"Segments empty or too short, falling back to transcript text for {conversation_id}")
        full_conversation = conversation_model.transcript

    if len(full_conversation) < MIN_CONVERSATION_LENGTH:
        logger.warning(f"Conversation too short for memory processing: {conversation_id}")
        return {"success": False, "error": "Conversation too short"}

    # Check primary speakers filter
    if user and user.primary_speakers:
        primary_speaker_names = {ps["name"].strip().lower() for ps in user.primary_speakers}

        if transcript_speakers and not transcript_speakers.intersection(primary_speaker_names):
            logger.info(
                f"Skipping memory - no primary speakers found in conversation {conversation_id}"
            )
            return {"success": True, "skipped": True, "reason": "No primary speakers"}

    # Process memory
    memory_service = get_memory_service()
    memory_result = await memory_service.add_memory(
        full_conversation,
        client_id,
        conversation_id,
        user_id,
        user_email,
        allow_update=True,
    )

    if memory_result:
        success, created_memory_ids = memory_result

        if success and created_memory_ids:
            # Add memory version to conversation
            # Fetch again to ensure atomic update handling (though save() handles it)
            conversation_model = await Conversation.find_one(
                Conversation.conversation_id == conversation_id
            )
            if conversation_model:
                processing_time = time.time() - start_time

                # Get active transcript version for reference
                transcript_version_id = conversation_model.active_transcript_version or "unknown"

                # Determine memory provider from memory service
                memory_provider = conversation_model.MemoryProvider.CHRONICLE  # Default
                try:
                    # Check for explicit provider identifier, fallback to class name
                    provider_id = getattr(memory_service, "provider_identifier", None)
                    if provider_id == "openmemory_mcp":
                        memory_provider = conversation_model.MemoryProvider.OPENMEMORY_MCP
                    elif not provider_id and "OpenMemory" in memory_service.__class__.__name__:
                        memory_provider = conversation_model.MemoryProvider.OPENMEMORY_MCP
                except Exception:
                    pass

                # Create version ID for this memory extraction
                version_id = str(uuid.uuid4())

                # Add memory version with metadata
                conversation_model.add_memory_version(
                    version_id=version_id,
                    memory_count=len(created_memory_ids),
                    transcript_version_id=transcript_version_id,
                    provider=memory_provider,
                    processing_time_seconds=processing_time,
                    metadata={"memory_ids": created_memory_ids},
                    set_as_active=True,
                )
                await conversation_model.save()

            logger.info(
                f"✅ Completed memory processing for conversation {conversation_id} - created {len(created_memory_ids)} memories in {processing_time:.2f}s"
            )

            # Update job metadata with memory information
            from rq import get_current_job

            current_job = get_current_job()
            if current_job:
                if not current_job.meta:
                    current_job.meta = {}

                # Fetch memory details to display in UI
                memory_details = []
                try:
                    for memory_id in created_memory_ids[:5]:  # Limit to first 5 for display
                        memory_entry = await memory_service.get_memory(memory_id, user_id)
                        if memory_entry:
                            # Handle different return types from memory service
                            memory_text: str
                            if isinstance(memory_entry, MemoryEntry):
                                # MemoryEntry object with content attribute
                                memory_text = memory_entry.content
                            elif isinstance(memory_entry, dict):
                                # Dictionary with "content" key
                                if "content" in memory_entry:
                                    memory_text = memory_entry["content"]
                                else:
                                    logger.error(
                                        f"Dict memory entry missing 'content' key for {memory_id}: {list(memory_entry.keys())}"
                                    )
                                    raise ValueError(
                                        f"Dict memory entry missing 'content' key for memory {memory_id}"
                                    )
                            elif isinstance(memory_entry, str):
                                # String content directly
                                memory_text = memory_entry
                            else:
                                # Unexpected type
                                logger.error(
                                    f"Unexpected memory entry type for {memory_id}: {type(memory_entry).__name__}"
                                )
                                raise TypeError(
                                    f"Unexpected memory entry type: {type(memory_entry).__name__}"
                                )

                            # Truncate to 200 chars
                            memory_details.append(
                                {"memory_id": memory_id, "text": memory_text[:200]}
                            )
                except Exception as e:
                    logger.warning(f"Failed to fetch memory details for UI: {e}")

                current_job.meta.update(
                    {
                        "conversation_id": conversation_id,
                        "memories_created": len(created_memory_ids),
                        "memory_ids": created_memory_ids[:5],  # Store first 5 IDs
                        "memory_details": memory_details,
                        "processing_time": processing_time,
                    }
                )
                current_job.save_meta()

            # NOTE: Listening jobs are restarted by open_conversation_job (not here)
            # This allows users to resume talking immediately after conversation closes,
            # without waiting for memory processing to complete.

            return {
                "success": True,
                "memories_created": len(created_memory_ids),
                "processing_time": processing_time,
            }
        else:
            # No memories created - still successful
            return {"success": True, "memories_created": 0, "skipped": True}
    else:
        return {"success": False, "error": "Memory service returned False"}


def enqueue_memory_processing(
    conversation_id: str,
    priority: JobPriority = JobPriority.NORMAL,
):
    """
    Enqueue a memory processing job.

    Returns RQ Job object for tracking.
    """
    timeout_mapping = {
        JobPriority.URGENT: 3600,  # 60 minutes
        JobPriority.HIGH: 2400,  # 40 minutes
        JobPriority.NORMAL: 1800,  # 30 minutes
        JobPriority.LOW: 900,  # 15 minutes
    }

    job = memory_queue.enqueue(
        process_memory_job,
        conversation_id,  # Only argument needed - job fetches conversation data internally
        job_timeout=timeout_mapping.get(priority, 1800),
        result_ttl=JOB_RESULT_TTL,
        job_id=f"memory_{conversation_id[:8]}",
        description=f"Process memory for conversation {conversation_id[:8]}",
    )

    logger.info(f"📥 RQ: Enqueued memory job {job.id} for conversation {conversation_id}")

    # Also enqueue title/summary generation to ensure summaries reflect any transcript changes
    try:
        # Use a timestamp in job_id to avoid conflicts if re-run frequently
        summary_job_id = f"title_summary_{conversation_id[:8]}_{int(time.time())}"
        
        default_queue.enqueue(
            generate_title_summary_job,
            conversation_id,
            job_timeout=300,
            result_ttl=JOB_RESULT_TTL,
            job_id=summary_job_id,
            description=f"Generate title and summary for conversation {conversation_id[:8]}",
        )
        logger.info(f"📥 RQ: Enqueued summary job {summary_job_id} for conversation {conversation_id}")
    except Exception as e:
        logger.error(f"Failed to enqueue summary job: {e}")
        raise e

    return job
