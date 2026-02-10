"""Audio file handling service"""

import os
import uuid
from typing import Tuple
from fastapi import UploadFile, HTTPException
from app.config import settings


class AudioService:
    """Service for handling audio file operations"""
    
    ALLOWED_EXTENSIONS = {".wav", ".mp3", ".webm", ".m4a", ".ogg"}
    ALLOWED_MIME_TYPES = {
        "audio/wav", "audio/wave", "audio/x-wav",
        "audio/mpeg", "audio/mp3",
        "audio/webm",
        "audio/mp4", "audio/x-m4a",
        "audio/ogg"
    }
    
    @staticmethod
    def validate_audio_file(file: UploadFile) -> None:
        """
        Validate audio file type and size.
        
        Args:
            file: Uploaded file to validate
            
        Raises:
            HTTPException: If file is invalid
        """
        # Check file extension
        file_ext = os.path.splitext(file.filename)[1].lower()
        if file_ext not in AudioService.ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file type. Allowed: {', '.join(AudioService.ALLOWED_EXTENSIONS)}"
            )
        
        # Check MIME type if available
        if file.content_type and file.content_type not in AudioService.ALLOWED_MIME_TYPES:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid content type: {file.content_type}"
            )
    
    @staticmethod
    async def save_audio_file(file: UploadFile) -> Tuple[str, str]:
        """
        Save uploaded audio file to disk.
        
        Args:
            file: Uploaded audio file
            
        Returns:
            Tuple of (file_path, original_filename)
            
        Raises:
            HTTPException: If file save fails
        """
        try:
            # Generate unique filename
            file_ext = os.path.splitext(file.filename)[1].lower()
            unique_filename = f"{uuid.uuid4()}{file_ext}"
            file_path = os.path.join(settings.upload_dir, unique_filename)
            
            # Save file
            with open(file_path, "wb") as buffer:
                content = await file.read()
                
                # Check file size
                size_mb = len(content) / (1024 * 1024)
                if size_mb > settings.max_upload_size_mb:
                    raise HTTPException(
                        status_code=413,
                        detail=f"File too large. Maximum size: {settings.max_upload_size_mb}MB"
                    )
                
                buffer.write(content)
            
            return file_path, file.filename
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to save audio file: {str(e)}"
            )
    
    @staticmethod
    def delete_audio_file(file_path: str) -> None:
        """
        Delete audio file from disk.
        
        Args:
            file_path: Path to file to delete
        """
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
        except Exception as e:
            # Log error but don't raise - cleanup is best effort
            print(f"Warning: Failed to delete audio file {file_path}: {str(e)}")
