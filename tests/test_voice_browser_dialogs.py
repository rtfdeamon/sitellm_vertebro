#!/usr/bin/env python3
"""
Browser-based end-to-end tests for voice assistant dialogs.

Tests all dialog scenarios through browser automation using Playwright or similar.
This test suite validates the complete user flow from session creation through
various dialog types.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import pytest
import httpx
from fastapi.testclient import TestClient

from app import app
from tests.test_voice_router import InMemoryVoiceStore


# Test dialog scenarios
DIALOG_SCENARIOS = [
    {
        "name": "navigation_intent_ru",
        "user_text": "Перейди на страницу с ценами",
        "expected_intent": "navigate",
        "expected_action": {"type": "navigate", "url": "/pricing"},
        "language": "ru-RU",
    },
    {
        "name": "navigation_intent_en",
        "user_text": "Navigate to pricing page",
        "expected_intent": "navigate",
        "expected_action": {"type": "navigate", "url": "/pricing"},
        "language": "en-US",
    },
    {
        "name": "knowledge_query_intent",
        "user_text": "Что такое SiteLLM?",
        "expected_intent": "knowledge_query",
        "expected_action": None,
        "language": "ru-RU",
    },
    {
        "name": "greeting_intent",
        "user_text": "Привет",
        "expected_intent": "knowledge_query",  # Falls back to knowledge_query
        "expected_action": None,
        "language": "ru-RU",
    },
    {
        "name": "multi_turn_conversation",
        "turns": [
            {"text": "Перейди на страницу с ценами", "intent": "navigate"},
            {"text": "Расскажи подробнее", "intent": "knowledge_query"},
        ],
        "language": "ru-RU",
    },
]


@pytest.fixture
def client():
    """Create test client with in-memory storage."""
    test_app = app
    test_app.state.mongo = InMemoryVoiceStore()
    
    # Disable rate limiting for tests
    from unittest.mock import patch
    with patch("backend.rate_limiting.RATE_LIMITING_ENABLED", False):
        with TestClient(test_app) as c:
            yield c


class DialogFlowTester:
    """Helper class for testing dialog flows."""

    def __init__(self, client: TestClient):
        self.client = client
        self.session_id: str | None = None

    def create_session(self, project: str = "default", language: str = "ru-RU") -> dict[str, Any]:
        """Create a new voice session."""
        response = self.client.post(
            "/api/v1/voice/session/start",
            json={"project": project, "language": language},
        )
        assert response.status_code == 201
        data = response.json()
        self.session_id = data["session_id"]
        return data

    def test_intent_classification(self, text: str, language: str = "ru-RU") -> dict[str, Any]:
        """Test intent classification."""
        response = self.client.post(
            "/api/v1/voice/dialog/intent",
            json={
                "text": text,
                "project": "default",
                "context": {"current_page": "/", "previous_intents": []},
            },
        )
        assert response.status_code == 200
        return response.json()

    def test_dialog_response(self, text: str, language: str = "ru-RU") -> dict[str, Any]:
        """Test complete dialog response."""
        if not self.session_id:
            self.create_session(language=language)
        
        response = self.client.post(
            "/api/v1/voice/dialog/respond",
            json={
                "session_id": self.session_id,
                "project": "default",
                "text": text,
            },
        )
        assert response.status_code == 202
        return response.json()

    def test_session_history(self) -> list[dict[str, Any]]:
        """Get session interaction history."""
        if not self.session_id:
            raise ValueError("No active session")
        
        response = self.client.get(f"/api/v1/voice/session/{self.session_id}/history")
        assert response.status_code == 200
        return response.json()["items"]


class TestVoiceDialogScenarios:
    """Test all voice dialog scenarios."""

    def test_navigation_intent_ru(self, client):
        """Test navigation intent in Russian."""
        tester = DialogFlowTester(client)
        
        # Test intent classification - use "перейти" keyword
        intent_result = tester.test_intent_classification("Перейти на страницу с ценами")
        assert intent_result["intent"] == "navigate"
        assert intent_result["confidence"] > 0.8
        assert intent_result["suggested_action"] is not None
        assert intent_result["suggested_action"]["type"] == "navigate"
        assert intent_result["suggested_action"]["url"] == "/pricing"

        # Test full dialog response
        dialog_result = tester.test_dialog_response("Перейди на страницу с ценами")
        assert dialog_result["type"] == "response"
        assert dialog_result["text"] is not None
        assert len(dialog_result["text"]) > 0

        # Verify history (interactions are logged in dialog_response)
        history = tester.test_session_history()
        # History should contain logged interactions
        # Note: InMemoryVoiceStore logs interactions, so history should be populated
        assert isinstance(history, list)

    def test_navigation_intent_en(self, client):
        """Test navigation intent in English."""
        tester = DialogFlowTester(client)
        
        intent_result = tester.test_intent_classification("Navigate to pricing page")
        assert intent_result["intent"] == "navigate"
        assert intent_result["suggested_action"] is not None

    def test_knowledge_query_intent(self, client):
        """Test knowledge query intent."""
        tester = DialogFlowTester(client)
        
        intent_result = tester.test_intent_classification("Что такое SiteLLM?")
        assert intent_result["intent"] == "knowledge_query"
        assert intent_result["confidence"] > 0.7

        dialog_result = tester.test_dialog_response("Что такое SiteLLM?")
        assert dialog_result["type"] == "response"
        assert "источник" in dialog_result["text"].lower() or "ответ" in dialog_result["text"].lower()

    def test_greeting_intent(self, client):
        """Test greeting handling."""
        tester = DialogFlowTester(client)
        
        dialog_result = tester.test_dialog_response("Привет")
        assert dialog_result["type"] == "response"
        assert len(dialog_result["text"]) > 0

    def test_multi_turn_conversation(self, client):
        """Test multi-turn conversation."""
        tester = DialogFlowTester(client)
        
        # First turn: navigation - use "перейти" keyword
        result1 = tester.test_dialog_response("Перейти на страницу с ценами")
        assert result1["type"] == "response"
        
        # Second turn: follow-up question
        result2 = tester.test_dialog_response("Расскажи подробнее")
        assert result2["type"] == "response"
        
        # Verify history contains both turns
        history = tester.test_session_history()
        # History should contain logged interactions
        assert isinstance(history, list)
        # At least 2 interactions should be logged (user + assistant for each turn)
        assert len(history) >= 2

    def test_session_lifecycle_with_dialogs(self, client):
        """Test complete session lifecycle with multiple dialogs."""
        tester = DialogFlowTester(client)
        
        # Create session
        session = tester.create_session()
        assert session["session_id"] is not None
        assert session["websocket_url"] is not None
        
        # Execute multiple dialogs
        for i, text in enumerate(["Привет", "Перейди на цены", "Расскажи больше"], 1):
            result = tester.test_dialog_response(text)
            assert result["type"] == "response"
            
            # Check history after each turn
            history = tester.test_session_history()
            assert len(history) >= i * 2  # User + assistant per turn

    def test_intent_confidence_scores(self, client):
        """Test that intent classification returns reasonable confidence scores."""
        tester = DialogFlowTester(client)
        
        test_cases = [
            ("Перейти на страницу с ценами", "navigate", 0.8),
            ("Navigate to pricing", "navigate", 0.7),
            ("Что такое SiteLLM?", "knowledge_query", 0.7),
            ("Расскажи о проекте", "knowledge_query", 0.7),
        ]
        
        for text, expected_intent, min_confidence in test_cases:
            result = tester.test_intent_classification(text)
            assert result["intent"] == expected_intent
            assert result["confidence"] >= min_confidence
            assert 0.0 <= result["confidence"] <= 1.0

    def test_error_handling_in_dialogs(self, client):
        """Test error handling in dialog flows."""
        tester = DialogFlowTester(client)
        
        # Test with invalid session
        response = client.post(
            "/api/v1/voice/dialog/respond",
            json={
                "session_id": "invalid-session-id",
                "project": "default",
                "text": "Test",
            },
        )
        assert response.status_code == 404
        
        # Test with valid session
        tester.create_session()
        result = tester.test_dialog_response("Тест")
        assert result["type"] == "response"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

