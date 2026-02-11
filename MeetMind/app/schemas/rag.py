"""Pydantic schemas for RAG query endpoints"""

from pydantic import BaseModel, Field
from typing import List
from datetime import datetime


class QueryRequest(BaseModel):
    """Request schema for RAG query"""
    user_id: str = Field(..., description="User identifier")
    query: str = Field(..., description="Question to ask about meetings")
    top_k: int = Field(default=5, description="Number of context chunks to retrieve", ge=1, le=20)


class ContextSnippet(BaseModel):
    """Context snippet used in generating answer"""
    type: str = Field(..., description="Type of content (transcript, decision, action_item, etc.)")
    meeting_id: str = Field(..., description="Source meeting ID")
    snippet: str = Field(..., description="Content snippet")
    relevance_score: float = Field(..., description="Relevance score (0-1)", ge=0, le=1)


class QueryResponse(BaseModel):
    """Response schema for RAG query"""
    answer: str = Field(..., description="Generated answer based on meeting context")
    sources: List[str] = Field(..., description="List of source meeting IDs")
    context_used: List[ContextSnippet] = Field(..., description="Context snippets used to generate answer")
