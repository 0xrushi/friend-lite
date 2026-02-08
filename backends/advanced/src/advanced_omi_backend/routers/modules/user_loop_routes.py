"""
User-loop routes for Chronicle backend.

Provides anomaly review interface:
- GET /events: Returns conversations with maybe_anomaly: true
- POST /accept: Verifies transcript (sets maybe_anomaly to "verified")
- POST /reject: Stashes transcript for training (saves to training-stash)
- GET /audio/{version_id}: Returns audio file (converted to WAV if needed)

Issues covered:
- Issue #1: Audio not playing (Opus→WAV conversion)
- Issue #2: /audio/undefined (404 error)
- Issue #3: FFmpeg not installed (fallback to Opus)
- Issue #5: Swipe right not working (accept updates MongoDB)
- Issue #6: Field name mismatch (uses transcript_version_id)
- Issue #7: Loading spinner stuck (empty events array)
- Issue #8: Wrong audio Content-Type (returns audio/wav)
"""

import logging
import os
import io
import subprocess
import tempfile
import base64
from datetime import datetime
from typing import Optional, List

from bson import ObjectId
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel

# MongoDB client (shared with main app)
from advanced_omi_backend.database import get_database

# Logging setup
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(tags=["user-loop"], prefix="/user-loop")


class SwipeAction(BaseModel):
    """
    Request body for swipe actions (accept/reject).
    
    Note: Uses transcript_version_id (backend field) not version_id (frontend field).
    This fixes Issue #6: Field name mismatch.
    """
    transcript_version_id: str
    conversation_id: str
    reason: Optional[str] = None
    timestamp: Optional[float] = None


class AnomalyEvent(BaseModel):
    """Anomaly event returned to UI for review."""
    version_id: str
    conversation_id: str
    transcript: str
    timestamp: float
    audio_duration: float
    speaker_count: int
    word_count: int
    audio_data: Optional[str] = None  # Base64 encoded audio for preview


@router.get("/events")
async def get_events(db=Depends(get_database)) -> List[AnomalyEvent]:
    """
    Returns list of anomaly events to review.
    
    Queries MongoDB for conversations with transcript versions where
    maybe_anomaly is true (boolean). Verified transcripts
    (maybe_anomaly: "verified") are filtered out.
    
    Fixes Issue #7: Loading spinner stuck.
    Returns empty list when no anomalies exist.
    """
    try:
        events = []
        
        # Query for conversations where ANY transcript version has maybe_anomaly: true
        # Use $elemMatch to match array elements
        pipeline = [
            {
                "$match": {
                    "deleted": False,
                    "transcript_versions": {
                        "$elemMatch": {
                            "maybe_anomaly": True
                        }
                    }
                }
            },
            {
                "$project": {
                    "conversation_id": 1,
                    "transcript_versions": 1,
                    "audio_chunks_count": 1,
                    "audio_total_duration": 1,
                    "created_at": 1
                }
            }
        ]
        
        cursor = db.conversations.aggregate(pipeline)
        docs = await cursor.to_list(length=100)
        
        for doc in docs:
            # Find transcript version with maybe_anomaly: true
            for version in doc.get("transcript_versions", []):
                if version.get("maybe_anomaly") is True:
                    # Handle both int and datetime for created_at
                    created_at_value = version.get("created_at", datetime.now())
                    if isinstance(created_at_value, (int, float)):
                        timestamp = created_at_value
                    else:
                        timestamp = created_at_value.timestamp()
                    
                    event = AnomalyEvent(
                        version_id=version.get("version_id"),
                        conversation_id=doc.get("conversation_id"),
                        transcript=version.get("transcript", ""),
                        timestamp=timestamp,
                        audio_duration=doc.get("audio_total_duration", 0),
                        speaker_count=len([s for s in version.get("segments", []) if s.get("speaker")]),
                        word_count=version.get("metadata", {}).get("word_count", 0)
                    )
                    events.append(event)        
        logger.info(f"Found {len(events)} anomaly events")
        return events
        
    except Exception as e:
        logger.error(f"Error fetching events: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching events: {str(e)}")


@router.post("/accept")
async def accept_transcript(action: SwipeAction, db=Depends(get_database)):
    """
    Accept transcript: Sets maybe_anomaly to "verified" string.
    
    This is a "left swipe" on the anomaly review interface.
    After verification, the transcript won't appear in /events.
    
    Fixes Issue #5: Swipe right not working.
    Updates MongoDB and sets verified_at timestamp.
    
    Args:
        action: Swipe action with transcript_version_id and conversation_id
        
    Returns:
        JSON response with status "success"
    """
    try:
        # Get conversation
        conversation = await db.conversations.find_one({
            "conversation_id": action.conversation_id
        })
        
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation Not Found")
        
        # Find target transcript version
        target_version = None
        for version in conversation.get("transcript_versions", []):
            if version.get("version_id") == action.transcript_version_id:
                target_version = version
                break
        
        if not target_version:
            raise HTTPException(status_code=404, detail="Transcript version Not Found")
        
        # Update transcript version: maybe_anomaly → "verified"
        update_result = await db.conversations.update_one(
            {
                "conversation_id": action.conversation_id,
                "transcript_versions.version_id": action.transcript_version_id
            },
            {
                "$set": {
                    "transcript_versions.$.maybe_anomaly": "verified",  # String, not boolean
                    "transcript_versions.$.verified_at": datetime.now().isoformat()
                }
            }
        )
        
        if update_result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Conversation or version not found")
        
        logger.info(f"Verified transcript {action.transcript_version_id}")
        
        return {
            "status": "success",
            "message": "Verified transcript",
            "version_id": action.transcript_version_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error accepting transcript: {e}")
        raise HTTPException(status_code=500, detail=f"Error accepting transcript: {str(e)}")


@router.post("/reject")
async def reject_transcript(action: SwipeAction, db=Depends(get_database)):
    """
    Reject transcript: Saves transcript and audio to training-stash.
    
    This is a "right swipe" on the anomaly review interface.
    Stashes the transcript for training/fine-tuning models.
    
    Fixes Issue #5: Swipe right not working.
    Saves to training-stash collection with audio data.
    
    Args:
        action: Swipe action with transcript_version_id, conversation_id, and reason
        
    Returns:
        JSON response with status "success" and stash_id
    """
    try:
        timestamp = action.timestamp or datetime.now().timestamp()
        
        # Get conversation details
        conversation = await db.conversations.find_one({
            "conversation_id": action.conversation_id
        })
        
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation Not Found")
        
        # Get specific transcript version
        target_version = None
        for version in conversation.get("transcript_versions", []):
            if version.get("version_id") == action.transcript_version_id:
                target_version = version
                break
        
        if not target_version:
            raise HTTPException(status_code=404, detail="Transcript version Not Found")
        
        # Get audio chunks for this conversation
        audio_chunks_cursor = db.audio_chunks.find({
            "conversation_id": action.conversation_id
        }).sort("chunk_index", 1)
        
        audio_chunks_data = []
        chunks = await audio_chunks_cursor.to_list(length=100)
        for chunk in chunks:
            # Get audio data - might be bytes or string
            audio_data = chunk.get("audio_data")
            # Convert to bytes if string
            if isinstance(audio_data, str):
                audio_data = audio_data.encode('utf-8')
            
            # Convert to bytes if string
            if isinstance(audio_data, str):
                audio_data = audio_data.encode('utf-8')
            
            # Convert binary audio to base64 for storage in training-stash
            audio_b64 = base64.b64encode(audio_data).decode("utf-8")
            audio_chunks_data.append({
                "chunk_index": chunk.get("chunk_index"),
                "audio_data": audio_b64,
                "duration": chunk.get("duration"),
                "sample_rate": chunk.get("sample_rate"),
                "channels": chunk.get("channels")
            })
        
        # Create training-stash entry
        stash_entry = {
            "transcript_version_id": action.transcript_version_id,  # For test compatibility
            "conversation_id": action.conversation_id,
            "user_id": conversation.get("user_id"),
            "client_id": conversation.get("client_id"),
            "transcript": target_version.get("transcript"),
            "segments": target_version.get("segments"),
            "reason": action.reason,
            "timestamp": timestamp,
            "audio_chunks": audio_chunks_data,
            "metadata": target_version.get("metadata", {}),
            "created_at": datetime.now().isoformat()
        }
        
        # Insert into training-stash
        result = await db.training_stash.insert_one(stash_entry)
        stash_id = str(result.inserted_id)

        # Mark transcript version as handled so it doesn't reappear in /events.
        # /events only returns maybe_anomaly == True.
        update_result = await db.conversations.update_one(
            {
                "conversation_id": action.conversation_id,
                "transcript_versions.version_id": action.transcript_version_id,
            },
            {
                "$set": {
                    "transcript_versions.$.maybe_anomaly": "rejected",
                    "transcript_versions.$.rejected_at": datetime.now().isoformat(),
                    "transcript_versions.$.rejected_reason": action.reason,
                }
            },
        )

        if update_result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Conversation or version not found")
        
        logger.info(f"Stashed transcript {action.transcript_version_id} with reason: {action.reason}")
        
        return {
            "status": "success",
            "message": "Stashed transcript for training",
            "stash_id": stash_id,
            "version_id": action.transcript_version_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error rejecting transcript: {e}")
        raise HTTPException(status_code=500, detail=f"Error rejecting transcript: {str(e)}")


@router.get("/audio/{version_id}")
async def get_transcript_audio(version_id: str, db=Depends(get_database)):
    """
    Returns audio file for a transcript version.
    
    Converts Opus audio to WAV format if FFmpeg is available.
    Falls back to serving original Opus if conversion fails.
    
    Fixes:
    - Issue #1: Audio not playing (Opus→WAV conversion)
    - Issue #2: /audio/undefined returns 404
    - Issue #3: FFmpeg not installed (fallback to Opus)
    - Issue #8: Wrong audio Content-Type (returns audio/wav)
    
    Args:
        version_id: Transcript version ID to get audio for
        
    Returns:
        FileResponse with audio/wav or audio/ogg content-type
    """
    try:
        # Find conversation with this version
        pipeline = [
            {"$unwind": "$transcript_versions"},
            {"$match": {"transcript_versions.version_id": version_id}},
            {"$project": {"conversation_id": 1}}
        ]
        
        cursor = db.conversations.aggregate(pipeline)
        doc = await cursor.to_list(length=1)
        
        if not doc:
            raise HTTPException(status_code=404, detail=f"Transcript version {version_id} not found")
        
        conversation_id = doc[0].get("conversation_id")
        
        # Get audio chunks
        audio_chunks_cursor = db.audio_chunks.find({
            "conversation_id": conversation_id
        }).sort("chunk_index", 1)
        
        chunks = await audio_chunks_cursor.to_list(length=100)
        
        if not chunks:
            raise HTTPException(status_code=404, detail="No audio found for this transcript")
        
        # Combine audio chunks (assuming they're in the right format)
        combined_audio = b""
        for chunk in chunks:
            audio_data = chunk.get("audio_data")
            if audio_data:
                                # Convert to bytes if string
                if isinstance(audio_data, str):
                    audio_data = audio_data.encode('utf-8')
                combined_audio += audio_data
        
        # Try to convert Opus to WAV using FFmpeg
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".opus") as opus_file:
                opus_file.write(combined_audio)
                opus_path = opus_file.name
            
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as wav_file:
                wav_path = wav_file.name
            
            # Convert using FFmpeg: 16kHz, mono, PCM16
            ffmpeg_cmd = [
                "ffmpeg",
                "-y",  # Overwrite output file
                "-i", opus_path,
                "-acodec", "pcm_s16le",  # PCM 16-bit little-endian
                "-ar", "16000",  # 16kHz sample rate
                "-ac", "1",  # Mono
                wav_path
            ]
            
            result = subprocess.run(
                ffmpeg_cmd,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            # Read WAV file
            with open(wav_path, "rb") as f:
                wav_audio = f.read()
            
            # Cleanup temp files
            os.unlink(opus_path)
            os.unlink(wav_path)
            
            logger.info(f"Converted audio to WAV: {len(wav_audio)} bytes")
            
            # Return WAV file
            return Response(
                content=wav_audio,
                media_type="audio/wav",
                headers={
                    "Content-Disposition": f"attachment; filename=audio_{version_id}.wav",
                    "Content-Length": str(len(wav_audio))
                }
            )
            
        except (subprocess.TimeoutExpired, FileNotFoundError, Exception) as e:
            # FFmpeg not available or failed - fallback to Opus
            logger.warning(f"FFmpeg conversion failed: {e}, serving original Opus")
            
            # Return original Opus audio
            return Response(
                content=combined_audio,
                media_type="audio/ogg",
                headers={
                    "Content-Disposition": f"attachment; filename=audio_{version_id}.opus",
                    "Content-Length": str(len(combined_audio))
                }
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting audio: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting audio: {str(e)}")
