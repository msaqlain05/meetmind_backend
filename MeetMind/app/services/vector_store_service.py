"""Vector store service with improved error handling and performance"""

import httpx
from typing import List, Dict, Any, Optional
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.config import settings
from app.constants import *
from app.logger import setup_logger
from app.exceptions import VectorStoreError, CollectionError, EmbeddingError

logger = setup_logger(__name__)


class VectorStoreService:
    """Service for managing Chroma Cloud vector store with user isolation"""
    
    def __init__(self):
        """Initialize Chroma Cloud HTTP client and embeddings"""
        if not settings.chroma_api_key:
            raise ValueError("CHROMA_API_KEY is required for vector store")
        
        logger.info("Initializing VectorStoreService")
        
        # Chroma Cloud API configuration
        self.base_url = CHROMA_API_BASE_URL
        self.headers = {
            "Authorization": f"Bearer {settings.chroma_api_key}",
            "Content-Type": "application/json",
            "X-Chroma-Tenant": settings.chroma_tenant,
            "X-Chroma-Database": settings.chroma_database
        }
        
        # Persistent HTTP client with connection pooling
        self.http_client = httpx.Client(
            timeout=HTTP_TIMEOUT_MEDIUM,
            limits=httpx.Limits(
                max_keepalive_connections=HTTP_MAX_KEEPALIVE,
                max_connections=HTTP_MAX_CONNECTIONS
            )
        )
        
        # Initialize OpenAI embeddings
        try:
            self.embeddings = OpenAIEmbeddings(
                model=settings.embedding_model,
                openai_api_key=settings.openai_api_key
            )
            logger.info(f"Initialized embeddings with model: {settings.embedding_model}")
        except Exception as e:
            logger.error(f"Failed to initialize embeddings: {e}")
            raise EmbeddingError(f"Embedding initialization failed: {str(e)}") from e
        
        # Text splitter for chunking transcripts
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.rag_chunk_size,
            chunk_overlap=settings.rag_chunk_overlap,
            separators=["\n\n", "\n", ". ", " ", ""]
        )
        
        logger.info("VectorStoreService initialized successfully")
    
    def __del__(self):
        """Cleanup HTTP client on destruction"""
        if hasattr(self, 'http_client'):
            try:
                self.http_client.close()
                logger.debug("HTTP client closed")
            except Exception as e:
                logger.warning(f"Error closing HTTP client: {e}")
    
    def _sanitize_user_id(self, user_id: str) -> str:
        """
        Sanitize user ID for collection name.
        
        Args:
            user_id: Raw user identifier
            
        Returns:
            Sanitized user ID safe for collection names
            
        Raises:
            ValueError: If user_id is empty or invalid
        """
        if not user_id or not user_id.strip():
            raise ValueError("user_id cannot be empty")
        
        # Remove invalid characters, keep only alphanumeric, dash, underscore
        safe_id = "".join(c if c.isalnum() or c in "-_" else "_" for c in user_id)
        
        # Limit length to prevent issues
        safe_id = safe_id[:100]
        
        if not safe_id:
            raise ValueError("user_id contains no valid characters")
        
        return safe_id
    
    def _get_collection_name(self, user_id: str) -> str:
        """Get collection name for user isolation"""
        safe_user_id = self._sanitize_user_id(user_id)
        return f"user_{safe_user_id}_meetings"
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(httpx.HTTPError)
    )
    def _get_or_create_collection(self, collection_name: str) -> str:
        """
        Get or create a collection with retry logic.
        
        Args:
            collection_name: Name of the collection
            
        Returns:
            Collection ID
            
        Raises:
            CollectionError: If collection operations fail
        """
        try:
            # Try to get existing collection
            response = self.http_client.get(
                f"{self.base_url}/api/{CHROMA_API_VERSION}/collections/{collection_name}",
                headers=self.headers
            )
            
            if response.status_code == 200:
                collection_id = response.json()["id"]
                logger.debug(f"Found existing collection: {collection_name}")
                return collection_id
            
            # Create new collection
            logger.info(f"Creating new collection: {collection_name}")
            response = self.http_client.post(
                f"{self.base_url}/api/{CHROMA_API_VERSION}/collections",
                headers=self.headers,
                json={
                    "name": collection_name,
                    "metadata": {"user_collection": "true"}
                }
            )
            
            if response.status_code in [200, 201]:
                collection_id = response.json()["id"]
                logger.info(f"Created collection: {collection_name} (ID: {collection_id})")
                return collection_id
            
            raise CollectionError(
                f"Failed to create collection: {response.status_code} - {response.text}"
            )
            
        except httpx.HTTPError as e:
            logger.error(f"HTTP error in _get_or_create_collection: {e}")
            raise CollectionError(f"HTTP error: {str(e)}") from e
        except Exception as e:
            logger.error(f"Unexpected error in _get_or_create_collection: {e}")
            raise CollectionError(f"Collection operation failed: {str(e)}") from e
    
    def index_meeting(
        self,
        user_id: str,
        meeting_id: str,
        transcript: str,
        summary: str,
        decisions: List[str],
        action_items: List[str],
        key_points: List[str]
    ) -> None:
        """
        Index meeting data in user's Chroma Cloud collection.
        
        Args:
            user_id: User identifier
            meeting_id: Meeting identifier
            transcript: Full meeting transcript
            summary: Meeting summary
            decisions: List of decisions
            action_items: List of action items
            key_points: List of key points
            
        Raises:
            VectorStoreError: If indexing fails
        """
        logger.info(f"Indexing meeting {meeting_id} for user {user_id}")
        
        try:
            # Get or create collection
            collection_name = self._get_collection_name(user_id)
            collection_id = self._get_or_create_collection(collection_name)
            
            # Prepare documents
            documents, metadatas, ids = self._prepare_documents(
                meeting_id, transcript, summary, decisions, action_items, key_points
            )
            
            logger.info(f"Generating embeddings for {len(documents)} documents")
            
            # Generate embeddings
            try:
                embeddings = self.embeddings.embed_documents(documents)
            except Exception as e:
                logger.error(f"Embedding generation failed: {e}")
                raise EmbeddingError(f"Failed to generate embeddings: {str(e)}") from e
            
            # Add to collection
            logger.debug(f"Adding documents to collection {collection_id}")
            response = self.http_client.post(
                f"{self.base_url}/api/{CHROMA_API_VERSION}/collections/{collection_id}/add",
                headers=self.headers,
                json={
                    "ids": ids,
                    "embeddings": embeddings,
                    "documents": documents,
                    "metadatas": metadatas
                },
                timeout=HTTP_TIMEOUT_LONG
            )
            
            if response.status_code not in [200, 201]:
                raise VectorStoreError(
                    f"Failed to add documents: {response.status_code} - {response.text}"
                )
            
            logger.info(f"Successfully indexed meeting {meeting_id} ({len(documents)} documents)")
            
        except (CollectionError, EmbeddingError) as e:
            # Re-raise custom exceptions
            raise
        except Exception as e:
            logger.error(f"Failed to index meeting {meeting_id}: {e}", exc_info=True)
            raise VectorStoreError(f"Indexing failed: {str(e)}") from e
    
    def _prepare_documents(
        self,
        meeting_id: str,
        transcript: str,
        summary: str,
        decisions: List[str],
        action_items: List[str],
        key_points: List[str]
    ) -> tuple[List[str], List[Dict], List[str]]:
        """
        Prepare documents for indexing.
        
        Args:
            meeting_id: Meeting identifier
            transcript: Full transcript
            summary: Summary text
            decisions: List of decisions
            action_items: List of action items
            key_points: List of key points
            
        Returns:
            Tuple of (documents, metadatas, ids)
        """
        documents = []
        metadatas = []
        ids = []
        
        def add_doc(content: str, doc_type: str, index: Optional[int] = None):
            """Helper to add a document"""
            documents.append(content)
            metadata = {"meeting_id": meeting_id, "type": doc_type}
            if index is not None:
                metadata["chunk_index"] = str(index)
            metadatas.append(metadata)
            
            id_suffix = f"_{index}" if index is not None else ""
            ids.append(f"{meeting_id}_{doc_type}{id_suffix}")
        
        # Chunk and add transcript
        transcript_chunks = self.text_splitter.split_text(transcript)
        logger.debug(f"Split transcript into {len(transcript_chunks)} chunks")
        for i, chunk in enumerate(transcript_chunks):
            add_doc(chunk, DOC_TYPE_TRANSCRIPT, i)
        
        # Add summary
        add_doc(summary, DOC_TYPE_SUMMARY)
        
        # Add decisions
        for i, decision in enumerate(decisions):
            add_doc(decision, DOC_TYPE_DECISION, i)
        
        # Add action items
        for i, item in enumerate(action_items):
            add_doc(item, DOC_TYPE_ACTION_ITEM, i)
        
        # Add key points
        for i, point in enumerate(key_points):
            add_doc(point, DOC_TYPE_KEY_POINT, i)
        
        logger.debug(f"Prepared {len(documents)} documents for indexing")
        return documents, metadatas, ids
    
    def search(
        self,
        user_id: str,
        query: str,
        top_k: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Search user's meeting data using similarity search.
        
        Args:
            user_id: User identifier
            query: Search query
            top_k: Number of results to return (default from settings)
            
        Returns:
            List of relevant documents with metadata
        """
        if top_k is None:
            top_k = settings.rag_top_k
        
        logger.info(f"Searching meetings for user {user_id}, query: '{query[:50]}...', top_k={top_k}")
        
        try:
            collection_name = self._get_collection_name(user_id)
            
            # Get collection
            response = self.http_client.get(
                f"{self.base_url}/api/{CHROMA_API_VERSION}/collections/{collection_name}",
                headers=self.headers
            )
            
            if response.status_code != 200:
                logger.warning(f"No collection found for user {user_id}")
                return []
            
            collection_id = response.json()["id"]
            
            # Generate query embedding
            try:
                query_embedding = self.embeddings.embed_query(query)
            except Exception as e:
                logger.error(f"Failed to generate query embedding: {e}")
                raise EmbeddingError(f"Query embedding failed: {str(e)}") from e
            
            # Search collection
            response = self.http_client.post(
                f"{self.base_url}/api/{CHROMA_API_VERSION}/collections/{collection_id}/query",
                headers=self.headers,
                json={
                    "query_embeddings": [query_embedding],
                    "n_results": top_k
                }
            )
            
            if response.status_code != 200:
                logger.error(f"Search failed: {response.status_code} - {response.text}")
                return []
            
            results = response.json()
            documents = self._format_search_results(results)
            
            logger.info(f"Found {len(documents)} results for user {user_id}")
            return documents
            
        except EmbeddingError:
            # Re-raise embedding errors
            raise
        except Exception as e:
            logger.error(f"Search error for user {user_id}: {e}", exc_info=True)
            return []  # Return empty results on error
    
    def _format_search_results(self, results: Dict) -> List[Dict[str, Any]]:
        """
        Format search results from Chroma API response.
        
        Args:
            results: Raw results from Chroma API
            
        Returns:
            Formatted list of documents
        """
        documents = []
        if results.get('ids') and len(results['ids'][0]) > 0:
            for i in range(len(results['ids'][0])):
                documents.append({
                    "content": results['documents'][0][i],
                    "metadata": results['metadatas'][0][i],
                    "distance": results.get('distances', [[0]])[0][i]
                })
        return documents
    
    def delete_meeting(self, user_id: str, meeting_id: str) -> None:
        """
        Delete all data for a specific meeting.
        
        Args:
            user_id: User identifier
            meeting_id: Meeting identifier
        """
        logger.info(f"Deleting meeting {meeting_id} for user {user_id}")
        
        try:
            collection_name = self._get_collection_name(user_id)
            
            # Get collection
            response = self.http_client.get(
                f"{self.base_url}/api/{CHROMA_API_VERSION}/collections/{collection_name}",
                headers=self.headers
            )
            
            if response.status_code != 200:
                logger.warning(f"No collection found for user {user_id}")
                return
            
            collection_id = response.json()["id"]
            
            # Delete documents with matching meeting_id
            response = self.http_client.post(
                f"{self.base_url}/api/{CHROMA_API_VERSION}/collections/{collection_id}/delete",
                headers=self.headers,
                json={
                    "where": {"meeting_id": meeting_id}
                }
            )
            
            if response.status_code in [200, 201]:
                logger.info(f"Successfully deleted meeting {meeting_id}")
            else:
                logger.warning(f"Delete operation returned status {response.status_code}")
                
        except Exception as e:
            logger.error(f"Failed to delete meeting {meeting_id}: {e}", exc_info=True)
            # Don't raise - deletion is best effort
