"""
Speech recognition scaffolding for the voice assistant.

Concrete recognizers (Whisper, Vosk, etc.) will plug into the public base class
defined here.  The scaffolding allows other modules to be type-checked while the
actual inference code is developed.
"""

from __future__ import annotations

from typing import Optional
import time

from models import RecognitionResult


class BaseRecognizer:
    """Common recognizer interface."""

    name: str = "base"

    async def setup(self) -> None:
        """Load heavy models/resources."""
        raise NotImplementedError

    async def recognize(
        self,
        audio_bytes: bytes,
        language: Optional[str] = None,
    ) -> RecognitionResult:
        """Perform synchronous recognition over the provided audio bytes."""
        raise NotImplementedError

    async def start_stream(self) -> None:
        """Initialize any streaming resources (WebRTC VAD, chunk queues, etc.)."""
        raise NotImplementedError

    async def process_stream_chunk(self, chunk: bytes) -> Optional[RecognitionResult]:
        """Process a single audio chunk and optionally return a result."""
        raise NotImplementedError

    async def finish_stream(self) -> Optional[RecognitionResult]:
        """Finalize the stream and flush remaining hypotheses."""
        raise NotImplementedError


class WhisperRecognizer(BaseRecognizer):
    """Placeholder for the Whisper-based recognizer."""

    name = "whisper"

    async def setup(self) -> None:
        raise NotImplementedError("Whisper recognizer setup pending implementation")

    async def recognize(
        self,
        audio_bytes: bytes,
        language: Optional[str] = None,
    ) -> RecognitionResult:
        raise NotImplementedError("Whisper recognition pending implementation")

    async def start_stream(self) -> None:
        raise NotImplementedError("Whisper streaming pending implementation")

    async def process_stream_chunk(self, chunk: bytes) -> Optional[RecognitionResult]:
        raise NotImplementedError("Whisper streaming pending implementation")

    async def finish_stream(self) -> Optional[RecognitionResult]:
        raise NotImplementedError("Whisper streaming pending implementation")


class VoskRecognizer(BaseRecognizer):
    """Placeholder for the lightweight Vosk recognizer."""

    name = "vosk"

    async def setup(self) -> None:
        raise NotImplementedError("Vosk recognizer setup pending implementation")

    async def recognize(
        self,
        audio_bytes: bytes,
        language: Optional[str] = None,
    ) -> RecognitionResult:
        raise NotImplementedError("Vosk recognition pending implementation")

    async def start_stream(self) -> None:
        raise NotImplementedError("Vosk streaming pending implementation")

    async def process_stream_chunk(self, chunk: bytes) -> Optional[RecognitionResult]:
        raise NotImplementedError("Vosk streaming pending implementation")

    async def finish_stream(self) -> Optional[RecognitionResult]:
        raise NotImplementedError("Vosk streaming pending implementation")


class SimpleRecognizer(BaseRecognizer):
    """Fallback recognizer used during early development/testing."""

    name = "simple"

    async def setup(self) -> None:
        return

    async def recognize(
        self,
        audio_bytes: bytes,
        language: Optional[str] = None,
        *,
        text_hint: Optional[str] = None,
    ) -> RecognitionResult:
        start = time.perf_counter()
        text = text_hint or f"{language or 'und'} audio ({len(audio_bytes)} bytes)"
        elapsed = (time.perf_counter() - start) * 1000
        return RecognitionResult(
            text=text,
            confidence=0.75,
            language=language or "und",
            processing_time_ms=elapsed,
            alternatives=None,
        )

    async def start_stream(self) -> None:
        return

    async def process_stream_chunk(self, chunk: bytes) -> Optional[RecognitionResult]:
        if chunk:
            return RecognitionResult(
                text=f"chunk-{len(chunk)}",
                confidence=0.5,
                is_final=False,
                language="und",
                processing_time_ms=0.0,
            )
        return None

    async def finish_stream(self) -> Optional[RecognitionResult]:
        return RecognitionResult(
            text="stream-finished",
            confidence=0.5,
            is_final=True,
            language="und",
            processing_time_ms=0.0,
        )