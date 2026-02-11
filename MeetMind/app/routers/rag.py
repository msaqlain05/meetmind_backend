"""RAG query API endpoints"""

from fastapi import APIRouter, HTTPException
from app.schemas.rag import QueryRequest, QueryResponse
from app.services.rag_service import RAGService

router = APIRouter(prefix="/query", tags=["rag"])


@router.post("/", response_model=QueryResponse)
def query_meetings(request: QueryRequest):
    """
    Query user's meeting data using RAG (Retrieval Augmented Generation).
    
    This endpoint:
    1. Retrieves relevant context from the user's meeting data in Chroma Cloud
    2. Uses an LLM to generate an answer grounded only in the retrieved context
    3. Returns the answer with source attribution
    
    The system ensures per-user isolation - users can only query their own meetings.
    
    Args:
        request: Query request with user_id, query, and optional top_k
        
    Returns:
        Answer with source meetings and context snippets used
        
    Example:
        ```json
        {
            "user_id": "user123",
            "query": "What decisions were made in my meetings?",
            "top_k": 5
        }
        ```
    """
    try:
        rag_service = RAGService()
        result = rag_service.query_meetings(
            user_id=request.user_id,
            query=request.query,
            top_k=request.top_k
        )
        
        return QueryResponse(**result)
    
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Query failed: {str(e)}"
        )
