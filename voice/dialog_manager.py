"""
Dialog management scaffolding for the voice assistant.

Provides placeholder classes for intent recognition, context storage, and
response generation.  These abstractions enable the rest of the stack to import
dialog primitives even before full logic lands.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class DialogTurn:
    """Represents a single turn in the conversation."""

    role: str  # "user" or "assistant"
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DialogContext:
    """Conversation history container."""

    turns: List[DialogTurn] = field(default_factory=list)

    def add_user_message(self, text: str, **metadata: Any) -> None:
        self.turns.append(DialogTurn(role="user", content=text, metadata=metadata))

    def add_assistant_message(self, text: str, **metadata: Any) -> None:
        self.turns.append(DialogTurn(role="assistant", content=text, metadata=metadata))


class IntentClassifier:
    """Stub intent classifier."""

    async def classify(self, text: str, context: DialogContext) -> Dict[str, Any]:
        lowered = text.lower()
        if any(keyword in lowered for keyword in ("navigate", "перейти", "открой")):
            return {
                "intent": "navigate",
                "confidence": 0.9,
                "entities": {"target": "pricing"},
                "suggested_action": {"type": "navigate", "url": "/pricing"},
            }
        return {
            "intent": "knowledge_query",
            "confidence": 0.8,
            "entities": {},
            "suggested_action": None,
        }


class ResponseGenerator:
    """Stub response generator with retrieval/LLM integration."""

    async def generate(self, intent: Dict[str, Any], context: DialogContext) -> Dict[str, Any]:
        if intent["intent"] == "navigate":
            return {
                "text": "Открываю нужный раздел и отправляю ссылку.",
                "sources": [],
                "actions": [intent["suggested_action"]],
            }
        return {
            "text": "Вот краткий ответ по вашему вопросу. Подробнее будет доступно в следующих версиях.",
            "sources": [{"title": "demo-source", "url": "/docs"}],
            "actions": [],
        }


class DialogManager:
    """High-level orchestrator stub."""

    def __init__(self) -> None:
        self.context = DialogContext()
        self.intent_classifier = IntentClassifier()
        self.response_generator = ResponseGenerator()

    async def handle_user_message(self, text: str) -> Dict[str, Any]:
        intent = await self.intent_classifier.classify(text, self.context)
        response = await self.response_generator.generate(intent, self.context)
        self.context.add_user_message(text, intent=intent["intent"])
        self.context.add_assistant_message(response.get("text", ""), intent=intent["intent"])
        return {"intent": intent, "response": response}

