"""
Azure Cognitive Services TTS provider.

Microsoft Azure Text-to-Speech service.
"""

from __future__ import annotations

import os
from typing import Optional
import structlog

from voice.synthesizer import BaseTTSProvider

logger = structlog.get_logger(__name__)

try:
    import azure.cognitiveservices.speech as speechsdk
    HAS_AZURE = True
except ImportError:
    HAS_AZURE = False


class AzureTTSPvider(BaseTTSProvider):
    """Azure Cognitive Services TTS provider.
    
    Note: Class name intentionally kept as AzureTTSPvider for backward compatibility.
    """
    
    name = "azure"
    
    # Default pricing (as of 2024): $0.016 per 1000 characters for standard voices
    COST_PER_1000_CHARS = 0.016
    
    def __init__(
        self,
        subscription_key: Optional[str] = None,
        region: Optional[str] = None,
    ):
        """Initialize Azure TTS provider.
        
        Parameters
        ----------
        subscription_key:
            Azure Speech subscription key (default: from AZURE_SPEECH_KEY env var)
        region:
            Azure region (default: from AZURE_SPEECH_REGION env var or 'eastus')
        """
        self.subscription_key = subscription_key or os.getenv("AZURE_SPEECH_KEY")
        self.region = region or os.getenv("AZURE_SPEECH_REGION", "eastus")
    
    async def setup(self) -> None:
        """Initialize Azure Speech client."""
        if not HAS_AZURE:
            raise ImportError(
                "Azure Cognitive Services Speech SDK is not installed. "
                "Install with: pip install azure-cognitiveservices-speech"
            )
        
        if not self.subscription_key:
            raise ValueError(
                "Azure Speech subscription key is required (set AZURE_SPEECH_KEY)"
            )
        
        logger.info("azure_tts_provider_initialized", region=self.region)
    
    async def synthesize(
        self,
        text: str,
        *,
        voice: str = "default",
        language: str = "ru-RU",
        emotion: Optional[str] = None,
        options: Optional[dict] = None,
    ) -> bytes:
        """Synthesize speech using Azure TTS."""
        if not self.subscription_key:
            raise ValueError("Azure Speech subscription key is not set")
        
        try:
            # Configure speech synthesizer
            speech_config = speechsdk.SpeechConfig(
                subscription=self.subscription_key,
                region=self.region,
            )
            
            # Map language to Azure voice name
            # Azure uses format: "language-Script-Region-VoiceName"
            voice_name = options.get("voice_name") if options else None
            if not voice_name:
                # Default voices for common languages
                voice_map = {
                    "ru-RU": "ru-RU-SvetlanaNeural",
                    "en-US": "en-US-AriaNeural",
                    "en-GB": "en-GB-SoniaNeural",
                }
                voice_name = voice_map.get(language, "ru-RU-SvetlanaNeural")
            
            speech_config.speech_synthesis_voice_name = voice_name
            
            # SSML for emotion/prosody control
            ssml_text = text
            if emotion:
                # Map emotion to SSML prosody
                emotion_map = {
                    "happy": {"rate": "1.1", "pitch": "+5%"},
                    "sad": {"rate": "0.9", "pitch": "-5%"},
                    "angry": {"rate": "1.15", "pitch": "+10%"},
                    "calm": {"rate": "1.0", "pitch": "0%"},
                }
                prosody = emotion_map.get(emotion.lower(), {})
                if prosody:
                    ssml_text = (
                        f'<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" '
                        f'xml:lang="{language}">'
                        f'<voice name="{voice_name}">'
                        f'<prosody rate="{prosody.get("rate", "1.0")}" '
                        f'pitch="{prosody.get("pitch", "0%")}">'
                        f"{text}</prosody></voice></speak>"
                    )
            
            # Create synthesizer
            synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config)
            
            # Synthesize
            if ssml_text != text:
                # Use SSML
                result = synthesizer.speak_ssml_async(ssml_text).get()
            else:
                # Use plain text
                result = synthesizer.speak_text_async(text).get()
            
            # Check result
            if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
                audio_bytes = result.audio_data
                logger.info("azure_tts_synthesis_complete", text_length=len(text))
                return audio_bytes
            elif result.reason == speechsdk.ResultReason.Canceled:
                cancellation = speechsdk.CancellationDetails(result)
                error_msg = f"Azure TTS canceled: {cancellation.reason}"
                if cancellation.reason == speechsdk.CancellationReason.Error:
                    error_msg += f" - {cancellation.error_details}"
                raise RuntimeError(error_msg)
            else:
                raise RuntimeError(f"Azure TTS synthesis failed: {result.reason}")
                
        except Exception as exc:  # noqa: BLE001
            logger.error("azure_tts_synthesis_failed", error=str(exc))
            raise
    
    def estimate_cost(self, text: str) -> float:
        """Estimate cost for Azure TTS synthesis."""
        return round(len(text) / 1000 * self.COST_PER_1000_CHARS, 4)
    
    def estimate_duration(self, text: str) -> float:
        """Estimate audio duration (Azure ~150 words/min)."""
        words = len(text.split())
        return max(0.5, words / 150 * 60)

