"""Unit tests for LangGraph service"""

import pytest
from unittest.mock import patch
from app.services.langgraph_service import LangGraphService


class TestLangGraphService:
    """Tests for LangGraphService"""
    
    def test_service_requires_api_key(self):
        """Test that service requires OpenAI API key"""
        with patch('app.config.settings.openai_api_key', None):
            with pytest.raises(ValueError, match="OPENAI_API_KEY is required"):
                LangGraphService()
    
    def test_service_initialization(self):
        """Test service initializes with API key"""
        with patch('app.config.settings.openai_api_key', 'test-key'):
            service = LangGraphService()
            assert service.llm is not None
    
    def test_build_graph(self):
        """Test graph building"""
        with patch('app.config.settings.openai_api_key', 'test-key'):
            service = LangGraphService()
            graph = service.build_graph()
            
            assert graph is not None
            # Graph should be compiled and ready to use

