#!/usr/bin/env python3
"""
Deepgram audio stream worker.

Starts a consumer that reads from audio:stream:deepgram and transcribes audio.
"""

import os

from advanced_omi_backend.services.transcription.deepgram import DeepgramStreamConsumer
from advanced_omi_backend.workers.base_audio_worker import BaseStreamWorker


class DeepgramStreamWorker(BaseStreamWorker):
    """Deepgram audio stream worker implementation."""

    def __init__(self):
        super().__init__(service_name="Deepgram audio stream worker")

    def validate_config(self):
        """Check that config.yml has Deepgram configured."""
        # The registry provider will load configuration from config.yml
        api_key = os.getenv("DEEPGRAM_API_KEY")
        if not api_key:
            self.logger.warning("DEEPGRAM_API_KEY environment variable not set")
            self.logger.warning("Ensure config.yml has a default 'stt' model configured for Deepgram")
            self.logger.warning("Audio transcription will use alternative providers if configured in config.yml")

    def get_consumer(self, redis_client):
        """Create Deepgram consumer with balanced buffer size."""
        # Create consumer with balanced buffer size
        # 20 chunks = ~5 seconds of audio
        # Balance between transcription accuracy and latency
        # Consumer uses registry-driven provider from config.yml
        return DeepgramStreamConsumer(
            redis_client=redis_client,
            buffer_chunks=20  # 5 seconds - good context without excessive delay
        )


if __name__ == "__main__":
    DeepgramStreamWorker.start()
