"""
Configuration management for Chronicle backend.

Uses OmegaConf for unified YAML configuration with environment variable interpolation.
Secrets are stored in .env files, all other config in config/config.yml.
"""

import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from omegaconf import OmegaConf

from advanced_omi_backend.config_loader import (
    get_backend_config,
    save_config_section,
    load_config,
    reload_config as reload_omegaconf_config,
)

logger = logging.getLogger(__name__)

# Data directory paths
DATA_DIR = Path(os.getenv("DATA_DIR", "/app/data"))
CHUNK_DIR = Path("./audio_chunks")  # Mounted to ./data/audio_chunks by Docker


# ============================================================================
# Configuration Functions (OmegaConf-based)
# ============================================================================

def get_config(force_reload: bool = False) -> dict:
    """
    Get merged configuration using OmegaConf.

    Wrapper around load_config() from config_loader for backward compatibility.

    Args:
        force_reload: If True, reload from disk even if cached

    Returns:
        Merged configuration dictionary with all settings
    """
    cfg = load_config(force_reload=force_reload)
    return OmegaConf.to_container(cfg, resolve=True)


def reload_config():
    """Reload configuration from disk (invalidate cache)."""
    return reload_omegaconf_config()


# ============================================================================
# Diarization Settings (OmegaConf-based)
# ============================================================================

def get_diarization_settings() -> dict:
    """
    Get diarization settings using OmegaConf.

    Returns:
        Dict with diarization configuration (resolved from YAML + env vars)
    """
    cfg = get_backend_config('diarization')
    return OmegaConf.to_container(cfg, resolve=True)


def save_diarization_settings(settings: dict) -> bool:
    """
    Save diarization settings to config.yml using OmegaConf.

    Args:
        settings: Dict with diarization settings to save

    Returns:
        True if saved successfully, False otherwise
    """
    return save_config_section('backend.diarization', settings)


# ============================================================================
# Cleanup Settings (OmegaConf-based)
# ============================================================================

@dataclass
class CleanupSettings:
    """Cleanup configuration for soft-deleted conversations."""
    auto_cleanup_enabled: bool = False
    retention_days: int = 30


def get_cleanup_settings() -> dict:
    """
    Get cleanup settings using OmegaConf.

    Returns:
        Dict with auto_cleanup_enabled and retention_days
    """
    cfg = get_backend_config('cleanup')
    return OmegaConf.to_container(cfg, resolve=True)


def save_cleanup_settings(settings: CleanupSettings) -> bool:
    """
    Save cleanup settings to config.yml using OmegaConf.

    Args:
        settings: CleanupSettings dataclass instance

    Returns:
        True if saved successfully, False otherwise
    """
    from dataclasses import asdict
    return save_config_section('backend.cleanup', asdict(settings))


# ============================================================================
# Speech Detection Settings (OmegaConf-based)
# ============================================================================

def get_speech_detection_settings() -> dict:
    """
    Get speech detection settings using OmegaConf.

    Returns:
        Dict with min_words, min_confidence, min_duration
    """
    cfg = get_backend_config('speech_detection')
    return OmegaConf.to_container(cfg, resolve=True)


# ============================================================================
# Conversation Stop Settings (OmegaConf-based)
# ============================================================================

def get_conversation_stop_settings() -> dict:
    """
    Get conversation stop settings using OmegaConf.

    Returns:
        Dict with transcription_buffer_seconds, speech_inactivity_threshold
    """
    cfg = get_backend_config('conversation_stop')
    settings = OmegaConf.to_container(cfg, resolve=True)

    # Add min_word_confidence from speech_detection for backward compatibility
    speech_cfg = get_backend_config('speech_detection')
    settings['min_word_confidence'] = OmegaConf.to_container(speech_cfg, resolve=True).get('min_confidence', 0.7)

    return settings


# ============================================================================
# Audio Storage Settings (OmegaConf-based)
# ============================================================================

def get_audio_storage_settings() -> dict:
    """
    Get audio storage settings using OmegaConf.

    Returns:
        Dict with audio_base_path, audio_chunks_path
    """
    cfg = get_backend_config('audio_storage')
    return OmegaConf.to_container(cfg, resolve=True)