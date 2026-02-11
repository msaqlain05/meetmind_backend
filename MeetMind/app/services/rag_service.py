"""RAG service with improved error handling and logging"""

from typing import Dict, Any, List, Optional
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

from app.services.vector_store_service import VectorStoreService
from app.config import settings
from app.constants import MODEL_GPT_4O_MINI, MAX_SNIPPET_LENGTH, MAX_CONTEXT_SNIPPETS
from app.logger import setup_logger
from app.exceptions import VectorStoreError, EmbeddingError

logger = setup_logger(__name__)


class RAGService:
    """Service for querying meeting data using Retrieval Augmented Generation"""
    
    def __init__(self):
        """Initialize RAG service with vector store and LLM"""
        logger.info("Initializing RAGService")
        
        try:
            self.vector_store = VectorStoreService()
        except Exception as e:
            logger.error(f"Failed to initialize vector store: {e}")
            raise
        
        try:
            self.llm = ChatOpenAI(
                model=MODEL_GPT_4O_MINI,
                temperature=0,  # Deterministic answers
                api_key=settings.openai_api_key,
                max_tokens=1000
            )
            logger.info(f"Initialized LLM with model: {MODEL_GPT_4O_MINI}")
        except Exception as e:
            logger.error(f"Failed to initialize LLM: {e}")
            raise
        
        logger.info("RAGService initialized successfully")
    
    def query_meetings(
        self,
        user_id: str,
        query: str,
        top_k: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Query user's meetings and generate answer from context.
        
        Args:
            user_id: User identifier
            query: User's question
            top_k: Number of context chunks to retrieve
            
        Returns:
            Dictionary with answer, sources, and context used
            
        Raises:
            ValueError: If inputs are invalid
            VectorStoreError: If vector store operations fail
        """
        # Validate inputs
        if not user_id or not user_id.strip():
            raise ValueError("user_id is required and cannot be empty")
        if not query or not query.strip():
            raise ValueError("query is required and cannot be empty")
        
        logger.info(f"Processing query for user {user_id}: '{query[:100]}...'")
        
        try:
            # Retrieve relevant context from vector store
            context_docs = self.vector_store.search(user_id, query, top_k)
            
            if not context_docs:
                logger.info(f"No context found for user {user_id}")
                return {
                    "answer": "I don't have any meeting data to answer this question. Please upload some meetings first.",
                    "sources": [],
                    "context_used": []
                }
            
            logger.info(f"Retrieved {len(context_docs)} context documents")
            
            # Build context string
            context = self._build_context(context_docs)
            
            # Generate answer using LLM
            logger.debug("Generating answer with LLM")
            answer = self._generate_answer(context, query)
            
            # Extract source meeting IDs
            source_meetings = list(set([
                doc['metadata']['meeting_id'] 
                for doc in context_docs
            ]))
            
            # Format context snippets for transparency
            context_used = self._format_context_snippets(context_docs)
            
            logger.info(
                f"Query completed successfully. "
                f"Found {len(source_meetings)} source meetings, "
                f"answer length: {len(answer)} chars"
            )
            
            return {
                "answer": answer,
                "sources": source_meetings,
                "context_used": context_used
            }
            
        except (VectorStoreError, EmbeddingError) as e:
            logger.error(f"Vector store/embedding error: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in query_meetings: {e}", exc_info=True)
            raise
    
    def _build_context(self, context_docs: List[Dict]) -> str:
        """
        Build context string from retrieved documents.
        
        Args:
            context_docs: List of retrieved documents
            
        Returns:
            Formatted context string
        """
        context_parts = []
        for doc in context_docs:
            doc_type = doc['metadata'].get('type', 'unknown')
            content = doc['content']
            context_parts.append(f"[{doc_type}] {content}")
        
        context = "\n\n".join(context_parts)
        logger.debug(f"Built context with {len(context)} characters")
        return context
    
    def _generate_answer(self, context: str, query: str) -> str:
        """
        Generate answer using LLM with strict grounding.
        
        Args:
            context: Context string from retrieved documents
            query: User's question
            
        Returns:
            Generated answer
        """
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a meeting assistant that answers questions ONLY using the provided meeting context.

Rules:
- Answer ONLY based on the context provided
- If the context doesn't contain the answer, say "I don't have information about that in your meetings"
- Be concise and specific
- Cite the type of information you're using (transcript, decision, action item, summary, key point)
- Do not make assumptions or add information not in the context
- If multiple meetings are relevant, mention that"""),
            ("user", "Context from meetings:\n{context}\n\nQuestion: {query}")
        ])
        
        try:
            chain = prompt | self.llm
            response = chain.invoke({"context": context, "query": query})
            return response.content
        except Exception as e:
            logger.error(f"LLM generation failed: {e}")
            raise RuntimeError(f"Failed to generate answer: {str(e)}") from e
    
    def _format_context_snippets(self, context_docs: List[Dict]) -> List[Dict]:
        """
        Format context snippets for response transparency.
        
        Args:
            context_docs: List of context documents
            
        Returns:
            List of formatted context snippets
        """
        context_used = []
        
        # Return top N most relevant documents
        for doc in context_docs[:MAX_CONTEXT_SNIPPETS]:
            snippet = doc['content']
            
            # Truncate long snippets
            if len(snippet) > MAX_SNIPPET_LENGTH:
                snippet = snippet[:MAX_SNIPPET_LENGTH] + "..."
            
            context_used.append({
                "type": doc['metadata'].get('type', 'unknown'),
                "meeting_id": doc['metadata']['meeting_id'],
                "snippet": snippet,
                "relevance_score": 1.0 - doc.get('distance', 0)  # Convert distance to score
            })
        
        return context_used
