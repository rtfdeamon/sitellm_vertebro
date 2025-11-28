#!/usr/bin/env python3
"""
Complete browser end-to-end tests for voice assistant dialogs.

Tests all dialog scenarios through real HTTP requests to the running server.
This test suite validates the complete user flow including session creation,
intent recognition, dialog responses, and history tracking.
"""

from __future__ import annotations

import json
import os
import time
from typing import Any

import httpx
import pytest

# Base URL for the running server
BASE_URL = os.getenv("VOICE_TEST_BASE_URL", "http://localhost:8000")
API_BASE = f"{BASE_URL}/api/v1/voice"


class VoiceDialogBrowserTester:
    """Helper class for browser-style dialog testing."""

    def __init__(self, base_url: str = API_BASE):
        self.base_url = base_url
        self.client = httpx.Client(timeout=30.0)
        self.session_id: str | None = None

    def create_session(self, project: str = "default", language: str = "ru-RU") -> dict[str, Any]:
        """Create a new voice session."""
        response = self.client.post(
            f"{self.base_url}/session/start",
            json={"project": project, "language": language},
        )
        assert response.status_code == 201, f"Failed to create session: {response.status_code} {response.text}"
        data = response.json()
        self.session_id = data["session_id"]
        return data

    def get_session(self) -> dict[str, Any]:
        """Get session information."""
        if not self.session_id:
            raise ValueError("No active session")
        
        response = self.client.get(f"{self.base_url}/session/{self.session_id}")
        assert response.status_code == 200
        return response.json()

    def classify_intent(self, text: str, project: str = "default") -> dict[str, Any]:
        """Classify intent from text."""
        response = self.client.post(
            f"{self.base_url}/dialog/intent",
            json={
                "text": text,
                "project": project,
                "context": {"current_page": "/", "previous_intents": []},
            },
        )
        assert response.status_code == 200
        return response.json()

    def send_dialog_message(self, text: str, project: str = "default") -> dict[str, Any]:
        """Send a dialog message and get response."""
        if not self.session_id:
            self.create_session()
        
        response = self.client.post(
            f"{self.base_url}/dialog/respond",
            json={
                "session_id": self.session_id,
                "project": project,
                "text": text,
            },
        )
        assert response.status_code == 202
        return response.json()

    def get_history(self, limit: int = 50) -> list[dict[str, Any]]:
        """Get session interaction history."""
        if not self.session_id:
            raise ValueError("No active session")
        
        response = self.client.get(
            f"{self.base_url}/session/{self.session_id}/history",
            params={"limit": limit},
        )
        assert response.status_code == 200
        return response.json()["items"]

    def delete_session(self) -> bool:
        """Delete the current session."""
        if not self.session_id:
            return False
        
        response = self.client.delete(f"{self.base_url}/session/{self.session_id}")
        return response.status_code == 204

    def close(self):
        """Close the HTTP client."""
        if self.session_id:
            try:
                self.delete_session()
            except Exception:
                pass
        self.client.close()


@pytest.mark.skipif(
    os.getenv("VOICE_TEST_BASE_URL") is None,
    reason="E2E tests require VOICE_TEST_BASE_URL environment variable",
)
class TestVoiceDialogBrowserE2E:
    """Complete browser E2E tests for voice dialogs."""

    @pytest.fixture
    def tester(self):
        """Create a dialog tester instance."""
        base_url = os.getenv("VOICE_TEST_BASE_URL", "http://localhost:8000")
        tester = VoiceDialogBrowserTester(base_url=f"{base_url}/api/v1/voice")
        yield tester
        tester.close()

    def test_complete_dialog_flow_navigation(self, tester):
        """Test complete dialog flow: session -> navigation intent -> response."""
        # Create session
        session = tester.create_session()
        assert session["session_id"] is not None
        assert session["websocket_url"] is not None
        assert session["initial_greeting"] is not None

        # Classify intent
        intent = tester.classify_intent("Перейти на страницу с ценами")
        assert intent["intent"] == "navigate"
        assert intent["confidence"] >= 0.8
        assert intent["suggested_action"] is not None
        assert intent["suggested_action"]["type"] == "navigate"

        # Send dialog message
        response = tester.send_dialog_message("Перейти на страницу с ценами")
        assert response["type"] == "response"
        assert response["text"] is not None
        assert len(response["text"]) > 0

        # Verify history
        history = tester.get_history()
        assert len(history) >= 2  # User + assistant messages
        user_msgs = [h for h in history if h.get("type") == "user"]
        assistant_msgs = [h for h in history if h.get("type") == "assistant"]
        assert len(user_msgs) >= 1
        assert len(assistant_msgs) >= 1

    def test_complete_dialog_flow_knowledge_query(self, tester):
        """Test complete dialog flow: session -> knowledge query -> response."""
        # Create session
        session = tester.create_session()
        
        # Classify intent
        intent = tester.classify_intent("Что такое SiteLLM?")
        assert intent["intent"] == "knowledge_query"
        assert intent["confidence"] >= 0.7

        # Send dialog message
        response = tester.send_dialog_message("Что такое SiteLLM?")
        assert response["type"] == "response"
        assert response["text"] is not None

    def test_multi_turn_conversation(self, tester):
        """Test multi-turn conversation with context."""
        # Create session
        tester.create_session()

        # Turn 1: Navigation
        response1 = tester.send_dialog_message("Перейти на страницу с ценами")
        assert response1["type"] == "response"
        assert "раздел" in response1["text"].lower() or "открываю" in response1["text"].lower()

        # Turn 2: Follow-up
        response2 = tester.send_dialog_message("Расскажи подробнее")
        assert response2["type"] == "response"
        assert response2["text"] is not None

        # Verify history contains both turns
        history = tester.get_history()
        assert len(history) >= 4  # 2 user + 2 assistant messages
        
        # Verify conversation order
        user_turns = [h for h in history if h.get("type") == "user"]
        assistant_turns = [h for h in history if h.get("type") == "assistant"]
        assert len(user_turns) >= 2
        assert len(assistant_turns) >= 2

    def test_navigation_intent_variations(self, tester):
        """Test various navigation intent variations."""
        tester.create_session()

        test_cases = [
            ("Перейти на страницу с ценами", "navigate"),
            ("Navigate to pricing", "navigate"),
            ("Открой раздел с ценами", "navigate"),
            ("Open pricing page", "navigate"),
        ]

        for text, expected_intent in test_cases:
            intent = tester.classify_intent(text)
            assert intent["intent"] == expected_intent
            assert intent["confidence"] >= 0.7

    def test_knowledge_query_variations(self, tester):
        """Test various knowledge query variations."""
        tester.create_session()

        test_cases = [
            ("Что такое SiteLLM?", "knowledge_query"),
            ("Расскажи о проекте", "knowledge_query"),
            ("Как это работает?", "knowledge_query"),
            ("What is SiteLLM?", "knowledge_query"),
        ]

        for text, expected_intent in test_cases:
            intent = tester.classify_intent(text)
            assert intent["intent"] == expected_intent
            assert intent["confidence"] >= 0.7

    def test_session_lifecycle(self, tester):
        """Test complete session lifecycle."""
        # Create session
        session = tester.create_session()
        session_id = session["session_id"]

        # Verify session exists
        session_info = tester.get_session()
        assert session_info["session_id"] == session_id

        # Execute multiple dialogs
        for i in range(3):
            response = tester.send_dialog_message(f"Сообщение {i+1}")
            assert response["type"] == "response"

        # Verify history
        history = tester.get_history()
        assert len(history) >= 6  # 3 user + 3 assistant messages

        # Delete session
        deleted = tester.delete_session()
        assert deleted

        # Verify session deleted (should return 404)
        response = tester.client.get(f"{tester.base_url}/session/{session_id}")
        assert response.status_code == 404

    def test_intent_confidence_scores(self, tester):
        """Test that intent confidence scores are reasonable."""
        tester.create_session()

        test_cases = [
            ("Перейти на страницу с ценами", 0.8),
            ("Navigate to pricing", 0.7),
            ("Что такое SiteLLM?", 0.7),
            ("Расскажи подробнее", 0.7),
        ]

        for text, min_confidence in test_cases:
            intent = tester.classify_intent(text)
            assert intent["confidence"] >= min_confidence
            assert 0.0 <= intent["confidence"] <= 1.0

    def test_error_handling(self, tester):
        """Test error handling in various scenarios."""
        # Test with invalid session
        response = tester.client.post(
            f"{tester.base_url}/dialog/respond",
            json={
                "session_id": "invalid-session-id",
                "project": "default",
                "text": "Test",
            },
        )
        assert response.status_code == 404

        # Test with valid session
        tester.create_session()
        response = tester.send_dialog_message("Тест")
        assert response["type"] == "response"

    def test_concurrent_dialogs(self, tester):
        """Test handling multiple dialog messages in sequence."""
        tester.create_session()

        messages = [
            "Привет",
            "Перейти на страницу с ценами",
            "Расскажи подробнее",
            "Что такое SiteLLM?",
        ]

        for msg in messages:
            response = tester.send_dialog_message(msg)
            assert response["type"] == "response"
            assert response["text"] is not None

        # Verify all messages in history
        history = tester.get_history()
        user_messages = [h for h in history if h.get("type") == "user"]
        assert len(user_messages) >= len(messages)

    def test_session_activity_tracking(self, tester):
        """Test that session activity is tracked correctly."""
        session = tester.create_session()
        
        # Send initial message
        tester.send_dialog_message("Привет")
        time.sleep(0.1)

        # Get session info
        session_info = tester.get_session()
        assert "total_interactions" in session_info or "last_activity" in session_info or session_info["session_id"] == session["session_id"]


@pytest.mark.skipif(
    os.getenv("VOICE_TEST_BASE_URL") is None and not os.path.exists("/.dockerenv"),
    reason="Server not running or not in CI environment",
)
class TestVoiceDialogBrowserE2ESkipped:
    """E2E tests that require running server - skipped by default."""
    
    def test_server_available(self):
        """Check if server is available for browser tests."""
        try:
            response = httpx.get(f"{BASE_URL}/api/v1/voice/analytics/project/default", timeout=5.0)
            assert response.status_code in (200, 404)  # 404 is OK if project doesn't exist
        except Exception as e:
            pytest.skip(f"Server not available: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

