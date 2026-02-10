"""Unit tests for database models"""

import pytest
from datetime import datetime
from app.models.meeting import User, Meeting
import json


class TestUserModel:
    """Tests for User model"""
    
    def test_create_user(self, test_db):
        """Test creating a user"""
        user = User(id="user-123")
        test_db.add(user)
        test_db.commit()
        
        assert user.id == "user-123"
        assert user.created_at is not None
        assert isinstance(user.created_at, datetime)
    
    def test_user_meetings_relationship(self, test_db):
        """Test user-meetings relationship"""
        user = User(id="user-456")
        test_db.add(user)
        test_db.commit()
        
        meeting = Meeting(
            user_id=user.id,
            audio_filename="test.mp3",
            transcript="Test transcript"
        )
        test_db.add(meeting)
        test_db.commit()
        
        assert len(user.meetings) == 1
        assert user.meetings[0].audio_filename == "test.mp3"


class TestMeetingModel:
    """Tests for Meeting model"""
    
    def test_create_meeting(self, test_db):
        """Test creating a meeting"""
        user = User(id="user-789")
        test_db.add(user)
        test_db.commit()
        
        meeting = Meeting(
            user_id=user.id,
            audio_filename="meeting.wav",
            transcript="Hello world",
            summary="Test summary",
            decisions=json.dumps(["Decision 1", "Decision 2"]),
            action_items=json.dumps(["Action 1"]),
            key_points=json.dumps(["Point 1", "Point 2"])
        )
        test_db.add(meeting)
        test_db.commit()
        
        assert meeting.id is not None
        assert meeting.user_id == "user-789"
        assert meeting.audio_filename == "meeting.wav"
        assert meeting.transcript == "Hello world"
        assert meeting.summary == "Test summary"
        assert json.loads(meeting.decisions) == ["Decision 1", "Decision 2"]
        assert json.loads(meeting.action_items) == ["Action 1"]
        assert json.loads(meeting.key_points) == ["Point 1", "Point 2"]
    
    def test_meeting_user_relationship(self, test_db):
        """Test meeting-user relationship"""
        user = User(id="user-999")
        test_db.add(user)
        test_db.commit()
        
        meeting = Meeting(
            user_id=user.id,
            audio_filename="test.mp3",
            transcript="Test"
        )
        test_db.add(meeting)
        test_db.commit()
        
        assert meeting.user.id == "user-999"
    
    def test_cascade_delete(self, test_db):
        """Test that deleting user deletes meetings"""
        user = User(id="user-cascade")
        test_db.add(user)
        test_db.commit()
        
        meeting1 = Meeting(user_id=user.id, audio_filename="m1.mp3", transcript="T1")
        meeting2 = Meeting(user_id=user.id, audio_filename="m2.mp3", transcript="T2")
        test_db.add_all([meeting1, meeting2])
        test_db.commit()
        
        # Delete user
        test_db.delete(user)
        test_db.commit()
        
        # Check meetings are deleted
        meetings = test_db.query(Meeting).filter(Meeting.user_id == "user-cascade").all()
        assert len(meetings) == 0
