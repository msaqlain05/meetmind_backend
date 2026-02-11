"""RAG query API endpoints with improved error handling"""

from fastapi import APIRouter, HTTPException, Depends

from app.schemas.rag import QueryRequest, QueryResponse
from app.services.rag_service import RAGService
from app.exceptions import VectorStoreError, EmbeddingError
from app.logger import setup_logger

logger = setup_logger(__name__)
router = APIRouter(prefix="/query", tags=["rag"])

# Singleton RAG service instance
_rag_service_instance = None


def get_rag_service() -> RAGService:
    """
    Get or create RAG service instance (dependency injection).
    
    Returns:
        RAGService instance
    """
    global _rag_service_instance
    if _rag_service_instance is None:
        logger.info("Creating RAG service instance")
        _rag_service_instance = RAGService()
    return _rag_service_instance


@router.post("/", response_model=QueryResponse)
def query_meetings(
    request: QueryRequest,
    rag_service: RAGService = Depends(get_rag_service)
):
    """
    Query user's meeting data using RAG (Retrieval Augmented Generation).
    
    This endpoint:
    1. Retrieves relevant context from the user's meeting data in Chroma Cloud
    2. Uses an LLM to generate an answer grounded only in the retrieved context
    3. Returns the answer with source attribution and context snippets
    
    The system ensures per-user isolation - users can only query their own meetings.
    
    Args:
        request: Query request with user_id, query, and optional top_k
        rag_service: Injected RAG service instance
        
    Returns:
        Answer with source meetings and context snippets used
        
    Raises:
        HTTPException: With appropriate status code for different error types
        
    Example Request:
        ```json
        {
            "user_id": "user123",
            "query": "What decisions were made in my meetings?",
            "top_k": 5
        }
        ```
    """
    logger.info(f"Received query request from user {request.user_id}")
    
    try:
        result = rag_service.query_meetings(
            user_id=request.user_id,
            query=request.query,
            top_k=request.top_k
        )
        
        logger.info(f"Query completed successfully for user {request.user_id}")
        return QueryResponse(**result)
    
    except ValueError as e:
        # Invalid input parameters
        logger.warning(f"Invalid input from user {request.user_id}: {e}")
        raise HTTPException(
            status_code=400,
            detail=f"Invalid request: {str(e)}"
        )
    
    except EmbeddingError as e:
        # Embedding generation failed
        logger.error(f"Embedding error for user {request.user_id}: {e}")
        raise HTTPException(
            status_code=503,
            detail="Embedding service unavailable. Please try again later."
        )
    
    except VectorStoreError as e:
        # Vector store operation failed
        logger.error(f"Vector store error for user {request.user_id}: {e}")
        raise HTTPException(
            status_code=503,
            detail="Vector store unavailable. Please try again later."
        )
    
    except Exception as e:
        # Unexpected error
        logger.error(
            f"Unexpected error for user {request.user_id}: {e}",
            exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail="Internal server error. Please try again later."
        )
