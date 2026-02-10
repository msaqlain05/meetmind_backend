"""API routes for meeting operations"""

from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from sqlalchemy.orm import Session
from typing import List
import json

from app.database import get_db
from app.schemas.meeting import (
    MeetingUploadResponse,
    MeetingDetailResponse,
    UserMeetingsResponse,
    MeetingListItem
)
from app.services.meeting_service import MeetingService

router = APIRouter(prefix="/meetings", tags=["meetings"])


@router.post("/upload", response_model=MeetingUploadResponse)
async def upload_meeting(
    user_id: str = Form(..., description="User identifier"),
    audio_file: UploadFile = File(..., description="Audio file to process"),
    db: Session = Depends(get_db)
):
    """
    Upload and process a meeting audio file.
    
    This endpoint:
    1. Validates and saves the audio file
    2. Transcribes it using Whisper
    3. Analyzes it with LangGraph
    4. Stores results in the database
    
    Args:
        user_id: Unique identifier for the user
        audio_file: Audio file (wav, mp3, webm, m4a, ogg)
        db: Database session
        
    Returns:
        Complete meeting analysis including transcript, summary, decisions, action items, and key points
    """
    meeting_service = MeetingService()
    meeting = await meeting_service.process_meeting(db, user_id, audio_file)
    
    return MeetingUploadResponse(
        meeting_id=meeting.id,
        user_id=meeting.user_id,
        status="completed",
        transcript=meeting.transcript,
        summary=meeting.summary,
        decisions=json.loads(meeting.decisions) if meeting.decisions else [],
        action_items=json.loads(meeting.action_items) if meeting.action_items else [],
        key_points=json.loads(meeting.key_points) if meeting.key_points else [],
        created_at=meeting.created_at
    )


@router.get("/user/{user_id}", response_model=UserMeetingsResponse)
def get_user_meetings(
    user_id: str,
    db: Session = Depends(get_db)
):
    """
    Get all meetings for a specific user.
    
    Args:
        user_id: User identifier
        db: Database session
        
    Returns:
        List of meetings with summaries
    """
    meeting_service = MeetingService()
    meetings = meeting_service.get_user_meetings(db, user_id)
    
    meeting_items = [
        MeetingListItem(
            meeting_id=m.id,
            audio_filename=m.audio_filename,
            summary=m.summary or "",
            created_at=m.created_at
        )
        for m in meetings
    ]
    
    return UserMeetingsResponse(
        user_id=user_id,
        meetings=meeting_items,
        total=len(meeting_items)
    )


@router.get("/{meeting_id}", response_model=MeetingDetailResponse)
def get_meeting_detail(
    meeting_id: str,
    user_id: str,
    db: Session = Depends(get_db)
):
    """
    Get detailed information about a specific meeting.
    
    Args:
        meeting_id: Meeting identifier
        user_id: User identifier (for authorization)
        db: Database session
        
    Returns:
        Complete meeting details
    """
    meeting_service = MeetingService()
    meeting = meeting_service.get_meeting_by_id(db, meeting_id, user_id)
    
    return MeetingDetailResponse(
        meeting_id=meeting.id,
        user_id=meeting.user_id,
        audio_filename=meeting.audio_filename,
        transcript=meeting.transcript or "",
        summary=meeting.summary or "",
        decisions=json.loads(meeting.decisions) if meeting.decisions else [],
        action_items=json.loads(meeting.action_items) if meeting.action_items else [],
        key_points=json.loads(meeting.key_points) if meeting.key_points else [],
        created_at=meeting.created_at
    )
