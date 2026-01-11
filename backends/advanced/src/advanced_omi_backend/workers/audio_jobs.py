"""
Audio-related RQ job functions.

This module contains jobs related to audio file processing and cropping.
"""

import asyncio
import os
import logging
import time
from typing import Dict, Any, Optional

from advanced_omi_backend.models.job import JobPriority, async_job

from advanced_omi_backend.controllers.queue_controller import (
    default_queue,
    JOB_RESULT_TTL,
)
from advanced_omi_backend.models.job import _ensure_beanie_initialized

logger = logging.getLogger(__name__)


@async_job(redis=True, beanie=True)
async def audio_streaming_persistence_job(
    session_id: str,
    user_id: str,
    client_id: str,
    *,
    redis_client=None
) -> Dict[str, Any]:
    """
    Long-running RQ job that progressively writes audio chunks to disk as they arrive.

    Opens a WAV file immediately and appends chunks in real-time, making the file
    available for playback in the UI before the session completes.

    Runs in parallel with transcription processing to reduce memory pressure.

    Args:
        session_id: Stream session ID
        user_id: User ID
        client_id: Client ID
        redis_client: Redis client (injected by decorator)

    Returns:
        Dict with audio_file_path, chunk_count, total_bytes, duration_seconds

    Note: user_email is fetched from the database when needed.
    """
    logger.info(f"🎵 Starting audio persistence for session {session_id}")

    # Setup audio persistence consumer group (separate from transcription consumer)
    audio_stream_name = f"audio:stream:{client_id}"
    audio_group_name = "audio_persistence"
    audio_consumer_name = f"persistence-{session_id[:8]}"

    try:
        await redis_client.xgroup_create(
            audio_stream_name,
            audio_group_name,
            "0",
            mkstream=True
        )
        logger.info(f"📦 Created audio persistence consumer group for {audio_stream_name}")
    except Exception as e:
        if "BUSYGROUP" not in str(e):
            logger.warning(f"Failed to create audio consumer group: {e}")
        logger.debug(f"Audio consumer group already exists for {audio_stream_name}")

    # Job control
    session_key = f"audio:session:{session_id}"
    max_runtime = 86340  # 24 hours - 60 seconds (graceful exit before RQ timeout)
    start_time = time.time()

    from advanced_omi_backend.config import CHUNK_DIR
    from easy_audio_interfaces.filesystem.filesystem_interfaces import LocalFileSink
    from wyoming.audio import AudioChunk

    # Ensure directory exists
    CHUNK_DIR.mkdir(parents=True, exist_ok=True)

    # File rotation state
    current_conversation_id = None
    file_sink = None
    file_path = None
    wav_filename = None
    conversation_chunk_count = 0
    conversation_start_time = None

    # Audio collection stats (across all conversations in this session)
    total_chunk_count = 0
    total_bytes = 0
    end_signal_received = False
    consecutive_empty_reads = 0
    max_empty_reads = 3  # Exit after 3 consecutive empty reads (deterministic check)
    conversation_count = 0

    # Get current job for zombie detection
    from rq import get_current_job
    from advanced_omi_backend.utils.job_utils import check_job_alive
    current_job = get_current_job()

    while True:
        # Check if job still exists in Redis (detect zombie state)
        if not await check_job_alive(redis_client, current_job, session_id):
            if file_sink:
                await file_sink.close()
            break

        # Check timeout
        if time.time() - start_time > max_runtime:
            logger.warning(f"⏱️ Timeout reached for audio persistence {session_id}")
            # Close current file if open
            if file_sink:
                await file_sink.close()
                logger.info(f"✅ Closed file on timeout: {wav_filename}")
            break

        # Check if session is finalizing (user stopped recording or WebSocket disconnected)
        session_status = await redis_client.hget(session_key, "status")
        if session_status and session_status.decode() in ["finalizing", "complete"]:
            logger.info(f"🛑 Session finalizing detected, writing final chunks...")
            # Give a brief moment for any in-flight chunks to arrive
            await asyncio.sleep(0.5)
            # Do one final read to write remaining chunks to current file
            if file_sink:
                try:
                    final_messages = await redis_client.xreadgroup(
                        audio_group_name,
                        audio_consumer_name,
                        {audio_stream_name: ">"},
                        count=50,
                        block=500
                    )
                    if final_messages:
                        for stream_name, msgs in final_messages:
                            for message_id, fields in msgs:
                                audio_data = fields.get(b"audio_data", b"")
                                chunk_id = fields.get(b"chunk_id", b"").decode()
                                if chunk_id != "END" and len(audio_data) > 0:
                                    chunk = AudioChunk(
                                        rate=16000,
                                        width=2,
                                        channels=1,
                                        audio=audio_data
                                    )
                                    await file_sink.write(chunk)
                                    conversation_chunk_count += 1
                                    total_chunk_count += 1
                                    total_bytes += len(audio_data)
                                await redis_client.xack(audio_stream_name, audio_group_name, message_id)
                        logger.info(f"📦 Final read wrote {len(final_messages[0][1]) if final_messages else 0} more chunks")
                except Exception as e:
                    logger.debug(f"Final audio read error (non-fatal): {e}")

                # Close final file
                await file_sink.close()
                logger.info(f"✅ Closed final file: {wav_filename} ({conversation_chunk_count} chunks)")
            break

        # Check for conversation change (file rotation signal)
        conversation_key = f"conversation:current:{session_id}"
        new_conversation_id = await redis_client.get(conversation_key)

        if new_conversation_id:
            new_conversation_id = new_conversation_id.decode()

            # Conversation changed - rotate to new file
            if new_conversation_id != current_conversation_id:
                # Close previous file if exists
                if file_sink:
                    await file_sink.close()
                    duration = (time.time() - conversation_start_time) if conversation_start_time else 0
                    logger.info(
                        f"✅ Closed conversation {current_conversation_id[:12]} file: {wav_filename} "
                        f"({conversation_chunk_count} chunks, {duration:.1f}s)"
                    )

                # Open new file for new conversation
                current_conversation_id = new_conversation_id
                conversation_count += 1
                conversation_chunk_count = 0
                conversation_start_time = time.time()

                timestamp = int(time.time() * 1000)
                wav_filename = f"{timestamp}_{client_id}_{current_conversation_id}.wav"
                file_path = CHUNK_DIR / wav_filename

                file_sink = LocalFileSink(
                    file_path=str(file_path),
                    sample_rate=16000,
                    channels=1,
                    sample_width=2
                )
                await file_sink.open()
                logger.info(
                    f"📁 Opened new file for conversation #{conversation_count} ({current_conversation_id[:12]}): {file_path}"
                )

                # Store file path in Redis (keyed by conversation_id, not session_id)
                audio_file_key = f"audio:file:{current_conversation_id}"
                await redis_client.set(audio_file_key, str(file_path), ex=86400)  # 24 hour TTL
                logger.info(f"💾 Stored audio file path in Redis: {audio_file_key}")
        else:
            # Key deleted - conversation ended, close current file
            if file_sink and current_conversation_id:
                await file_sink.close()
                duration = (time.time() - conversation_start_time) if conversation_start_time else 0
                logger.info(
                    f"✅ Closed conversation {current_conversation_id[:12]} file after conversation ended: {wav_filename} "
                    f"({conversation_chunk_count} chunks, {duration:.1f}s)"
                )
                file_sink = None  # Clear sink to prevent writing to closed file
                current_conversation_id = None

        # If no file open yet, wait for conversation to be created
        if not file_sink:
            await asyncio.sleep(0.0001)  # Minimal sleep to yield to event loop
            continue

        # Read audio chunks from stream (non-blocking)
        try:
            audio_messages = await redis_client.xreadgroup(
                audio_group_name,
                audio_consumer_name,
                {audio_stream_name: ">"},
                count=20,  # Read up to 20 chunks at a time for efficiency
                block=100  # 100ms timeout - more responsive
            )

            if audio_messages:
                # Reset empty read counter - we got messages
                consecutive_empty_reads = 0

                for stream_name, msgs in audio_messages:
                    for message_id, fields in msgs:
                        # Extract audio data
                        audio_data = fields.get(b"audio_data", b"")
                        chunk_id = fields.get(b"chunk_id", b"").decode()

                        # Check for END signal
                        if chunk_id == "END":
                            logger.info(f"📡 Received END signal in audio persistence")
                            end_signal_received = True
                        elif len(audio_data) > 0:
                            # Write chunk immediately to file
                            chunk = AudioChunk(
                                rate=16000,
                                width=2,
                                channels=1,
                                audio=audio_data
                            )
                            await file_sink.write(chunk)
                            conversation_chunk_count += 1
                            total_chunk_count += 1
                            total_bytes += len(audio_data)

                            # Log every 40 chunks to avoid spam
                            if total_chunk_count % 40 == 0:
                                logger.info(
                                    f"📦 Session {session_id[:12]}: {total_chunk_count} total chunks "
                                    f"(conversation {current_conversation_id[:12]}: {conversation_chunk_count} chunks)"
                                )

                        # ACK the message
                        await redis_client.xack(audio_stream_name, audio_group_name, message_id)
            else:
                # No new messages - stream might be empty
                if end_signal_received:
                    consecutive_empty_reads += 1
                    logger.info(f"📭 No new messages ({consecutive_empty_reads}/{max_empty_reads} empty reads after END signal)")

                    if consecutive_empty_reads >= max_empty_reads:
                        logger.info(f"✅ Stream empty after END signal - stopping audio collection")
                        break

        except Exception as audio_error:
            # Stream might not exist yet or other transient errors
            logger.debug(f"Audio stream read error (non-fatal): {audio_error}")

        await asyncio.sleep(0.0001)  # Minimal sleep to yield to event loop

    # Job complete - calculate final stats
    runtime_seconds = time.time() - start_time

    # Calculate duration (16kHz, 16-bit mono = 32000 bytes/second)
    if total_bytes > 0:
        duration = total_bytes / (16000 * 2 * 1)  # sample_rate * sample_width * channels
    else:
        logger.warning(f"⚠️ No audio chunks written for session {session_id}")
        duration = 0.0

    logger.info(
        f"🎵 Audio persistence job complete for session {session_id}: "
        f"{conversation_count} conversations, {total_chunk_count} total chunks, "
        f"{total_bytes / 1024 / 1024:.2f} MB, {runtime_seconds:.1f}s runtime"
    )

    # Clean up Redis tracking keys
    audio_job_key = f"audio_persistence:session:{session_id}"
    await redis_client.delete(audio_job_key)
    conversation_key = f"conversation:current:{session_id}"
    await redis_client.delete(conversation_key)
    logger.info(f"🧹 Cleaned up tracking keys for session {session_id}")

    return {
        "session_id": session_id,
        "conversation_count": conversation_count,
        "last_audio_file_path": str(file_path) if file_path else None,
        "total_chunk_count": total_chunk_count,
        "total_bytes": total_bytes,
        "duration_seconds": duration,
        "runtime_seconds": runtime_seconds
    }


# Enqueue wrapper functions
