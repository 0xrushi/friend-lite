from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

from advanced_omi_backend.models.annotation import TranscriptAnnotation
from advanced_omi_backend.models.conversation import Conversation
from advanced_omi_backend.auth import current_active_user
from advanced_omi_backend.models.user import User
from advanced_omi_backend.workers.memory_jobs import enqueue_memory_processing
from advanced_omi_backend.models.job import JobPriority

router = APIRouter()

class AnnotationCreate(BaseModel):
    conversation_id: str
    segment_index: int
    original_text: str
    corrected_text: str
    status: Optional[TranscriptAnnotation.AnnotationStatus] = TranscriptAnnotation.AnnotationStatus.ACCEPTED

class AnnotationResponse(BaseModel):
    id: str
    conversation_id: str
    segment_index: int
    original_text: str
    corrected_text: str
    status: str
    created_at: datetime

@router.post("/", response_model=AnnotationResponse)
async def create_annotation(
    annotation: AnnotationCreate,
    current_user: User = Depends(current_active_user)
):
    # Verify conversation exists and belongs to user
    conversation = await Conversation.find_one({
        "conversation_id": annotation.conversation_id,
        "user_id": str(current_user.id)
    })
    
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Create annotation
    new_annotation = TranscriptAnnotation(
        conversation_id=annotation.conversation_id,
        segment_index=annotation.segment_index,
        original_text=annotation.original_text,
        corrected_text=annotation.corrected_text,
        user_id=str(current_user.id),
        status=annotation.status,
        source=TranscriptAnnotation.AnnotationSource.USER
    )
    
    await new_annotation.insert()
    
    # Update the actual transcript in the conversation
    # We need to find the active transcript version and update the segment
    if conversation.active_transcript:
        version = conversation.active_transcript
        if 0 <= annotation.segment_index < len(version.segments):
            version.segments[annotation.segment_index].text = annotation.corrected_text
            
            # Save the conversation with the updated segment
            # We need to update the specific version in the list
            for i, v in enumerate(conversation.transcript_versions):
                if v.version_id == version.version_id:
                    conversation.transcript_versions[i] = version
                    break
            
            await conversation.save()
            
            # Trigger memory reprocessing
            enqueue_memory_processing(
                client_id=conversation.client_id,
                user_id=str(current_user.id),
                user_email=current_user.email,
                conversation_id=conversation.conversation_id,
                priority=JobPriority.NORMAL
            )
        else:
            raise HTTPException(status_code=400, detail="Segment index out of range")
    else:
        raise HTTPException(status_code=400, detail="No active transcript found")

    return AnnotationResponse(
        id=str(new_annotation.id),
        conversation_id=new_annotation.conversation_id,
        segment_index=new_annotation.segment_index,
        original_text=new_annotation.original_text,
        corrected_text=new_annotation.corrected_text,
        status=new_annotation.status,
        created_at=new_annotation.created_at
    )

@router.get("/{conversation_id}", response_model=List[AnnotationResponse])
async def get_annotations(
    conversation_id: str,
    current_user: User = Depends(current_active_user)
):
    annotations = await TranscriptAnnotation.find({
        "conversation_id": conversation_id,
        "user_id": str(current_user.id)
    }).to_list()
    
    return [
        AnnotationResponse(
            id=str(a.id),
            conversation_id=a.conversation_id,
            segment_index=a.segment_index,
            original_text=a.original_text,
            corrected_text=a.corrected_text,
            status=a.status,
            created_at=a.created_at
        )
        for a in annotations
    ]
