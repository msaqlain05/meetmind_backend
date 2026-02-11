"""RAG service for intelligent meeting queries"""

from typing import Dict, Any, List
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from app.services.vector_store_service import VectorStoreService
from app.config import settings


class RAGService:
    """Service for querying meeting data using RAG"""
    
    def __init__(self):
        """Initialize RAG service with vector store and LLM"""
        self.vector_store = VectorStoreService()
        
        # Use GPT-4o-mini for fast, cost-effective responses
        self.llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0,  # Deterministic answers
            api_key=settings.openai_api_key,
            max_tokens=1000
        )
    
    def query_meetings(
        self,
        user_id: str,
        query: str,
        top_k: int = None
    ) -> Dict[str, Any]:
        """
        Query user's meetings and generate answer from context.
        
        Args:
            user_id: User identifier
            query: User's question
            top_k: Number of context chunks to retrieve
            
        Returns:
            Dictionary with answer, sources, and context used
        """
        # 1. Retrieve relevant context from vector store
        context_docs = self.vector_store.search(user_id, query, top_k)
        
        if not context_docs:
            return {
                "answer": "I don't have any meeting data to answer this question. Please upload some meetings first.",
                "sources": [],
                "context_used": []
            }
        
        # 2. Build context string from retrieved documents
        context_parts = []
        for doc in context_docs:
            doc_type = doc['metadata'].get('type', 'unknown')
            content = doc['content']
            context_parts.append(f"[{doc_type}] {content}")
        
        context = "\n\n".join(context_parts)
        
        # 3. Generate answer using LLM with strict grounding
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a meeting assistant that answers questions ONLY using the provided meeting context.

Rules:
- Answer ONLY based on the context provided
- If the context doesn't contain the answer, say "I don't have information about that in your meetings"
- Be concise and specific
- Cite the type of information you're using (transcript, decision, action item, summary, key point)
- Do not make assumptions or add information not in the context"""),
            ("user", "Context from meetings:\n{context}\n\nQuestion: {query}")
        ])
        
        chain = prompt | self.llm
        response = chain.invoke({"context": context, "query": query})
        
        # 4. Extract source meeting IDs
        source_meetings = list(set([
            doc['metadata']['meeting_id'] 
            for doc in context_docs
        ]))
        
        # 5. Format context snippets for transparency
        context_used = []
        for doc in context_docs[:3]:  # Top 3 most relevant
            snippet = doc['content']
            if len(snippet) > 200:
                snippet = snippet[:200] + "..."
            
            context_used.append({
                "type": doc['metadata'].get('type', 'unknown'),
                "meeting_id": doc['metadata']['meeting_id'],
                "snippet": snippet
            })
        
        return {
            "answer": response.content,
            "sources": source_meetings,
            "context_used": context_used
        }
