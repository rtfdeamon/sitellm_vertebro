"""
Vosk-based speech recognition provider.

Uses Vosk for lightweight, offline speech recognition.
"""

from __future__ import annotations

import os
import json
import io
from typing import Optional
import asyncio
import structlog

from voice.recognizer import BaseRecognizer
from models import RecognitionResult

logger = structlog.get_logger(__name__)

try:
    from vosk import Model, KaldiRecognizer, SetLogLevel
    SetLogLevel(-1)  # Disable Vosk logging
    HAS_VOSK = True
except ImportError:
    HAS_VOSK = False


class VoskRecognizer(BaseRecognizer):
    """Vosk-based speech recognition provider."""
    
    name = "vosk"
    
    def __init__(self, model_path: Optional[str] = None, sample_rate: int = 16000):
        """Initialize Vosk recognizer.
        
        Parameters
        ----------
        model_path:
            Path to Vosk model directory (default: auto-detect or download)
        sample_rate:
            Audio sample rate in Hz (default: 16000)
        """
        self.model_path = model_path
        self.sample_rate = sample_rate
        self.model = None
        self.recognizer = None
        self._lock = asyncio.Lock()
    
    async def setup(self) -> None:
        """Load Vosk model."""
        async with self._lock:
            if self.model is not None:
                return
            
            if not HAS_VOSK:
                raise ImportError(
                    "Vosk is not installed. Install with: pip install vosk"
                )
            
            logger.info("loading_vosk_model", path=self.model_path)
            
            try:
                # Use provided model path or try to find default
                if self.model_path and os.path.exists(self.model_path):
                    model_path = self.model_path
                else:
                    # Try common model paths
                    possible_paths = [
                        os.path.expanduser("~/vosk-model"),
                        "/usr/share/vosk-model",
                        "./models/vosk",
                    ]
                    model_path = None
                    for path in possible_paths:
                        if os.path.exists(path):
                            model_path = path
                            break
                    
                    if not model_path:
                        raise FileNotFoundError(
                            "Vosk model not found. Please download a model from "
                            "https://alphacephei.com/vosk/models and specify the path."
                        )
                
                # Load Vosk model (blocking operation, run in thread pool)
                loop = asyncio.get_event_loop()
                self.model = await loop.run_in_executor(None, Model, model_path)
                
                # Create recognizer
                self.recognizer = KaldiRecognizer(self.model, self.sample_rate)
                self.recognizer.SetWords(True)  # Enable word-level results
                
                logger.info("vosk_model_loaded", path=model_path)
                
            except Exception as exc:  # noqa: BLE001
                logger.error("vosk_model_load_failed", error=str(exc))
                raise
    
    async def recognize(
        self,
        audio_bytes: bytes,
        language: Optional[str] = None,
    ) -> RecognitionResult:
        """Recognize speech from audio bytes using Vosk."""
        import time
        import wave
        start = time.perf_counter()
        
        if self.model is None:
            await self.setup()
        
        try:
            # Vosk expects PCM audio in a specific format
            # Try to parse as WAV if it looks like WAV, otherwise assume raw PCM
            audio_io = io.BytesIO(audio_bytes)
            
            # Check if it's a WAV file
            if audio_bytes[:4] == b"RIFF":
                # It's a WAV file, try to read it
                try:
                    with wave.open(audio_io, "rb") as wf:
                        # Verify sample rate matches
                        if wf.getframerate() != self.sample_rate:
                            logger.warning(
                                "vosk_sample_rate_mismatch",
                                expected=self.sample_rate,
                                actual=wf.getframerate(),
                            )
                        # Read audio data
                        audio_data = wf.readframes(wf.getnframes())
                except Exception as exc:  # noqa: BLE001
                    logger.warning("vosk_wav_parse_failed", error=str(exc))
                    # Fallback to raw bytes
                    audio_data = audio_bytes
            else:
                # Assume raw PCM
                audio_data = audio_bytes
            
            # Run recognition in thread pool (Vosk is CPU bound)
            loop = asyncio.get_event_loop()
            
            def _recognize() -> dict:
                recognizer = KaldiRecognizer(self.model, self.sample_rate)
                recognizer.SetWords(True)
                
                # Process audio in chunks
                chunk_size = 4000  # Process 4000 bytes at a time
                results = []
                
                for i in range(0, len(audio_data), chunk_size):
                    chunk = audio_data[i:i + chunk_size]
                    if recognizer.AcceptWaveform(chunk):
                        result = json.loads(recognizer.Result())
                        if result.get("text"):
                            results.append(result)
                
                # Get final result
                final_result = json.loads(recognizer.FinalResult())
                if final_result.get("text"):
                    results.append(final_result)
                
                # Combine all results
                if results:
                    # Merge all text segments
                    text = " ".join(r.get("text", "") for r in results if r.get("text"))
                    # Calculate average confidence
                    words = []
                    for r in results:
                        words.extend(r.get("result", []))
                    if words:
                        confidences = [w.get("conf", 0.5) for w in words]
                        confidence = sum(confidences) / len(confidences) if confidences else 0.5
                    else:
                        confidence = 0.75
                    return {"text": text.strip(), "confidence": confidence}
                else:
                    return {"text": "", "confidence": 0.0}
            
            result = await loop.run_in_executor(None, _recognize)
            
            elapsed = (time.perf_counter() - start) * 1000
            
            return RecognitionResult(
                text=result["text"],
                confidence=result["confidence"],
                language=language or "ru-RU",  # Vosk doesn't auto-detect language
                processing_time_ms=elapsed,
                alternatives=None,
            )
            
        except Exception as exc:  # noqa: BLE001
            logger.error("vosk_recognition_failed", error=str(exc))
            raise
    
    async def start_stream(self) -> None:
        """Initialize streaming recognition."""
        if self.model is None:
            await self.setup()
        
        # Create a new recognizer for streaming
        loop = asyncio.get_event_loop()
        self.recognizer = await loop.run_in_executor(
            None,
            lambda: KaldiRecognizer(self.model, self.sample_rate),
        )
        self.recognizer.SetWords(True)
        logger.debug("vosk_stream_started")
    
    async def process_stream_chunk(self, chunk: bytes) -> Optional[RecognitionResult]:
        """Process a streaming chunk."""
        if self.recognizer is None:
            await self.start_stream()
        
        try:
            # Run recognition in thread pool
            loop = asyncio.get_event_loop()
            
            def _process_chunk() -> Optional[dict]:
                if self.recognizer.AcceptWaveform(chunk):
                    result = json.loads(self.recognizer.Result())
                    if result.get("text"):
                        words = result.get("result", [])
                        confidence = (
                            sum(w.get("conf", 0.5) for w in words) / len(words)
                            if words
                            else 0.5
                        )
                        return {
                            "text": result["text"],
                            "confidence": confidence,
                            "is_final": True,
                        }
                return None
            
            result = await loop.run_in_executor(None, _process_chunk)
            
            if result:
                return RecognitionResult(
                    text=result["text"],
                    confidence=result["confidence"],
                    is_final=result["is_final"],
                    language="ru-RU",
                    processing_time_ms=0.0,
                )
            return None
            
        except Exception as exc:  # noqa: BLE001
            logger.error("vosk_stream_chunk_failed", error=str(exc))
            return None
    
    async def finish_stream(self) -> Optional[RecognitionResult]:
        """Finalize streaming recognition."""
        if self.recognizer is None:
            return None
        
        try:
            # Get final result
            loop = asyncio.get_event_loop()
            
            def _finalize() -> Optional[dict]:
                result = json.loads(self.recognizer.FinalResult())
                if result.get("text"):
                    words = result.get("result", [])
                    confidence = (
                        sum(w.get("conf", 0.5) for w in words) / len(words)
                        if words
                        else 0.5
                    )
                    return {
                        "text": result["text"],
                        "confidence": confidence,
                        "is_final": True,
                    }
                return None
            
            result = await loop.run_in_executor(None, _finalize)
            
            if result:
                return RecognitionResult(
                    text=result["text"],
                    confidence=result["confidence"],
                    is_final=True,
                    language="ru-RU",
                    processing_time_ms=0.0,
                )
            return None
            
        except Exception as exc:  # noqa: BLE001
            logger.error("vosk_stream_finalize_failed", error=str(exc))
            return None
        finally:
            self.recognizer = None





