"""SQLAlchemy ORM models for users and meetings"""

from sqlalchemy import Column, String, Text, ForeignKey, DateTime, Index
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.database import Base


def generate_uuid():
    """Generate UUID as string for compatibility with SQLite"""
    return str(uuid.uuid4())


class User(Base):
    """User model for storing user information"""
    
    __tablename__ = "users"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Relationship to meetings
    meetings = relationship("Meeting", back_populates="user", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<User(id={self.id})>"


class Meeting(Base):
    """Meeting model for storing meeting data and AI-generated insights"""
    
    __tablename__ = "meetings"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    audio_filename = Column(String(255), nullable=False)
    transcript = Column(Text, nullable=True)
    summary = Column(Text, nullable=True)
    decisions = Column(Text, nullable=True)  # JSON stored as text
    action_items = Column(Text, nullable=True)  # JSON stored as text
    key_points = Column(Text, nullable=True)  # JSON stored as text
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Relationship to user
    user = relationship("User", back_populates="meetings")
    
    # Index for faster user queries
    __table_args__ = (
        Index('idx_meetings_user_id', 'user_id'),
    )
    
    def __repr__(self):
        return f"<Meeting(id={self.id}, user_id={self.user_id}, filename={self.audio_filename})>"
