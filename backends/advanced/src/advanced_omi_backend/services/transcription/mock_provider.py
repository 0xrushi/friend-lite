"""
Mock transcription provider for testing without external API dependencies.

This provider returns predefined transcripts for testing purposes, allowing
tests to run without Deepgram or other external transcription APIs.
"""

from typing import Optional
from .base import BatchTranscriptionProvider


class MockTranscriptionProvider(BatchTranscriptionProvider):
    """
    Mock transcription provider for testing.

    Returns predefined transcripts with word-level timestamps.
    Useful for testing API contracts and data flow without external APIs.
    """

    def __init__(self):
        """Initialize the mock transcription provider."""
        self._is_connected = False

    @property
    def name(self) -> str:
        """Return the provider name for logging."""
        return "mock"

    async def transcribe(self, audio_data: bytes, sample_rate: int, diarize: bool = False) -> dict:
        """
        Return a predefined mock transcript.

        Args:
            audio_data: Raw audio bytes (ignored in mock)
            sample_rate: Audio sample rate (ignored in mock)
            diarize: Whether to enable speaker diarization (ignored in mock)

        Returns:
            Dictionary containing predefined transcript with words and segments
        """
        # Calculate audio duration from bytes (assuming 16-bit PCM)
        audio_duration = len(audio_data) / (sample_rate * 2)  # 2 bytes per sample

        # Return a mock transcript with word-level timestamps
        # This simulates a real transcription result
        mock_transcript = "This is a mock transcription for testing purposes."

        # Generate mock words with timestamps
        words = [
            {"word": "This", "start": 0.0, "end": 0.3, "confidence": 0.99, "speaker": 0},
            {"word": "is", "start": 0.3, "end": 0.5, "confidence": 0.99, "speaker": 0},
            {"word": "a", "start": 0.5, "end": 0.6, "confidence": 0.99, "speaker": 0},
            {"word": "mock", "start": 0.6, "end": 0.9, "confidence": 0.99, "speaker": 0},
            {"word": "transcription", "start": 0.9, "end": 1.5, "confidence": 0.98, "speaker": 0},
            {"word": "for", "start": 1.5, "end": 1.7, "confidence": 0.99, "speaker": 0},
            {"word": "testing", "start": 1.7, "end": 2.1, "confidence": 0.99, "speaker": 0},
            {"word": "purposes", "start": 2.1, "end": 2.6, "confidence": 0.97, "speaker": 0},
        ]

        # Mock segments (single speaker for simplicity)
        segments = [
            {
                "speaker": 0,
                "start": 0.0,
                "end": 2.6,
                "text": mock_transcript
            }
        ]

        return {
            "text": mock_transcript,
            "words": words,
            "segments": segments if diarize else []
        }

    async def connect(self, client_id: Optional[str] = None):
        """Initialize the mock provider (no-op)."""
        self._is_connected = True

    async def disconnect(self):
        """Cleanup the mock provider (no-op)."""
        self._is_connected = False
