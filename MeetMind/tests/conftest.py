"""Test configuration and fixtures"""

import pytest
import os
import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.database import Base
from app.main import app
from app.database import get_db


# Test database URL
TEST_DATABASE_URL = "sqlite:///./test_meetmind.db"


@pytest.fixture(scope="function")
def test_db():
    """Create a test database for each test"""
    # Create test engine
    engine = create_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False}
    )
    
    # Create all tables
    Base.metadata.create_all(bind=engine)
    
    # Create session
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = TestingSessionLocal()
    
    try:
        yield db
    finally:
        db.close()
        # Drop all tables after test
        Base.metadata.drop_all(bind=engine)
        # Remove test database file
        if os.path.exists("test_meetmind.db"):
            os.remove("test_meetmind.db")


@pytest.fixture(scope="function")
def client(test_db):
    """Create a test client with test database"""
    def override_get_db():
        try:
            yield test_db
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    
    with TestClient(app) as test_client:
        yield test_client
    
    app.dependency_overrides.clear()


@pytest.fixture
def sample_user_id():
    """Sample user ID for testing"""
    return "test-user-123"


@pytest.fixture
def sample_transcript():
    """Sample meeting transcript for testing"""
    return """
    Good morning everyone. Let's start our weekly team meeting.
    First, we need to discuss the new feature implementation.
    John, can you give us an update on the authentication module?
    
    Sure, I've completed the OAuth integration and it's ready for testing.
    We decided to use JWT tokens for session management.
    
    Great! Sarah, what about the database migration?
    
    The migration is scheduled for next Friday. We need to backup all data before proceeding.
    I'll send out a notification to all team members.
    
    Perfect. Any other topics to discuss?
    
    Yes, we should plan the next sprint. I suggest we focus on the user dashboard.
    Everyone agrees? Okay, let's make that our priority.
    
    Alright, meeting adjourned. Thanks everyone!
    """
