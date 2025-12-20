"""
Transcription provider implementations and factory.

This module contains concrete implementations of transcription providers
for different ASR services (Deepgram, Parakeet, etc.) and a factory function
to instantiate the appropriate provider based on configuration.
"""

import logging
import os
from typing import Optional

from advanced_omi_backend.services.memory.config import load_config_yml as _load_root_config
from advanced_omi_backend.services.memory.config import resolve_value as _resolve_value

from .base import BaseTranscriptionProvider
from advanced_omi_backend.services.transcription.deepgram import (
    DeepgramProvider,
    DeepgramStreamingProvider,
    DeepgramStreamConsumer,
)
from advanced_omi_backend.services.transcription.parakeet import (
    ParakeetProvider,
    ParakeetStreamingProvider,
)

logger = logging.getLogger(__name__)


def get_transcription_provider(
    provider_name: Optional[str] = None,
    mode: Optional[str] = None,
) -> Optional[BaseTranscriptionProvider]:
    """
    Factory function to get the appropriate transcription provider.

    Args:
        provider_name: Name of the provider ('deepgram', 'parakeet').
                      If None, will auto-select based on available configuration.
        mode: Processing mode ('streaming', 'batch'). If None, defaults to 'batch'.

    Returns:
        An instance of BaseTranscriptionProvider, or None if no provider is configured.

    Raises:
        RuntimeError: If a specific provider is requested but not properly configured.
    """
    # Prefer config.yml driven selection; no direct env access
    if mode is None:
        mode = "batch"
    mode = mode.lower()

    try:
        cfg = _load_root_config() or {}
        defaults = cfg.get("defaults", {}) or {}
        models = cfg.get("models", []) or []
        stt_name = defaults.get("stt")
        if stt_name:
            stt_def = next((m for m in models if m.get("name") == stt_name), None)
            if stt_def:
                provider = (stt_def.get("model_provider") or "").lower()
                api_family = (stt_def.get("api_family") or "http").lower()
                if provider == "deepgram":
                    api_key = str(_resolve_value(stt_def.get("api_key", "")))
                    if not api_key:
                        logger.warning("Deepgram selected in config.yml but api_key missing or empty")
                        return None
                    return DeepgramStreamingProvider(api_key) if mode == "streaming" else DeepgramProvider(api_key)
                elif provider == "parakeet":
                    service_url = str(_resolve_value(stt_def.get("model_url", "")))
                    if not service_url:
                        logger.warning("Parakeet selected in config.yml but model_url missing or empty")
                        return None
                    return ParakeetStreamingProvider(service_url) if mode == "streaming" else ParakeetProvider(service_url)
                else:
                    logger.warning(f"Unsupported STT provider in config.yml: {provider}")
                    return None
    except Exception as e:
        logger.warning(f"Failed to load STT provider from config.yml: {e}")
        raise

    # If no config present, no provider configured
    logger.warning("No STT default configured in config.yml (defaults.stt)")
    return None


__all__ = [
    "get_transcription_provider",
    "DeepgramProvider",
    "DeepgramStreamingProvider",
    "DeepgramStreamConsumer",
    "ParakeetProvider",
    "ParakeetStreamingProvider",
]
