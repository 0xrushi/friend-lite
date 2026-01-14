"""
Configuration management for Chronicle backend.

Currently contains diarization settings because they were used in multiple places 
causing circular imports. Other configurations can be moved here as needed.
"""

import json
import logging
import os
import shutil
import yaml
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Data directory paths
DATA_DIR = Path(os.getenv("DATA_DIR", "/app/data"))
CHUNK_DIR = Path("./audio_chunks")  # Mounted to ./data/audio_chunks by Docker

# Default diarization settings
DEFAULT_DIARIZATION_SETTINGS = {
    "diarization_source": "pyannote",
    "similarity_threshold": 0.15,
    "min_duration": 0.5,
    "collar": 2.0,
    "min_duration_off": 1.5,
    "min_speakers": 2,
    "max_speakers": 6
}

# Default speech detection settings
DEFAULT_SPEECH_DETECTION_SETTINGS = {
    "min_words": 10,              # Minimum words to create conversation (increased from 5)
    "min_confidence": 0.7,        # Word confidence threshold (increased from 0.5)
    "min_duration": 10.0,         # Minimum speech duration in seconds (increased from 2.0)
}

# Default conversation stop settings
DEFAULT_CONVERSATION_STOP_SETTINGS = {
    "transcription_buffer_seconds": 120,    # Periodic transcription interval (2 minutes)
    "speech_inactivity_threshold": 60,      # Speech gap threshold for closure (1 minute)
}

# Default audio storage settings
DEFAULT_AUDIO_STORAGE_SETTINGS = {
    "audio_base_path": "/app/data",  # Main audio directory (where volume is mounted)
    "audio_chunks_path": "/app/audio_chunks",  # Full path to audio chunks subfolder
}

# Global cache for diarization settings
_diarization_settings = None


def get_diarization_config_path():
    """Get the path to the diarization config file."""
    # Try different locations in order of preference
    # 1. Data directory (for persistence across container restarts)
    data_path = Path("/app/data/diarization_config.json")
    if data_path.parent.exists():
        return data_path

    # 2. App root directory
    app_path = Path("/app/diarization_config.json")
    if app_path.parent.exists():
        return app_path

    # 3. Local development path
    local_path = Path("diarization_config.json")
    return local_path


# ============================================================================
# Configuration Merging System (for defaults.yml + config.yml)
# ============================================================================

def get_config_dir() -> Path:
    """
    Get config directory path. Single source of truth for config location.
    Matches root config_manager.py logic.

    Returns:
        Path to config directory
    """
    config_dir = os.getenv("CONFIG_DIR", "/app/config")
    return Path(config_dir)


def get_config_yml_path() -> Path:
    """Get path to config.yml file."""
    return get_config_dir() / "config.yml"


def get_defaults_yml_path() -> Path:
    """Get path to defaults.yml file."""
    return get_config_dir() / "defaults.yml"


def get_defaults_config_path():
    """
    Get the path to the defaults config file.

    DEPRECATED: Use get_defaults_yml_path() instead.
    Kept for backward compatibility.
    """
    defaults_path = get_defaults_yml_path()
    return defaults_path if defaults_path.exists() else None


def merge_configs(defaults: dict, overrides: dict) -> dict:
    """
    Deep merge two configuration dictionaries.

    Override values take precedence over defaults.
    Lists are replaced (not merged).

    Args:
        defaults: Default configuration values
        overrides: User-provided overrides

    Returns:
        Merged configuration dictionary
    """
    result = defaults.copy()

    for key, value in overrides.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            # Recursively merge dictionaries
            result[key] = merge_configs(result[key], value)
        else:
            # Override (lists, scalars, new keys)
            result[key] = value

    return result


# Global cache for merged config
_config_cache: Optional[dict] = None


def get_config(force_reload: bool = False) -> dict:
    """
    Get merged configuration from defaults.yml + config.yml.

    Priority order: config.yml > environment variables > defaults.yml

    Args:
        force_reload: If True, reload from disk even if cached

    Returns:
        Merged configuration dictionary with all settings
    """
    global _config_cache

    if _config_cache is not None and not force_reload:
        return _config_cache

    # Load defaults
    defaults_path = get_defaults_yml_path()
    defaults = {}
    if defaults_path.exists():
        try:
            with open(defaults_path, 'r') as f:
                defaults = yaml.safe_load(f) or {}
            logger.info(f"Loaded defaults from {defaults_path}")
        except Exception as e:
            logger.warning(f"Could not load defaults from {defaults_path}: {e}")

    # Load user config
    config_path = get_config_yml_path()
    user_config = {}
    if config_path.exists():
        try:
            with open(config_path, 'r') as f:
                user_config = yaml.safe_load(f) or {}
            logger.info(f"Loaded config from {config_path}")
        except Exception as e:
            logger.error(f"Error loading config from {config_path}: {e}")

    # Merge configurations
    merged = merge_configs(defaults, user_config)

    # Resolve environment variables (lazy import to avoid circular dependency)
    try:
        from advanced_omi_backend.model_registry import _deep_resolve_env
        merged = _deep_resolve_env(merged)
    except ImportError:
        # If model_registry not available, skip env resolution
        # (will be resolved when model_registry loads the config)
        logger.warning("Could not import _deep_resolve_env, environment variables may not be resolved")

    # Cache result
    _config_cache = merged

    return merged


def reload_config():
    """Reload configuration from disk (invalidate cache)."""
    global _config_cache
    _config_cache = None
    return get_config(force_reload=True)


def load_diarization_settings_from_file():
    """Load diarization settings from file or create from template."""
    global _diarization_settings
    
    config_path = get_diarization_config_path()
    template_path = Path("/app/diarization_config.json.template")
    
    # If no template, try local development path
    if not template_path.exists():
        template_path = Path("diarization_config.json.template")
    
    # If config doesn't exist, try to copy from template
    if not config_path.exists():
        if template_path.exists():
            try:
                # Ensure parent directory exists
                config_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy(template_path, config_path)
                logger.info(f"Created diarization config from template at {config_path}")
            except Exception as e:
                logger.warning(f"Could not copy template to {config_path}: {e}")
    
    # Load from file if it exists
    if config_path.exists():
        try:
            with open(config_path, 'r') as f:
                _diarization_settings = json.load(f)
                logger.info(f"Loaded diarization settings from {config_path}")
                return _diarization_settings
        except Exception as e:
            logger.error(f"Error loading diarization settings from {config_path}: {e}")
    
    # Fall back to defaults
    _diarization_settings = DEFAULT_DIARIZATION_SETTINGS.copy()
    logger.info("Using default diarization settings")
    return _diarization_settings


def save_diarization_settings_to_file(settings):
    """Save diarization settings to file."""
    global _diarization_settings
    
    config_path = get_diarization_config_path()
    
    try:
        # Ensure parent directory exists
        config_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write settings to file
        with open(config_path, 'w') as f:
            json.dump(settings, f, indent=2)
        
        # Update cache
        _diarization_settings = settings
        
        logger.info(f"Saved diarization settings to {config_path}")
        return True
    except Exception as e:
        logger.error(f"Error saving diarization settings to {config_path}: {e}")
        return False


# ============================================================================
# Cleanup Settings (JSON file-based with in-memory caching)
# ============================================================================

@dataclass
class CleanupSettings:
    """Cleanup configuration for soft-deleted conversations."""
    auto_cleanup_enabled: bool = False
    retention_days: int = 30

# Global cache for cleanup settings
_cleanup_settings: Optional[CleanupSettings] = None


def get_cleanup_config_path() -> Path:
    """Get path to cleanup settings JSON file."""
    data_dir = Path(os.getenv("DATA_DIR", "/app/data"))
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir / "cleanup_config.json"


def load_cleanup_settings_from_file() -> CleanupSettings:
    """
    Load cleanup settings from JSON file or return defaults.

    Returns cached settings if available, otherwise loads from file.
    If file doesn't exist, returns default settings.
    """
    global _cleanup_settings

    # Return cached settings if available
    if _cleanup_settings is not None:
        return _cleanup_settings

    config_path = get_cleanup_config_path()

    # Try to load from file
    if config_path.exists():
        try:
            with open(config_path, "r") as f:
                data = json.load(f)
                _cleanup_settings = CleanupSettings(**data)
                logger.info(f"✅ Loaded cleanup settings: auto_cleanup={_cleanup_settings.auto_cleanup_enabled}, retention={_cleanup_settings.retention_days}d")
                return _cleanup_settings
        except Exception as e:
            logger.error(f"❌ Failed to load cleanup settings from {config_path}: {e}")

    # Return defaults if file doesn't exist or failed to load
    _cleanup_settings = CleanupSettings()
    logger.info("Using default cleanup settings (auto_cleanup_enabled=False, retention_days=30)")
    return _cleanup_settings


def save_cleanup_settings_to_file(settings: CleanupSettings) -> None:
    """
    Save cleanup settings to JSON file and update in-memory cache.

    Args:
        settings: CleanupSettings to persist

    Raises:
        Exception: If file write fails
    """
    global _cleanup_settings

    config_path = get_cleanup_config_path()

    try:
        # Save to JSON file
        with open(config_path, "w") as f:
            json.dump(asdict(settings), f, indent=2)

        # Update in-memory cache
        _cleanup_settings = settings

        logger.info(f"✅ Saved cleanup settings: auto_cleanup={settings.auto_cleanup_enabled}, retention={settings.retention_days}d")
    except Exception as e:
        logger.error(f"❌ Failed to save cleanup settings to {config_path}: {e}")
        raise


def get_cleanup_settings() -> dict:
    """
    Get current cleanup settings as dict (for API responses).

    Returns:
        Dict with auto_cleanup_enabled and retention_days
    """
    settings = load_cleanup_settings_from_file()
    return {
        "auto_cleanup_enabled": settings.auto_cleanup_enabled,
        "retention_days": settings.retention_days,
    }


def get_speech_detection_settings():
    """Get speech detection settings from environment or defaults."""

    return {
        "min_words": int(os.getenv("SPEECH_DETECTION_MIN_WORDS", DEFAULT_SPEECH_DETECTION_SETTINGS["min_words"])),
        "min_confidence": float(os.getenv("SPEECH_DETECTION_MIN_CONFIDENCE", DEFAULT_SPEECH_DETECTION_SETTINGS["min_confidence"])),
        "min_duration": float(os.getenv("SPEECH_DETECTION_MIN_DURATION", DEFAULT_SPEECH_DETECTION_SETTINGS["min_duration"])),
    }


def get_conversation_stop_settings():
    """Get conversation stop settings from environment or defaults."""

    return {
        "transcription_buffer_seconds": float(os.getenv("TRANSCRIPTION_BUFFER_SECONDS", DEFAULT_CONVERSATION_STOP_SETTINGS["transcription_buffer_seconds"])),
        "speech_inactivity_threshold": float(os.getenv("SPEECH_INACTIVITY_THRESHOLD_SECONDS", DEFAULT_CONVERSATION_STOP_SETTINGS["speech_inactivity_threshold"])),
        "min_word_confidence": float(os.getenv("SPEECH_DETECTION_MIN_CONFIDENCE", DEFAULT_SPEECH_DETECTION_SETTINGS["min_confidence"])),
    }


def get_audio_storage_settings():
    """Get audio storage settings from environment or defaults."""
    
    # Get base path and derive chunks path
    audio_base_path = os.getenv("AUDIO_BASE_PATH", DEFAULT_AUDIO_STORAGE_SETTINGS["audio_base_path"])
    audio_chunks_path = os.getenv("AUDIO_CHUNKS_PATH", f"{audio_base_path}/audio_chunks")
    
    return {
        "audio_base_path": audio_base_path,
        "audio_chunks_path": audio_chunks_path,
    }


# Initialize settings on module load
_diarization_settings = load_diarization_settings_from_file()