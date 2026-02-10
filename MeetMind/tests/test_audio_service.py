"""Unit tests for audio service"""

import pytest
import os
import tempfile
from io import BytesIO
from fastapi import UploadFile, HTTPException
from app.services.audio_service import AudioService


class TestAudioService:
    """Tests for AudioService"""
    
    def test_validate_audio_file_valid_wav(self):
        """Test validation with valid WAV file"""
        file = UploadFile(
            filename="test.wav",
            file=BytesIO(b"fake audio data"),
            headers={"content-type": "audio/wav"}
        )
        
        # Should not raise exception
        AudioService.validate_audio_file(file)
    
    def test_validate_audio_file_valid_mp3(self):
        """Test validation with valid MP3 file"""
        file = UploadFile(
            filename="test.mp3",
            file=BytesIO(b"fake audio data"),
            headers={"content-type": "audio/mpeg"}
        )
        
        AudioService.validate_audio_file(file)
    
    def test_validate_audio_file_invalid_extension(self):
        """Test validation with invalid file extension"""
        file = UploadFile(
            filename="test.txt",
            file=BytesIO(b"fake data"),
            headers={"content-type": "text/plain"}
        )
        
        with pytest.raises(HTTPException) as exc_info:
            AudioService.validate_audio_file(file)
        
        assert exc_info.value.status_code == 400
        assert "Invalid file type" in exc_info.value.detail
    
    def test_validate_audio_file_invalid_mime_type(self):
        """Test validation with invalid MIME type"""
        file = UploadFile(
            filename="test.mp3",
            file=BytesIO(b"fake data"),
            headers={"content-type": "application/pdf"}
        )
        
        with pytest.raises(HTTPException) as exc_info:
            AudioService.validate_audio_file(file)
        
        assert exc_info.value.status_code == 400
        assert "Invalid content type" in exc_info.value.detail
    
    @pytest.mark.asyncio
    async def test_save_audio_file(self):
        """Test saving audio file"""
        # Create fake audio file
        content = b"fake audio content" * 100
        file = UploadFile(
            filename="test_audio.mp3",
            file=BytesIO(content)
        )
        
        # Save file
        file_path, original_filename = await AudioService.save_audio_file(file)
        
        try:
            assert os.path.exists(file_path)
            assert original_filename == "test_audio.mp3"
            assert file_path.endswith(".mp3")
            
            # Verify file content
            with open(file_path, "rb") as f:
                saved_content = f.read()
            assert saved_content == content
        finally:
            # Cleanup
            if os.path.exists(file_path):
                os.remove(file_path)
    
    @pytest.mark.asyncio
    async def test_save_audio_file_too_large(self):
        """Test saving file that exceeds size limit"""
        # Create file larger than max size (100MB default)
        large_content = b"x" * (101 * 1024 * 1024)  # 101 MB
        file = UploadFile(
            filename="large.mp3",
            file=BytesIO(large_content)
        )
        
        with pytest.raises(HTTPException) as exc_info:
            await AudioService.save_audio_file(file)
        
        assert exc_info.value.status_code == 413
        assert "too large" in exc_info.value.detail.lower()
    
    def test_delete_audio_file(self):
        """Test deleting audio file"""
        # Create temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp:
            tmp.write(b"test content")
            tmp_path = tmp.name
        
        assert os.path.exists(tmp_path)
        
        # Delete file
        AudioService.delete_audio_file(tmp_path)
        
        assert not os.path.exists(tmp_path)
    
    def test_delete_nonexistent_file(self):
        """Test deleting file that doesn't exist (should not raise error)"""
        # Should not raise exception
        AudioService.delete_audio_file("/nonexistent/path/file.mp3")
