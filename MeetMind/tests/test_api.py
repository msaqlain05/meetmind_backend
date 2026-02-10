"""Integration tests for API endpoints"""

import pytest
import json
from io import BytesIO
from unittest.mock import patch, Mock


class TestHealthEndpoints:
    """Tests for health check endpoints"""
    
    def test_root_endpoint(self, client):
        """Test root endpoint"""
        response = client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "MeetMind" in data["message"]
        assert data["status"] == "running"
    
    def test_health_check(self, client):
        """Test health check endpoint"""
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"


class TestMeetingEndpoints:
    """Tests for meeting endpoints"""
    
    def test_upload_meeting_missing_user_id(self, client):
        """Test upload without user_id"""
        files = {
            "audio_file": ("test.mp3", BytesIO(b"data"), "audio/mpeg")
        }
        
        response = client.post("/meetings/upload", files=files)
        
        assert response.status_code == 422  # Validation error
    
    def test_upload_meeting_missing_file(self, client, sample_user_id):
        """Test upload without audio file"""
        data = {"user_id": sample_user_id}
        
        response = client.post("/meetings/upload", data=data)
        
        assert response.status_code == 422  # Validation error
    
    def test_upload_meeting_invalid_file_type(self, client, sample_user_id):
        """Test upload with invalid file type"""
        files = {
            "audio_file": ("test.txt", BytesIO(b"text data"), "text/plain")
        }
        data = {"user_id": sample_user_id}
        
        response = client.post("/meetings/upload", files=files, data=data)
        
        assert response.status_code == 400
        assert "Invalid file type" in response.json()["detail"]
    
    def test_get_user_meetings_empty(self, client, sample_user_id):
        """Test getting meetings for user with no meetings"""
        response = client.get(f"/meetings/user/{sample_user_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == sample_user_id
        assert data["meetings"] == []
        assert data["total"] == 0
    
    def test_get_user_meetings_with_data(self, client, test_db, sample_user_id):
        """Test getting meetings for user with meetings"""
        from app.models.meeting import User, Meeting
        
        # Create user and meetings
        user = User(id=sample_user_id)
        test_db.add(user)
        test_db.commit()
        
        meeting1 = Meeting(
            user_id=sample_user_id,
            audio_filename="meeting1.mp3",
            transcript="Transcript 1",
            summary="Summary 1",
            decisions=json.dumps(["Decision 1"]),
            action_items=json.dumps(["Action 1"]),
            key_points=json.dumps(["Point 1"])
        )
        meeting2 = Meeting(
            user_id=sample_user_id,
            audio_filename="meeting2.mp3",
            transcript="Transcript 2",
            summary="Summary 2",
            decisions=json.dumps([]),
            action_items=json.dumps([]),
            key_points=json.dumps([])
        )
        test_db.add_all([meeting1, meeting2])
        test_db.commit()
        
        response = client.get(f"/meetings/user/{sample_user_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == sample_user_id
        assert data["total"] == 2
        assert len(data["meetings"]) == 2
    
    def test_get_meeting_detail_success(self, client, test_db, sample_user_id):
        """Test getting meeting details"""
        from app.models.meeting import User, Meeting
        
        # Create user and meeting
        user = User(id=sample_user_id)
        test_db.add(user)
        test_db.commit()
        
        meeting = Meeting(
            user_id=sample_user_id,
            audio_filename="test.mp3",
            transcript="Full transcript",
            summary="Full summary",
            decisions=json.dumps(["Decision 1", "Decision 2"]),
            action_items=json.dumps(["Action 1"]),
            key_points=json.dumps(["Point 1", "Point 2", "Point 3"])
        )
        test_db.add(meeting)
        test_db.commit()
        
        response = client.get(f"/meetings/{meeting.id}?user_id={sample_user_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["meeting_id"] == meeting.id
        assert data["user_id"] == sample_user_id
        assert data["transcript"] == "Full transcript"
        assert len(data["decisions"]) == 2
        assert len(data["action_items"]) == 1
        assert len(data["key_points"]) == 3
    
    def test_get_meeting_detail_not_found(self, client, sample_user_id):
        """Test getting non-existent meeting"""
        response = client.get(f"/meetings/nonexistent-id?user_id={sample_user_id}")
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
    
    def test_get_meeting_detail_wrong_user(self, client, test_db):
        """Test getting meeting with wrong user_id (authorization)"""
        from app.models.meeting import User, Meeting
        
        # Create two users
        user1 = User(id="user-1")
        user2 = User(id="user-2")
        test_db.add_all([user1, user2])
        test_db.commit()
        
        # Create meeting for user1
        meeting = Meeting(
            user_id="user-1",
            audio_filename="test.mp3",
            transcript="Private meeting",
            summary="Summary"
        )
        test_db.add(meeting)
        test_db.commit()
        
        # Try to access with user2
        response = client.get(f"/meetings/{meeting.id}?user_id=user-2")
        
        assert response.status_code == 403
        assert "permission" in response.json()["detail"].lower()
    
    def test_get_meeting_detail_missing_user_id(self, client, test_db, sample_user_id):
        """Test getting meeting without user_id parameter"""
        from app.models.meeting import User, Meeting
        
        user = User(id=sample_user_id)
        test_db.add(user)
        test_db.commit()
        
        meeting = Meeting(
            user_id=sample_user_id,
            audio_filename="test.mp3",
            transcript="Test"
        )
        test_db.add(meeting)
        test_db.commit()
        
        response = client.get(f"/meetings/{meeting.id}")
        
        assert response.status_code == 422  # Validation error
