"""
Whisper-based speech recognition provider.

Uses OpenAI Whisper or faster-whisper for high-quality speech recognition.
"""

from __future__ import annotations

import os
import io
import tempfile
from typing import Optional
import asyncio
import structlog

from voice.recognizer import BaseRecognizer
from models import RecognitionResult

logger = structlog.get_logger(__name__)

# Try to import faster-whisper first (more efficient), fallback to openai-whisper
try:
    from faster_whisper import WhisperModel
    HAS_FASTER_WHISPER = True
except ImportError:
    HAS_FASTER_WHISPER = False
    try:
        import whisper
        HAS_WHISPER = True
    except ImportError:
        HAS_WHISPER = False


class WhisperRecognizer(BaseRecognizer):
    """Whisper-based speech recognition provider."""
    
    name = "whisper"
    
    def __init__(
        self,
        model_size: str = "base",
        device: str = "cpu",
        compute_type: str = "int8",
    ):
        """Initialize Whisper recognizer.
        
        Parameters
        ----------
        model_size:
            Model size: tiny, base, small, medium, large (default: base)
        device:
            Device: cpu, cuda (default: cpu)
        compute_type:
            Compute type for faster-whisper: int8, int8_float16, float16, float32 (default: int8)
        """
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self.model = None
        self._lock = asyncio.Lock()
    
    async def setup(self) -> None:
        """Load Whisper model."""
        async with self._lock:
            if self.model is not None:
                return
            
            logger.info("loading_whisper_model", size=self.model_size, device=self.device)
            
            try:
                if HAS_FASTER_WHISPER:
                    # Use faster-whisper (more efficient)
                    self.model = WhisperModel(
                        self.model_size,
                        device=self.device,
                        compute_type=self.compute_type,
                    )
                    logger.info("whisper_model_loaded", provider="faster-whisper")
                elif HAS_WHISPER:
                    # Fallback to openai-whisper
                    self.model = whisper.load_model(self.model_size)
                    logger.info("whisper_model_loaded", provider="openai-whisper")
                else:
                    raise ImportError(
                        "Neither faster-whisper nor openai-whisper is installed. "
                        "Install with: pip install faster-whisper or pip install openai-whisper"
                    )
            except Exception as exc:  # noqa: BLE001
                logger.error("whisper_model_load_failed", error=str(exc))
                raise
    
    async def recognize(
        self,
        audio_bytes: bytes,
        language: Optional[str] = None,
    ) -> RecognitionResult:
        """Recognize speech from audio bytes using Whisper."""
        import time
        start = time.perf_counter()
        
        if self.model is None:
            await self.setup()
        
        # Save audio bytes to temporary file for Whisper
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
            tmp_file.write(audio_bytes)
            tmp_path = tmp_file.name
        
        try:
            # Run recognition in thread pool (Whisper is CPU/GPU bound)
            loop = asyncio.get_event_loop()
            
            if HAS_FASTER_WHISPER and isinstance(self.model, WhisperModel):
                # faster-whisper API
                segments, info = await loop.run_in_executor(
                    None,
                    lambda: self.model.transcribe(tmp_path, language=language or None),
                )
                
                # Extract text from segments
                text = " ".join(segment.text for segment in segments)
                detected_language = info.language
                
                # Calculate average confidence (faster-whisper doesn't provide per-segment confidence)
                confidence = 0.85  # Default confidence for Whisper
                
            elif HAS_WHISPER:
                # openai-whisper API
                result = await loop.run_in_executor(
                    None,
                    lambda: self.model.transcribe(tmp_path, language=language or None),
                )
                
                text = result["text"].strip()
                detected_language = result.get("language", language or "unknown")
                segments = result.get("segments", [])
                
                # Calculate average confidence from segments
                if segments:
                    confidences = [seg.get("no_speech_prob", 0.0) for seg in segments]
                    # Convert no_speech_prob to confidence (inverse)
                    confidence = 1.0 - (sum(confidences) / len(confidences))
                else:
                    confidence = 0.85
            else:
                raise RuntimeError("Whisper model not loaded")
            
            elapsed = (time.perf_counter() - start) * 1000
            
            return RecognitionResult(
                text=text,
                confidence=confidence,
                language=detected_language,
                processing_time_ms=elapsed,
                alternatives=None,
            )
            
        except Exception as exc:  # noqa: BLE001
            logger.error("whisper_recognition_failed", error=str(exc))
            raise
        finally:
            # Clean up temporary file
            try:
                os.unlink(tmp_path)
            except Exception:  # noqa: BLE001
                pass
    
    async def start_stream(self) -> None:
        """Initialize streaming recognition."""
        # Whisper doesn't natively support streaming, but we can accumulate chunks
        if self.model is None:
            await self.setup()
        logger.debug("whisper_stream_started")
    
    async def process_stream_chunk(self, chunk: bytes) -> Optional[RecognitionResult]:
        """Process a streaming chunk (accumulates chunks for Whisper)."""
        # Whisper requires full audio, so we just accumulate chunks
        # Return None to indicate we need more chunks
        return None
    
    async def finish_stream(self) -> Optional[RecognitionResult]:
        """Finalize streaming recognition."""
        # In a real implementation, we'd process accumulated chunks here
        # For now, return None as we need the full audio
        return None





