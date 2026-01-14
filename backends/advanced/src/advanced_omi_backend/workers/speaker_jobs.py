"""
Speaker recognition related RQ job functions.

This module contains all jobs related to speaker identification and recognition.
"""

import asyncio
import logging
import time
from typing import Dict, Any

from advanced_omi_backend.models.job import async_job
from advanced_omi_backend.controllers.queue_controller import transcription_queue

logger = logging.getLogger(__name__)


def _merge_overlapping_speaker_segments(
    segments: list[dict],
    overlap: float
) -> list[dict]:
    """
    Merge speaker segments from overlapping audio chunks.

    This function handles segments that may overlap due to chunked processing,
    merging segments from the same speaker and resolving conflicts using confidence scores.

    Args:
        segments: List of speaker segment dicts with start, end, text, speaker, confidence
        overlap: Overlap duration in seconds used during chunking

    Returns:
        Merged list of speaker segments

    Example:
        >>> segments = [
        ...     {"start": 0, "end": 930, "speaker": "Alice", "text": "...", "confidence": 0.9},
        ...     {"start": 900, "end": 1830, "speaker": "Alice", "text": "...", "confidence": 0.8},
        ... ]
        >>> merged = _merge_overlapping_speaker_segments(segments, overlap=30.0)
        >>> # Returns single merged segment from Alice
    """
    if not segments:
        return []

    # Sort by start time
    segments.sort(key=lambda s: s.get("start", 0))

    merged = []
    current = segments[0].copy()  # Copy to avoid mutating input

    for next_seg in segments[1:]:
        # Check if segments overlap
        if next_seg["start"] < current["end"]:
            # Overlapping - decide how to merge
            if current.get("speaker") == next_seg.get("speaker"):
                # Same speaker - merge by extending end time
                current["end"] = max(current["end"], next_seg["end"])

                # Combine text (avoid duplication in overlap region)
                current_text = current.get("text", "")
                next_text = next_seg.get("text", "")

                # Simple text merging - just append if different
                if next_text and next_text not in current_text:
                    current["text"] = f"{current_text} {next_text}".strip()

                # Use higher confidence
                current["confidence"] = max(
                    current.get("confidence", 0),
                    next_seg.get("confidence", 0)
                )
            else:
                # Different speakers - use confidence to decide boundary
                current_conf = current.get("confidence", 0)
                next_conf = next_seg.get("confidence", 0)

                if next_conf > current_conf:
                    # Next segment more confident, close current and start new
                    merged.append(current)
                    current = next_seg.copy()
                else:
                    # Current more confident, adjust next segment start
                    # Save current, update next to start after current
                    merged.append(current)
                    next_seg_copy = next_seg.copy()
                    next_seg_copy["start"] = current["end"]
                    current = next_seg_copy
        else:
            # No overlap, save current and move to next
            merged.append(current)
            current = next_seg.copy()

    # Don't forget last segment
    merged.append(current)

    return merged


@async_job(redis=True, beanie=True)
async def check_enrolled_speakers_job(
    session_id: str,
    user_id: str,
    client_id: str,
    *,
    redis_client=None
) -> Dict[str, Any]:
    """
    Check if any enrolled speakers are present in the current audio stream.

    This job is used during speech detection to filter conversations by enrolled speakers.

    Args:
        session_id: Stream session ID
        user_id: User ID
        client_id: Client ID
        redis_client: Redis client (injected by decorator)

    Returns:
        Dict with enrolled_present, identified_speakers, and speaker_result
    """
    from advanced_omi_backend.services.audio_stream import TranscriptionResultsAggregator
    from advanced_omi_backend.speaker_recognition_client import SpeakerRecognitionClient

    logger.info(f"🎤 Starting enrolled speaker check for session {session_id[:12]}")

    start_time = time.time()

    # Get aggregated transcription results
    aggregator = TranscriptionResultsAggregator(redis_client)
    raw_results = await aggregator.get_session_results(session_id)

    # Check for enrolled speakers
    speaker_client = SpeakerRecognitionClient()
    enrolled_present, speaker_result = await speaker_client.check_if_enrolled_speaker_present(
        redis_client=redis_client,
        client_id=client_id,
        session_id=session_id,
        user_id=user_id,
        transcription_results=raw_results
    )

    # Check for errors from speaker service
    if speaker_result and speaker_result.get("error"):
        error_type = speaker_result.get("error")
        error_message = speaker_result.get("message", "Unknown error")
        logger.error(f"🎤 [SPEAKER CHECK] Speaker service error: {error_type} - {error_message}")

        # Fail the job - don't create conversation if speaker service failed
        return {
            "success": False,
            "session_id": session_id,
            "error": f"Speaker recognition failed: {error_type}",
            "error_details": error_message,
            "enrolled_present": False,
            "identified_speakers": [],
            "processing_time_seconds": time.time() - start_time
        }

    # Extract identified speakers
    identified_speakers = []
    if speaker_result and "segments" in speaker_result:
        for seg in speaker_result["segments"]:
            identified_as = seg.get("identified_as")
            if identified_as and identified_as != "Unknown" and identified_as not in identified_speakers:
                identified_speakers.append(identified_as)

    processing_time = time.time() - start_time

    if enrolled_present:
        logger.info(f"✅ Enrolled speaker(s) found: {', '.join(identified_speakers)} ({processing_time:.2f}s)")
    else:
        logger.info(f"⏭️ No enrolled speakers found ({processing_time:.2f}s)")

    # Update job metadata for timeline tracking
    from rq import get_current_job
    current_job = get_current_job()
    if current_job:
        if not current_job.meta:
            current_job.meta = {}
        current_job.meta.update({
            "session_id": session_id,
            "audio_uuid": session_id,
            "client_id": client_id,
            "enrolled_present": enrolled_present,
            "identified_speakers": identified_speakers,
            "speaker_count": len(identified_speakers),
            "processing_time": processing_time
        })
        current_job.save_meta()

    return {
        "success": True,
        "session_id": session_id,
        "enrolled_present": enrolled_present,
        "identified_speakers": identified_speakers,
        "speaker_result": speaker_result,
        "processing_time_seconds": processing_time
    }


@async_job(redis=True, beanie=True)
async def recognise_speakers_job(
    conversation_id: str,
    version_id: str,
    transcript_text: str = "",
    words: list = None,
    *,
    redis_client=None
) -> Dict[str, Any]:
    """
    RQ job function for identifying speakers in a transcribed conversation.

    This job runs after transcription and:
    1. Reconstructs audio from MongoDB chunks
    2. Calls speaker recognition service to identify speakers
    3. Updates the transcript version with identified speaker labels
    4. Returns results for downstream jobs (memory)

    Args:
        conversation_id: Conversation ID
        version_id: Transcript version ID to update
        transcript_text: Transcript text from transcription job (optional, reads from DB if empty)
        words: Word-level timing data from transcription job (optional, reads from DB if empty)
        redis_client: Redis client (injected by decorator)

    Returns:
        Dict with processing results
    """
    from advanced_omi_backend.models.conversation import Conversation
    from advanced_omi_backend.speaker_recognition_client import SpeakerRecognitionClient

    logger.info(f"🎤 RQ: Starting speaker recognition for conversation {conversation_id}")

    start_time = time.time()

    # Get the conversation
    conversation = await Conversation.find_one(Conversation.conversation_id == conversation_id)
    if not conversation:
        logger.error(f"Conversation {conversation_id} not found")
        return {"success": False, "error": "Conversation not found"}

    # Get user_id from conversation
    user_id = conversation.user_id

    # Find the transcript version to update
    transcript_version = None
    for version in conversation.transcript_versions:
        if version.version_id == version_id:
            transcript_version = version
            break

    if not transcript_version:
        logger.error(f"Transcript version {version_id} not found")
        return {"success": False, "error": "Transcript version not found"}

    # Check if speaker recognition is enabled
    speaker_client = SpeakerRecognitionClient()
    if not speaker_client.enabled:
        logger.info(f"🎤 Speaker recognition disabled, skipping")
        return {
            "success": True,
            "conversation_id": conversation_id,
            "version_id": version_id,
            "speaker_recognition_enabled": False,
            "processing_time_seconds": 0
        }

    # Reconstruct audio from MongoDB chunks
    from advanced_omi_backend.utils.audio_chunk_utils import (
        reconstruct_wav_from_conversation,
        reconstruct_audio_segments,
        filter_transcript_by_time
    )
    import os

    # Read transcript text and words from the transcript version
    # (Parameters may be empty if called via job dependency)
    actual_transcript_text = transcript_text or transcript_version.transcript or ""
    actual_words = words if words else []

    # If words not provided, we need to get them from metadata
    if not actual_words and transcript_version.metadata:
        actual_words = transcript_version.metadata.get("words", [])

    if not actual_transcript_text:
        logger.warning(f"🎤 No transcript text found in version {version_id}")
        return {
            "success": False,
            "conversation_id": conversation_id,
            "version_id": version_id,
            "error": "No transcript text available",
            "processing_time_seconds": 0
        }

    transcript_data = {
        "text": actual_transcript_text,
        "words": actual_words
    }

    # Check if we need to use chunked processing
    total_duration = conversation.audio_total_duration or 0.0
    chunk_threshold = float(os.getenv("SPEAKER_CHUNK_THRESHOLD", "1500"))  # 25 minutes default

    logger.info(f"📦 Reconstructing audio from MongoDB chunks for conversation {conversation_id}")
    logger.info(f"📊 Total duration: {total_duration:.1f}s, Threshold: {chunk_threshold:.1f}s")

    # Call speaker recognition service
    try:
        speaker_segments = []

        if total_duration > chunk_threshold:
            # Chunked processing for large files
            logger.info(f"🎤 Using chunked processing for large file ({total_duration:.1f}s > {chunk_threshold:.1f}s)")

            segment_duration = float(os.getenv("SPEAKER_CHUNK_SIZE", "900"))  # 15 minutes default
            overlap = float(os.getenv("SPEAKER_CHUNK_OVERLAP", "30"))  # 30 seconds default

            async for wav_data, start_time, end_time in reconstruct_audio_segments(
                conversation_id=conversation_id,
                segment_duration=segment_duration,
                overlap=overlap
            ):
                logger.info(
                    f"📦 Processing segment {start_time:.1f}s - {end_time:.1f}s: "
                    f"{len(wav_data) / 1024 / 1024:.2f} MB"
                )

                # Filter transcript for this time range
                segment_transcript = filter_transcript_by_time(
                    transcript_data,
                    start_time,
                    end_time
                )

                # Call speaker service for this segment
                speaker_result = await speaker_client.diarize_identify_match(
                    audio_data=wav_data,
                    transcript_data=segment_transcript,
                    user_id=user_id
                )

                # Check for errors from speaker service
                if speaker_result.get("error"):
                    error_type = speaker_result.get("error")
                    error_message = speaker_result.get("message", "Unknown error")
                    logger.error(f"🎤 Speaker service error on segment {start_time:.1f}s: {error_type}")

                    # Raise exception for connection failures
                    if error_type in ("connection_failed", "timeout", "client_error"):
                        raise RuntimeError(f"Speaker recognition service unavailable: {error_type} - {error_message}")

                    # For processing errors, continue with other segments
                    continue

                # Adjust timestamps to global time
                if speaker_result and "segments" in speaker_result:
                    for seg in speaker_result["segments"]:
                        seg["start"] += start_time
                        seg["end"] += start_time

                    speaker_segments.extend(speaker_result["segments"])

            logger.info(f"🎤 Collected {len(speaker_segments)} segments from chunked processing")

            # Merge overlapping segments
            if speaker_segments:
                speaker_segments = _merge_overlapping_speaker_segments(speaker_segments, overlap)
                logger.info(f"🎤 After merging overlaps: {len(speaker_segments)} segments")

            # Package as result dict for consistent handling below
            speaker_result = {"segments": speaker_segments}

        else:
            # Normal processing for files <= threshold
            logger.info(f"🎤 Using normal processing for small file ({total_duration:.1f}s <= {chunk_threshold:.1f}s)")

            # Reconstruct WAV from MongoDB chunks (already in memory as bytes)
            wav_data = await reconstruct_wav_from_conversation(conversation_id)

            logger.info(
                f"📦 Reconstructed audio from MongoDB chunks: "
                f"{len(wav_data) / 1024 / 1024:.2f} MB"
            )

            logger.info(f"🎤 Calling speaker recognition service...")

            # Call speaker service with in-memory audio data (no temp file needed!)
            speaker_result = await speaker_client.diarize_identify_match(
                audio_data=wav_data,  # Pass bytes directly, no disk I/O
                transcript_data=transcript_data,
                user_id=user_id
            )

    except ValueError as e:
        # No chunks found for conversation
        logger.error(f"No audio chunks found for conversation {conversation_id}: {e}")
        return {
            "success": False,
            "conversation_id": conversation_id,
            "version_id": version_id,
            "error": f"No audio chunks found: {e}",
            "processing_time_seconds": time.time() - start_time
        }
    except Exception as audio_error:
        logger.error(f"Failed to reconstruct audio from MongoDB: {audio_error}", exc_info=True)
        return {
            "success": False,
            "conversation_id": conversation_id,
            "version_id": version_id,
            "error": f"Audio reconstruction failed: {audio_error}",
            "processing_time_seconds": time.time() - start_time
        }

    # Continue with speaker recognition result processing
    try:

        # Check for errors from speaker service
        if speaker_result.get("error"):
            error_type = speaker_result.get("error")
            error_message = speaker_result.get("message", "Unknown error")
            logger.error(f"🎤 Speaker recognition service error: {error_type} - {error_message}")

            # Raise exception for connection failures so dependent jobs are canceled
            # This ensures RQ marks the job as "failed" instead of "completed"
            if error_type in ("connection_failed", "timeout", "client_error"):
                raise RuntimeError(f"Speaker recognition service unavailable: {error_type} - {error_message}")

            # For other errors (e.g., processing errors), return error dict without failing
            return {
                "success": False,
                "conversation_id": conversation_id,
                "version_id": version_id,
                "error": f"Speaker recognition failed: {error_type}",
                "error_details": error_message,
                "processing_time_seconds": time.time() - start_time
            }

        # Service worked but found no segments (legitimate empty result)
        if not speaker_result or "segments" not in speaker_result or not speaker_result["segments"]:
            logger.warning(f"🎤 Speaker recognition returned no segments")
            return {
                "success": True,
                "conversation_id": conversation_id,
                "version_id": version_id,
                "speaker_recognition_enabled": True,
                "identified_speakers": [],
                "processing_time_seconds": time.time() - start_time
            }

        speaker_segments = speaker_result["segments"]
        logger.info(f"🎤 Speaker recognition returned {len(speaker_segments)} segments")

        # Update the transcript version segments with identified speakers
        # Filter out empty segments (diarization sometimes creates segments with no text)
        updated_segments = []
        empty_segment_count = 0
        for seg in speaker_segments:
            # FIX: More robust empty segment detection
            text = seg.get("text", "").strip()

            # Skip segments with no text, whitespace-only, or very short
            if not text or len(text) < 3:
                empty_segment_count += 1
                logger.debug(f"Filtered empty/short segment: text='{text}'")
                continue

            # Skip segments with invalid structure
            if not isinstance(seg.get("start"), (int, float)) or not isinstance(seg.get("end"), (int, float)):
                empty_segment_count += 1
                logger.debug(f"Filtered segment with invalid timing: {seg}")
                continue

            speaker_name = seg.get("identified_as") or seg.get("speaker", "Unknown")
            updated_segments.append(
                Conversation.SpeakerSegment(
                    start=seg.get("start", 0),
                    end=seg.get("end", 0),
                    text=text,
                    speaker=speaker_name,
                    confidence=seg.get("confidence")
                )
            )

        if empty_segment_count > 0:
            logger.info(f"🔇 Filtered out {empty_segment_count} empty segments from speaker recognition")

        # Update the transcript version
        transcript_version.segments = updated_segments

        # Extract unique identified speakers for metadata
        identified_speakers = set()
        for seg in speaker_segments:
            identified_as = seg.get("identified_as", "Unknown")
            if identified_as != "Unknown":
                identified_speakers.add(identified_as)

        # Update metadata
        if not transcript_version.metadata:
            transcript_version.metadata = {}

        transcript_version.metadata["speaker_recognition"] = {
            "enabled": True,
            "identified_speakers": list(identified_speakers),
            "speaker_count": len(identified_speakers),
            "total_segments": len(speaker_segments),
            "processing_time_seconds": time.time() - start_time
        }

        await conversation.save()

        processing_time = time.time() - start_time
        logger.info(f"✅ Speaker recognition completed for {conversation_id} in {processing_time:.2f}s")

        return {
            "success": True,
            "conversation_id": conversation_id,
            "version_id": version_id,
            "speaker_recognition_enabled": True,
            "identified_speakers": list(identified_speakers),
            "segment_count": len(updated_segments),
            "processing_time_seconds": processing_time
        }

    except Exception as speaker_error:
        logger.error(f"❌ Speaker recognition failed: {speaker_error}")
        import traceback
        logger.debug(traceback.format_exc())

        return {
            "success": False,
            "conversation_id": conversation_id,
            "version_id": version_id,
            "error": str(speaker_error),
            "processing_time_seconds": time.time() - start_time
        }
