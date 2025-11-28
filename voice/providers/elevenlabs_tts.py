"""
ElevenLabs TTS provider.

High-quality neural voice synthesis using ElevenLabs API.
"""

from __future__ import annotations

import os
from typing import Optional
import structlog

from voice.synthesizer import BaseTTSProvider

logger = structlog.get_logger(__name__)

try:
    from elevenlabs import generate, Voice, VoiceSettings
    HAS_ELEVENLABS = True
except ImportError:
    HAS_ELEVENLABS = False


class ElevenLabsTTSProvider(BaseTTSProvider):
    """ElevenLabs TTS provider."""
    
    name = "elevenlabs"
    
    # Default pricing (as of 2024): $0.30 per 1000 characters
    COST_PER_1000_CHARS = 0.30
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize ElevenLabs provider.
        
        Parameters
        ----------
        api_key:
            ElevenLabs API key (default: from ELEVENLABS_API_KEY env var)
        """
        self.api_key = api_key or os.getenv("ELEVENLABS_API_KEY")
        if not self.api_key:
            logger.warning("elevenlabs_api_key_missing")
    
    async def setup(self) -> None:
        """Initialize ElevenLabs client."""
        if not HAS_ELEVENLABS:
            raise ImportError(
                "ElevenLabs is not installed. Install with: pip install elevenlabs"
            )
        
        if not self.api_key:
            raise ValueError("ElevenLabs API key is required (set ELEVENLABS_API_KEY)")
        
        # Set API key as environment variable for elevenlabs library
        os.environ["ELEVENLABS_API_KEY"] = self.api_key
        logger.info("elevenlabs_provider_initialized")
    
    async def synthesize(
        self,
        text: str,
        *,
        voice: str = "default",
        language: str = "ru-RU",
        emotion: Optional[str] = None,
        options: Optional[dict] = None,
    ) -> bytes:
        """Synthesize speech using ElevenLabs."""
        if not self.api_key:
            raise ValueError("ElevenLabs API key is not set")
        
        try:
            # Map voice name to ElevenLabs voice ID or name
            voice_id = options.get("voice_id") if options else None
            if not voice_id:
                # Use voice name directly (ElevenLabs supports voice names)
                voice_id = voice
            
            # Voice settings
            voice_settings = VoiceSettings(
                stability=options.get("stability", 0.5) if options else 0.5,
                similarity_boost=options.get("similarity_boost", 0.75) if options else 0.75,
            )
            
            # Generate audio
            audio_bytes = generate(
                text=text,
                voice=Voice(voice_id=voice_id, settings=voice_settings),
                model=options.get("model", "eleven_multilingual_v2") if options else "eleven_multilingual_v2",
            )
            
            logger.info("elevenlabs_synthesis_complete", text_length=len(text))
            return audio_bytes
            
        except Exception as exc:  # noqa: BLE001
            logger.error("elevenlabs_synthesis_failed", error=str(exc))
            raise
    
    def estimate_cost(self, text: str) -> float:
        """Estimate cost for ElevenLabs synthesis."""
        return round(len(text) / 1000 * self.COST_PER_1000_CHARS, 4)
    
    def estimate_duration(self, text: str) -> float:
        """Estimate audio duration (ElevenLabs ~150 words/min)."""
        words = len(text.split())
        return max(0.5, words / 150 * 60)





