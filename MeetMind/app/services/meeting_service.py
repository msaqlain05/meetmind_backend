"""Meeting service for orchestrating the complete workflow"""

from sqlalchemy.orm import Session
from fastapi import HTTPException, UploadFile
from typing import Dict, Any
import json

from app.models.meeting import User, Meeting
from app.services.audio_service import AudioService
from app.services.whisper_service import WhisperService
from app.services.langgraph_service import LangGraphService
from app.services.vector_store_service import VectorStoreService


class MeetingService:
    """Service for orchestrating meeting processing workflow"""
    
    def __init__(self):
        """Initialize meeting service"""
        self.audio_service = AudioService()
        self.whisper_service = WhisperService()
        self.langgraph_service = LangGraphService()
        
        # Initialize vector store (optional - graceful degradation if not configured)
        try:
            self.vector_store = VectorStoreService()
        except Exception as e:
            print(f"Warning: Vector store not available: {e}")
            self.vector_store = None
    
    def get_or_create_user(self, db: Session, user_id: str) -> User:
        """
        Get existing user or create new one.
        
        Args:
            db: Database session
            user_id: User identifier
            
        Returns:
            User object
        """
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            user = User(id=user_id)
            db.add(user)
            db.commit()
            db.refresh(user)
        return user
    
    async def process_meeting(
        self,
        db: Session,
        user_id: str,
        audio_file: UploadFile
    ) -> Meeting:
        """
        Complete workflow: Audio → Whisper → LangGraph → Database.
        
        Args:
            db: Database session
            user_id: User identifier
            audio_file: Uploaded audio file
            
        Returns:
            Created Meeting object with all analysis
            
        Raises:
            HTTPException: If any step fails
        """
        audio_path = None
        
        try:
            # Step 1: Validate and save audio file
            print(f"Processing meeting for user: {user_id}")
            self.audio_service.validate_audio_file(audio_file)
            audio_path, original_filename = await self.audio_service.save_audio_file(audio_file)
            
            # Step 2: Transcribe with Whisper
            transcript = self.whisper_service.transcribe_audio(audio_path)
            
            # Step 3: Process with LangGraph
            analysis = self.langgraph_service.process_transcript(transcript)
            
            # Step 4: Get or create user
            user = self.get_or_create_user(db, user_id)
            
            # Step 5: Save to database
            meeting = Meeting(
                user_id=user_id,
                audio_filename=original_filename,
                transcript=transcript,
                summary=analysis["summary"],
                decisions=json.dumps(analysis["decisions"]),
                action_items=json.dumps(analysis["action_items"]),
                key_points=json.dumps(analysis["key_points"])
            )
            
            db.add(meeting)
            db.commit()
            db.refresh(meeting)
            
            print(f"Meeting created successfully: {meeting.id}")
            
            # Step 6: Index in vector store for RAG (if available)
            if self.vector_store:
                try:
                    self.vector_store.index_meeting(
                        user_id=user_id,
                        meeting_id=meeting.id,
                        transcript=transcript,
                        summary=analysis["summary"],
                        decisions=analysis["decisions"],
                        action_items=analysis["action_items"],
                        key_points=analysis["key_points"]
                    )
                    print(f"✓ Meeting indexed in vector store")
                except Exception as e:
                    # Log error but don't fail the upload
                    print(f"⚠ Vector store indexing failed: {e}")
            
            return meeting
            
        except HTTPException:
            raise
        except Exception as e:
            db.rollback()
            raise HTTPException(
                status_code=500,
                detail=f"Failed to process meeting: {str(e)}"
            )
        finally:
            # Cleanup: Delete temporary audio file
            if audio_path:
                self.audio_service.delete_audio_file(audio_path)
    
    def get_user_meetings(self, db: Session, user_id: str) -> list[Meeting]:
        """
        Get all meetings for a specific user.
        
        Args:
            db: Database session
            user_id: User identifier
            
        Returns:
            List of Meeting objects
        """
        return db.query(Meeting).filter(
            Meeting.user_id == user_id
        ).order_by(Meeting.created_at.desc()).all()
    
    def get_meeting_by_id(
        self,
        db: Session,
        meeting_id: str,
        user_id: str
    ) -> Meeting:
        """
        Get specific meeting by ID with user validation.
        
        Args:
            db: Database session
            meeting_id: Meeting identifier
            user_id: User identifier for authorization
            
        Returns:
            Meeting object
            
        Raises:
            HTTPException: If meeting not found or unauthorized
        """
        meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
        
        if not meeting:
            raise HTTPException(
                status_code=404,
                detail="Meeting not found"
            )
        
        # Verify user owns this meeting
        if meeting.user_id != user_id:
            raise HTTPException(
                status_code=403,
                detail="You do not have permission to access this meeting"
            )
        
        return meeting
