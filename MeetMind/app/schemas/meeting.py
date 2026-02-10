"""Pydantic schemas for request validation and response serialization"""

from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


class MeetingUploadResponse(BaseModel):
    """Response schema for meeting upload endpoint"""
    
    meeting_id: str = Field(..., description="Unique meeting identifier")
    user_id: str = Field(..., description="User identifier")
    status: str = Field(default="completed", description="Processing status")
    transcript: str = Field(..., description="Full meeting transcript")
    summary: str = Field(..., description="Meeting summary")
    decisions: List[str] = Field(default_factory=list, description="Decisions made in meeting")
    action_items: List[str] = Field(default_factory=list, description="Action items identified")
    key_points: List[str] = Field(default_factory=list, description="Key discussion points")
    created_at: datetime = Field(..., description="Meeting creation timestamp")
    
    class Config:
        from_attributes = True


class MeetingDetailResponse(BaseModel):
    """Response schema for meeting detail endpoint"""
    
    meeting_id: str = Field(..., description="Unique meeting identifier")
    user_id: str = Field(..., description="User identifier")
    audio_filename: str = Field(..., description="Original audio filename")
    transcript: str = Field(..., description="Full meeting transcript")
    summary: str = Field(..., description="Meeting summary")
    decisions: List[str] = Field(default_factory=list, description="Decisions made in meeting")
    action_items: List[str] = Field(default_factory=list, description="Action items identified")
    key_points: List[str] = Field(default_factory=list, description="Key discussion points")
    created_at: datetime = Field(..., description="Meeting creation timestamp")
    
    class Config:
        from_attributes = True


class MeetingListItem(BaseModel):
    """Schema for individual meeting in list"""
    
    meeting_id: str = Field(..., description="Unique meeting identifier")
    audio_filename: str = Field(..., description="Original audio filename")
    summary: str = Field(..., description="Meeting summary")
    created_at: datetime = Field(..., description="Meeting creation timestamp")
    
    class Config:
        from_attributes = True


class UserMeetingsResponse(BaseModel):
    """Response schema for user meetings list endpoint"""
    
    user_id: str = Field(..., description="User identifier")
    meetings: List[MeetingListItem] = Field(default_factory=list, description="List of meetings")
    total: int = Field(..., description="Total number of meetings")
    
    class Config:
        from_attributes = True
