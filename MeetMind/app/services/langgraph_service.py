"""LangGraph service for AI-powered meeting analysis"""

from typing import TypedDict, List, Dict, Any
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from fastapi import HTTPException
from app.config import settings
import json


class MeetingState(TypedDict):
    """State schema for LangGraph workflow"""
    transcript: str
    cleaned_transcript: str
    topics: List[str]
    summary: str
    decisions: List[str]
    action_items: List[str]
    key_points: List[str]


class LangGraphService:
    """Service for processing meeting transcripts using LangGraph"""
    
    def __init__(self):
        """Initialize LangGraph service with LLM"""
        if not settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY is required for LangGraph service")
        
        # Use GPT-4o-mini for faster processing and lower cost
        self.llm = ChatOpenAI(
            model="gpt-4o-mini",  # Faster and cheaper than gpt-3.5-turbo
            temperature=0.2,  # Lower temperature for more consistent results
            api_key=settings.openai_api_key,
            max_tokens=2000  # Limit response length for speed
        )
    
    def clean_transcript(self, state: MeetingState) -> MeetingState:
        """
        Node 1: Clean transcript by removing filler words and fixing grammar.
        
        Args:
            state: Current meeting state
            
        Returns:
            Updated state with cleaned transcript
        """
        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are a transcript editor. Clean the following meeting transcript by removing filler words (um, uh, like), fixing grammar, and improving readability. Preserve all important content and context."),
            ("user", "{transcript}")
        ])
        
        chain = prompt | self.llm
        response = chain.invoke({"transcript": state["transcript"]})
        
        state["cleaned_transcript"] = response.content.strip()
        return state
    
    def detect_topics(self, state: MeetingState) -> MeetingState:
        """
        Node 2: Detect main topics discussed in the meeting.
        
        Args:
            state: Current meeting state
            
        Returns:
            Updated state with detected topics
        """
        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are a meeting analyst. Identify the main topics discussed in this meeting. Return ONLY a JSON array of topic strings, nothing else."),
            ("user", "{transcript}")
        ])
        
        chain = prompt | self.llm
        response = chain.invoke({"transcript": state["cleaned_transcript"]})
        
        try:
            topics = json.loads(response.content.strip())
            if not isinstance(topics, list):
                topics = [response.content.strip()]
        except json.JSONDecodeError:
            # Fallback: split by newlines or commas
            topics = [t.strip() for t in response.content.strip().split('\n') if t.strip()]
        
        state["topics"] = topics
        return state
    
    def generate_summary(self, state: MeetingState) -> MeetingState:
        """
        Node 3: Generate concise meeting summary.
        
        Args:
            state: Current meeting state
            
        Returns:
            Updated state with summary
        """
        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are a meeting summarizer. Create a concise, professional summary of this meeting in 2-4 sentences. Focus on the main purpose, key discussions, and outcomes."),
            ("user", "Topics: {topics}\n\nTranscript: {transcript}")
        ])
        
        chain = prompt | self.llm
        response = chain.invoke({
            "topics": ", ".join(state["topics"]),
            "transcript": state["cleaned_transcript"]
        })
        
        state["summary"] = response.content.strip()
        return state
    
    def extract_decisions(self, state: MeetingState) -> MeetingState:
        """
        Node 4: Extract decisions made during the meeting.
        
        Args:
            state: Current meeting state
            
        Returns:
            Updated state with decisions
        """
        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are a meeting analyst. Extract all decisions that were made during this meeting. Return ONLY a JSON array of decision strings. If no decisions were made, return an empty array []."),
            ("user", "Topics: {topics}\n\nTranscript: {transcript}")
        ])
        
        chain = prompt | self.llm
        response = chain.invoke({
            "topics": ", ".join(state["topics"]),
            "transcript": state["cleaned_transcript"]
        })
        
        try:
            decisions = json.loads(response.content.strip())
            if not isinstance(decisions, list):
                decisions = []
        except json.JSONDecodeError:
            decisions = [d.strip() for d in response.content.strip().split('\n') if d.strip() and d.strip() != "[]"]
        
        state["decisions"] = decisions
        return state
    
    def extract_action_items(self, state: MeetingState) -> MeetingState:
        """
        Node 5: Extract action items and tasks from the meeting.
        
        Args:
            state: Current meeting state
            
        Returns:
            Updated state with action items
        """
        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are a meeting analyst. Extract all action items, tasks, and follow-ups mentioned in this meeting. Include who is responsible if mentioned. Return ONLY a JSON array of action item strings. If no action items exist, return an empty array []."),
            ("user", "Topics: {topics}\n\nTranscript: {transcript}")
        ])
        
        chain = prompt | self.llm
        response = chain.invoke({
            "topics": ", ".join(state["topics"]),
            "transcript": state["cleaned_transcript"]
        })
        
        try:
            action_items = json.loads(response.content.strip())
            if not isinstance(action_items, list):
                action_items = []
        except json.JSONDecodeError:
            action_items = [a.strip() for a in response.content.strip().split('\n') if a.strip() and a.strip() != "[]"]
        
        state["action_items"] = action_items
        return state
    
    def extract_key_points(self, state: MeetingState) -> MeetingState:
        """
        Node 6: Extract key discussion points from the meeting.
        
        Args:
            state: Current meeting state
            
        Returns:
            Updated state with key points
        """
        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are a meeting analyst. Extract the most important discussion points and insights from this meeting. Return ONLY a JSON array of key point strings (3-5 points)."),
            ("user", "Topics: {topics}\n\nTranscript: {transcript}")
        ])
        
        chain = prompt | self.llm
        response = chain.invoke({
            "topics": ", ".join(state["topics"]),
            "transcript": state["cleaned_transcript"]
        })
        
        try:
            key_points = json.loads(response.content.strip())
            if not isinstance(key_points, list):
                key_points = []
        except json.JSONDecodeError:
            key_points = [k.strip() for k in response.content.strip().split('\n') if k.strip() and k.strip() != "[]"]
        
        state["key_points"] = key_points
        return state
    
    def build_graph(self) -> StateGraph:
        """
        Build the LangGraph workflow.
        
        Returns:
            Compiled StateGraph
        """
        workflow = StateGraph(MeetingState)
        
        # Add nodes
        workflow.add_node("clean_transcript", self.clean_transcript)
        workflow.add_node("detect_topics", self.detect_topics)
        workflow.add_node("generate_summary", self.generate_summary)
        workflow.add_node("extract_decisions", self.extract_decisions)
        workflow.add_node("extract_action_items", self.extract_action_items)
        workflow.add_node("extract_key_points", self.extract_key_points)
        
        # Define edges - Sequential execution to avoid concurrent state updates
        workflow.set_entry_point("clean_transcript")
        workflow.add_edge("clean_transcript", "detect_topics")
        workflow.add_edge("detect_topics", "generate_summary")
        workflow.add_edge("generate_summary", "extract_decisions")
        workflow.add_edge("extract_decisions", "extract_action_items")
        workflow.add_edge("extract_action_items", "extract_key_points")
        workflow.add_edge("extract_key_points", END)
        
        return workflow.compile()
    
    def process_transcript(self, transcript: str) -> Dict[str, Any]:
        """
        Process meeting transcript through LangGraph workflow.
        
        Args:
            transcript: Raw meeting transcript
            
        Returns:
            Dictionary with summary, decisions, action_items, and key_points
            
        Raises:
            HTTPException: If processing fails
        """
        try:
            print("🤖 AI analysis...")
            
            # Initialize state
            initial_state: MeetingState = {
                "transcript": transcript,
                "cleaned_transcript": "",
                "topics": [],
                "summary": "",
                "decisions": [],
                "action_items": [],
                "key_points": []
            }
            
            # Build and run graph
            graph = self.build_graph()
            final_state = graph.invoke(initial_state)
            
            print("  ✓ Analysis complete")
            
            return {
                "summary": final_state.get("summary", ""),
                "decisions": final_state.get("decisions", []),
                "action_items": final_state.get("action_items", []),
                "key_points": final_state.get("key_points", [])
            }
            
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to process transcript with LangGraph: {str(e)}"
            )
