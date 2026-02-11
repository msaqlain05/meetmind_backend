"""Vector store service using Chroma Cloud HTTP API (Python 3.14 compatible)"""

import httpx
from typing import List, Dict, Any
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from app.config import settings


class VectorStoreService:
    """Service for managing Chroma Cloud vector store with user isolation using HTTP API"""
    
    def __init__(self):
        """Initialize Chroma Cloud HTTP client and embeddings"""
        if not settings.chroma_api_key:
            raise ValueError("CHROMA_API_KEY is required for vector store")
        
        # Chroma Cloud API configuration
        self.base_url = "https://api.trychroma.com"
        self.headers = {
            "Authorization": f"Bearer {settings.chroma_api_key}",
            "Content-Type": "application/json",
            "X-Chroma-Tenant": settings.chroma_tenant,
            "X-Chroma-Database": settings.chroma_database
        }
        
        # Initialize OpenAI embeddings
        self.embeddings = OpenAIEmbeddings(
            model=settings.embedding_model,
            openai_api_key=settings.openai_api_key
        )
        
        # Text splitter for chunking transcripts
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.rag_chunk_size,
            chunk_overlap=settings.rag_chunk_overlap,
            separators=["\n\n", "\n", ". ", " ", ""]
        )
    
    def _get_collection_name(self, user_id: str) -> str:
        """Get collection name for user isolation"""
        # Sanitize user_id for collection name
        safe_user_id = user_id.replace("-", "_").replace(" ", "_")
        return f"user_{safe_user_id}_meetings"
    
    def _get_or_create_collection(self, collection_name: str) -> str:
        """Get or create a collection, returns collection ID"""
        with httpx.Client(timeout=30.0) as client:
            # Try to get existing collection
            response = client.get(
                f"{self.base_url}/api/v1/collections/{collection_name}",
                headers=self.headers
            )
            
            if response.status_code == 200:
                return response.json()["id"]
            
            # Create new collection
            response = client.post(
                f"{self.base_url}/api/v1/collections",
                headers=self.headers,
                json={
                    "name": collection_name,
                    "metadata": {"user_collection": "true"}
                }
            )
            
            if response.status_code in [200, 201]:
                return response.json()["id"]
            
            raise Exception(f"Failed to create collection: {response.text}")
    
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
        """
        collection_name = self._get_collection_name(user_id)
        collection_id = self._get_or_create_collection(collection_name)
        
        # Prepare documents for indexing
        documents = []
        metadatas = []
        ids = []
        
        # 1. Chunk and index transcript
        transcript_chunks = self.text_splitter.split_text(transcript)
        for i, chunk in enumerate(transcript_chunks):
            documents.append(chunk)
            metadatas.append({
                "meeting_id": meeting_id,
                "type": "transcript",
                "chunk_index": str(i)
            })
            ids.append(f"{meeting_id}_transcript_{i}")
        
        # 2. Index summary
        documents.append(summary)
        metadatas.append({
            "meeting_id": meeting_id,
            "type": "summary"
        })
        ids.append(f"{meeting_id}_summary")
        
        # 3. Index decisions
        for i, decision in enumerate(decisions):
            documents.append(decision)
            metadatas.append({
                "meeting_id": meeting_id,
                "type": "decision"
            })
            ids.append(f"{meeting_id}_decision_{i}")
        
        # 4. Index action items
        for i, item in enumerate(action_items):
            documents.append(item)
            metadatas.append({
                "meeting_id": meeting_id,
                "type": "action_item"
            })
            ids.append(f"{meeting_id}_action_{i}")
        
        # 5. Index key points
        for i, point in enumerate(key_points):
            documents.append(point)
            metadatas.append({
                "meeting_id": meeting_id,
                "type": "key_point"
            })
            ids.append(f"{meeting_id}_keypoint_{i}")
        
        # Generate embeddings for all documents
        embeddings = self.embeddings.embed_documents(documents)
        
        # Add to Chroma Cloud collection via HTTP API
        with httpx.Client(timeout=60.0) as client:
            response = client.post(
                f"{self.base_url}/api/v1/collections/{collection_id}/add",
                headers=self.headers,
                json={
                    "ids": ids,
                    "embeddings": embeddings,
                    "documents": documents,
                    "metadatas": metadatas
                }
            )
            
            if response.status_code not in [200, 201]:
                raise Exception(f"Failed to add documents: {response.text}")
    
    def search(
        self,
        user_id: str,
        query: str,
        top_k: int = None
    ) -> List[Dict[str, Any]]:
        """
        Search user's meeting data using similarity search.
        
        Args:
            user_id: User identifier
            query: Search query
            top_k: Number of results to return
            
        Returns:
            List of relevant documents with metadata
        """
        if top_k is None:
            top_k = settings.rag_top_k
        
        collection_name = self._get_collection_name(user_id)
        
        try:
            with httpx.Client(timeout=30.0) as client:
                # Get collection
                response = client.get(
                    f"{self.base_url}/api/v1/collections/{collection_name}",
                    headers=self.headers
                )
                
                if response.status_code != 200:
                    return []  # No collection for this user
                
                collection_id = response.json()["id"]
                
                # Generate query embedding
                query_embedding = self.embeddings.embed_query(query)
                
                # Search collection
                response = client.post(
                    f"{self.base_url}/api/v1/collections/{collection_id}/query",
                    headers=self.headers,
                    json={
                        "query_embeddings": [query_embedding],
                        "n_results": top_k
                    }
                )
                
                if response.status_code != 200:
                    return []
                
                results = response.json()
                
                # Format results
                documents = []
                if results.get('ids') and len(results['ids'][0]) > 0:
                    for i in range(len(results['ids'][0])):
                        documents.append({
                            "content": results['documents'][0][i],
                            "metadata": results['metadatas'][0][i],
                            "distance": results.get('distances', [[0]])[0][i]
                        })
                
                return documents
                
        except Exception as e:
            print(f"Search error: {e}")
            return []
    
    def delete_meeting(self, user_id: str, meeting_id: str) -> None:
        """
        Delete all data for a specific meeting.
        
        Args:
            user_id: User identifier
            meeting_id: Meeting identifier
        """
        collection_name = self._get_collection_name(user_id)
        
        try:
            with httpx.Client(timeout=30.0) as client:
                # Get collection
                response = client.get(
                    f"{self.base_url}/api/v1/collections/{collection_name}",
                    headers=self.headers
                )
                
                if response.status_code != 200:
                    return
                
                collection_id = response.json()["id"]
                
                # Delete documents with matching meeting_id
                response = client.post(
                    f"{self.base_url}/api/v1/collections/{collection_id}/delete",
                    headers=self.headers,
                    json={
                        "where": {"meeting_id": meeting_id}
                    }
                )
                
        except Exception as e:
            print(f"Warning: Failed to delete meeting from vector store: {e}")
