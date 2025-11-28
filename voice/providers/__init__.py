"""
Voice provider implementations.

Provides production-ready STT and TTS providers.
"""

# Import recognizers
try:
    from voice.providers.whisper_recognizer import WhisperRecognizer
except ImportError:
    WhisperRecognizer = None  # type: ignore

try:
    from voice.providers.vosk_recognizer import VoskRecognizer
except ImportError:
    VoskRecognizer = None  # type: ignore

# Import TTS providers
try:
    from voice.providers.elevenlabs_tts import ElevenLabsTTSProvider
except ImportError:
    ElevenLabsTTSProvider = None  # type: ignore

try:
    from voice.providers.azure_tts import AzureTTSPvider
except ImportError:
    AzureTTSPvider = None  # type: ignore

__all__ = [
    "WhisperRecognizer",
    "VoskRecognizer",
    "ElevenLabsTTSProvider",
    "AzureTTSPvider",
]
