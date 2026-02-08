#!/usr/bin/env python3
"""
Parakeet audio stream worker.

Starts a consumer that reads from audio:stream:* and transcribes audio using Parakeet.
"""

import os

from advanced_omi_backend.services.transcription.parakeet_stream_consumer import ParakeetStreamConsumer
from advanced_omi_backend.workers.base_audio_worker import BaseStreamWorker


class ParakeetStreamWorker(BaseStreamWorker):
    """Parakeet audio stream worker implementation."""

    def __init__(self):
        super().__init__(service_name="Parakeet audio stream worker")

    def validate_config(self):
        """Check that config.yml has Parakeet configured."""
        # The registry provider will load configuration from config.yml
        service_url = os.getenv("PARAKEET_ASR_URL")
        if not service_url:
            self.logger.warning("PARAKEET_ASR_URL environment variable not set")
            self.logger.warning("Ensure config.yml has a default 'stt' model configured for Parakeet")
            self.logger.warning("Audio transcription will use alternative providers if configured in config.yml")

    def get_consumer(self, redis_client):
        """Create Parakeet consumer with balanced buffer size."""
        # Create consumer with balanced buffer size
        # 20 chunks = ~5 seconds of audio
        # Balance between transcription accuracy and latency
        # Consumer uses registry-driven provider from config.yml
        return ParakeetStreamConsumer(
            redis_client=redis_client,
            buffer_chunks=20  # 5 seconds - good context without excessive delay
        )


if __name__ == "__main__":
    ParakeetStreamWorker.start()

