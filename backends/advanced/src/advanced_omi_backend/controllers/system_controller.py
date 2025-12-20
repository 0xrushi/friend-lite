"""
System controller for handling system-related business logic.
"""

import logging
import os
import shutil
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Tuple

from advanced_omi_backend.config import (
    load_diarization_settings_from_file,
    save_diarization_settings_to_file,
)
from advanced_omi_backend.models.user import User
from advanced_omi_backend.task_manager import get_task_manager
from fastapi.responses import JSONResponse
import yaml

from advanced_omi_backend.services.memory.config import load_config_yml as _load_root_config
from advanced_omi_backend.services.memory.service_factory import reset_memory_service, get_memory_service

logger = logging.getLogger(__name__)
audio_logger = logging.getLogger("audio_processing")


async def get_current_metrics():
    """Get current system metrics."""
    try:
        # Get memory provider configuration
        memory_provider = (await get_memory_provider())["current_provider"]

        # Get basic system metrics
        metrics = {
            "timestamp": int(time.time()),
            "memory_provider": memory_provider,
            "memory_provider_supports_threshold": memory_provider == "chronicle",
        }

        return metrics

    except Exception as e:
        audio_logger.error(f"Error fetching metrics: {e}")
        return JSONResponse(
            status_code=500, content={"error": f"Failed to fetch metrics: {str(e)}"}
        )


async def get_auth_config():
    """Get authentication configuration for frontend."""
    return {
        "auth_method": "email",
        "registration_enabled": False,  # Only admin can create users
        "features": {
            "email_login": True,
            "user_id_login": False,  # Deprecated
            "registration": False,
        },
    }


# Audio file processing functions moved to audio_controller.py


# Configuration functions moved to config.py to avoid circular imports


async def get_diarization_settings():
    """Get current diarization settings."""
    try:
        # Reload from file to get latest settings
        settings = load_diarization_settings_from_file()
        return {
            "settings": settings,
            "status": "success"
        }
    except Exception as e:
        logger.error(f"Error getting diarization settings: {e}")
        return JSONResponse(
            status_code=500, content={"error": f"Failed to get settings: {str(e)}"}
        )


async def save_diarization_settings(settings: dict):
    """Save diarization settings."""
    try:
        # Validate settings
        valid_keys = {
            "diarization_source", "similarity_threshold", "min_duration", "collar", 
            "min_duration_off", "min_speakers", "max_speakers"
        }
        
        for key, value in settings.items():
            if key not in valid_keys:
                return JSONResponse(
                    status_code=400, content={"error": f"Invalid setting key: {key}"}
                )
            
            # Type validation
            if key in ["min_speakers", "max_speakers"]:
                if not isinstance(value, int) or value < 1 or value > 20:
                    return JSONResponse(
                        status_code=400, content={"error": f"Invalid value for {key}: must be integer 1-20"}
                    )
            elif key == "diarization_source":
                if not isinstance(value, str) or value not in ["pyannote", "deepgram"]:
                    return JSONResponse(
                        status_code=400, content={"error": f"Invalid value for {key}: must be 'pyannote' or 'deepgram'"}
                    )
            else:
                if not isinstance(value, (int, float)) or value < 0:
                    return JSONResponse(
                        status_code=400, content={"error": f"Invalid value for {key}: must be positive number"}
                    )
        
        # Get current settings and merge with new values
        current_settings = load_diarization_settings_from_file()
        current_settings.update(settings)
        
        # Save to file
        if save_diarization_settings_to_file(current_settings):
            logger.info(f"Updated and saved diarization settings: {settings}")
            
            return {
                "message": "Diarization settings saved successfully",
                "settings": current_settings,
                "status": "success"
            }
        else:
            # Even if file save fails, we've updated the in-memory settings
            logger.warning("Settings updated in memory but file save failed")
            return {
                "message": "Settings updated (file save failed)",
                "settings": current_settings,
                "status": "partial"
            }
        
    except Exception as e:
        logger.error(f"Error saving diarization settings: {e}")
        return JSONResponse(
            status_code=500, content={"error": f"Failed to save settings: {str(e)}"}
        )


async def get_speaker_configuration(user: User):
    """Get current user's primary speakers configuration."""
    try:
        return {
            "primary_speakers": user.primary_speakers,
            "user_id": user.user_id,
            "status": "success"
        }
    except Exception as e:
        logger.error(f"Error getting speaker configuration for user {user.user_id}: {e}")
        return JSONResponse(
            status_code=500, content={"error": f"Failed to get speaker configuration: {str(e)}"}
        )


async def update_speaker_configuration(user: User, primary_speakers: list[dict]):
    """Update current user's primary speakers configuration."""
    try:
        # Validate speaker data format
        for speaker in primary_speakers:
            if not isinstance(speaker, dict):
                return JSONResponse(
                    status_code=400, content={"error": "Each speaker must be a dictionary"}
                )
            
            required_fields = ["speaker_id", "name", "user_id"]
            for field in required_fields:
                if field not in speaker:
                    return JSONResponse(
                        status_code=400, content={"error": f"Missing required field: {field}"}
                    )
        
        # Enforce server-side user_id and add timestamp to each speaker
        for speaker in primary_speakers:
            speaker["user_id"] = user.user_id  # Override client-supplied user_id
            speaker["selected_at"] = datetime.now(UTC).isoformat()
        
        # Update user model
        user.primary_speakers = primary_speakers
        await user.save()
        
        logger.info(f"Updated primary speakers configuration for user {user.user_id}: {len(primary_speakers)} speakers")
        
        return {
            "message": "Primary speakers configuration updated successfully",
            "primary_speakers": primary_speakers,
            "count": len(primary_speakers),
            "status": "success"
        }
        
    except Exception as e:
        logger.error(f"Error updating speaker configuration for user {user.user_id}: {e}")
        return JSONResponse(
            status_code=500, content={"error": f"Failed to update speaker configuration: {str(e)}"}
        )


async def get_enrolled_speakers(user: User):
    """Get enrolled speakers from speaker recognition service."""
    try:
        from advanced_omi_backend.speaker_recognition_client import (
            SpeakerRecognitionClient,
        )

        # Initialize speaker recognition client
        speaker_client = SpeakerRecognitionClient()
        
        if not speaker_client.enabled:
            return {
                "speakers": [],
                "service_available": False,
                "message": "Speaker recognition service is not configured or disabled",
                "status": "success"
            }
        
        # Get enrolled speakers - using hardcoded user_id=1 for now (as noted in speaker_recognition_client.py)
        speakers = await speaker_client.get_enrolled_speakers(user_id="1")
        
        return {
            "speakers": speakers.get("speakers", []) if speakers else [],
            "service_available": True,
            "message": "Successfully retrieved enrolled speakers",
            "status": "success"
        }
        
    except Exception as e:
        logger.error(f"Error getting enrolled speakers for user {user.user_id}: {e}")
        return {
            "speakers": [],
            "service_available": False,
            "message": f"Failed to retrieve speakers: {str(e)}",
            "status": "error"
        }


async def get_speaker_service_status():
    """Check speaker recognition service health status."""
    try:
        from advanced_omi_backend.speaker_recognition_client import (
            SpeakerRecognitionClient,
        )

        # Initialize speaker recognition client
        speaker_client = SpeakerRecognitionClient()
        
        if not speaker_client.enabled:
            return {
                "service_available": False,
                "healthy": False,
                "message": "Speaker recognition service is not configured or disabled",
                "status": "disabled"
            }
        
        # Perform health check
        health_result = await speaker_client.health_check()
        
        if health_result:
            return {
                "service_available": True,
                "healthy": True,
                "message": "Speaker recognition service is healthy",
                "service_url": speaker_client.service_url,
                "status": "healthy"
            }
        else:
            return {
                "service_available": False,
                "healthy": False,
                "message": "Speaker recognition service is not responding",
                "service_url": speaker_client.service_url,
                "status": "unhealthy"
            }
        
    except Exception as e:
        logger.error(f"Error checking speaker service status: {e}")
        return {
            "service_available": False,
            "healthy": False,
            "message": f"Health check failed: {str(e)}",
            "status": "error"
        }


# Memory Configuration Management Functions Removed - Project uses config.yml exclusively


async def delete_all_user_memories(user: User):
    """Delete all memories for the current user."""
    try:
        from advanced_omi_backend.services.memory import get_memory_service

        memory_service = get_memory_service()

        # Delete all memories for the user
        deleted_count = await memory_service.delete_all_user_memories(user.user_id)

        logger.info(f"Deleted {deleted_count} memories for user {user.user_id}")

        return {
            "message": f"Successfully deleted {deleted_count} memories",
            "deleted_count": deleted_count,
            "user_id": user.user_id,
            "status": "success"
        }

    except Exception as e:
        logger.error(f"Error deleting all memories for user {user.user_id}: {e}")
        return JSONResponse(
            status_code=500, content={"error": f"Failed to delete memories: {str(e)}"}
        )


# Memory Provider Configuration Functions

async def get_memory_provider():
    """Get current memory provider configuration."""
    try:
        current_provider = os.getenv("MEMORY_PROVIDER", "chronicle").lower()
        # Map legacy provider names to current names
        if current_provider in ("friend-lite", "friend_lite"):
            current_provider = "chronicle"

        # Get available providers
        available_providers = ["chronicle", "openmemory_mcp", "mycelia"]

        return {
            "current_provider": current_provider,
            "available_providers": available_providers,
            "status": "success"
        }

    except Exception as e:
        logger.error(f"Error getting memory provider: {e}")
        return JSONResponse(
            status_code=500, content={"error": f"Failed to get memory provider: {str(e)}"}
        )


async def set_memory_provider(provider: str):
    """Set memory provider and update .env file."""
    try:
        # Validate provider
        provider = provider.lower().strip()
        valid_providers = ["chronicle", "openmemory_mcp", "mycelia"]

        if provider not in valid_providers:
            return JSONResponse(
                status_code=400,
                content={"error": f"Invalid provider '{provider}'. Valid providers: {', '.join(valid_providers)}"}
            )

        # Path to .env file (assuming we're running from backends/advanced/)
        env_path = os.path.join(os.getcwd(), ".env")

        if not os.path.exists(env_path):
            return JSONResponse(
                status_code=404,
                content={"error": f".env file not found at {env_path}"}
            )

        # Read current .env file
        with open(env_path, 'r') as file:
            lines = file.readlines()

        # Update or add MEMORY_PROVIDER line
        provider_found = False
        updated_lines = []

        for line in lines:
            if line.strip().startswith("MEMORY_PROVIDER="):
                updated_lines.append(f"MEMORY_PROVIDER={provider}\n")
                provider_found = True
            else:
                updated_lines.append(line)

        # If MEMORY_PROVIDER wasn't found, add it
        if not provider_found:
            updated_lines.append(f"\n# Memory Provider Configuration\nMEMORY_PROVIDER={provider}\n")

        # Create backup
        backup_path = f"{env_path}.bak"
        shutil.copy2(env_path, backup_path)
        logger.info(f"Created .env backup at {backup_path}")

        # Write updated .env file
        with open(env_path, 'w') as file:
            file.writelines(updated_lines)

        # Update environment variable for current process
        os.environ["MEMORY_PROVIDER"] = provider

        logger.info(f"Updated MEMORY_PROVIDER to '{provider}' in .env file")

        return {
            "message": f"Memory provider updated to '{provider}'. Please restart the backend service for changes to take effect.",
            "provider": provider,
            "env_path": env_path,
            "backup_created": True,
            "requires_restart": True,
            "status": "success"
        }

    except Exception as e:
        logger.error(f"Error setting memory provider: {e}")
        return JSONResponse(
            status_code=500, content={"error": f"Failed to set memory provider: {str(e)}"}
        )


###############################################
# Memory configuration (config.yml backed)
###############################################

def _find_config_yml_path() -> Tuple[Path, dict]:
    """Locate the active config.yml and return its path and parsed YAML.

    Follows the same search order used by the memory config loader.
    """
    current_dir = Path(__file__).parent.resolve()
    candidates = [
        Path("/app/config.yml"),
        current_dir.parent.parent.parent.parent.parent / "config.yml",
        Path("./config.yml"),
    ]
    for p in candidates:
        if p.exists():
            with open(p, "r") as f:
                data = yaml.safe_load(f) or {}
            return p, data
    # If none found, default to /app/config.yml for write, start with empty
    p = Path("/app/config.yml")
    return p, {}


async def get_memory_config_raw():
    """Return the memory section of config.yml as YAML text for editing."""
    try:
        _, data = _find_config_yml_path()
        memory_section = data.get("memory", {}) or {}
        # Return as a full section including the root key for clarity
        yaml_text = yaml.safe_dump({"memory": memory_section}, sort_keys=False)
        return {"config_yaml": yaml_text}
    except Exception as e:
        logger.exception(f"Failed to load memory configuration: {e}")
        raise e


def _parse_memory_yaml(config_yaml: str) -> dict:
    try:
        doc = yaml.safe_load(config_yaml) or {}
        if not isinstance(doc, dict):
            raise ValueError("YAML must define a mapping")
        if "memory" in doc:
            mem = doc.get("memory") or {}
        else:
            mem = doc
        if not isinstance(mem, dict):
            raise ValueError("'memory' section must be a mapping")
        return mem
    except Exception as e:
        logger.exception(f"Invalid YAML: {e}")
        raise e


async def validate_memory_config_raw(config_yaml: str):
    """Validate posted memory YAML without saving."""
    try:
        mem = _parse_memory_yaml(config_yaml)
        # Basic validation rules
        if "provider" in mem and not isinstance(mem["provider"], str):
            return JSONResponse(status_code=400, content={"error": "'provider' must be a string"})
        if "timeout_seconds" in mem and not isinstance(mem["timeout_seconds"], int):
            return JSONResponse(status_code=400, content={"error": "'timeout_seconds' must be an integer"})
        extraction = mem.get("extraction")
        if extraction is not None and not isinstance(extraction, dict):
            return JSONResponse(status_code=400, content={"error": "'extraction' must be a mapping"})
        # If prompt exists, must be string
        if extraction and "prompt" in extraction and not isinstance(extraction["prompt"], str):
            return JSONResponse(status_code=400, content={"error": "'extraction.prompt' must be a string"})
        if extraction and "enabled" in extraction and not isinstance(extraction["enabled"], bool):
            return JSONResponse(status_code=400, content={"error": "'extraction.enabled' must be a boolean"})

        return {"message": "Configuration is valid", "status": "success"}
    except ValueError as e:
        return JSONResponse(status_code=400, content={"error": str(e)})
    except Exception as e:
        logger.error(f"Validation failed: {e}")
        return JSONResponse(status_code=500, content={"error": f"Validation failed: {str(e)}"})


async def update_memory_config_raw(config_yaml: str):
    """Save memory YAML into config.yml and hot-reload memory service."""
    try:
        mem = _parse_memory_yaml(config_yaml)
        path, data = _find_config_yml_path()
        # Merge and write
        data["memory"] = mem
        # Ensure parents
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            yaml.safe_dump(data, f, sort_keys=False)

        # Hot-reload memory service
        reset_memory_service()
        # Create a new instance (lazy init) to validate structure loads
        try:
            _ = get_memory_service()
        except Exception as e:
            # Don't fail the save if service creation fails; report warning
            logger.warning(f"Memory service creation after config update failed: {e}")

        return {
            "message": "Configuration saved and reloaded",
            "path": str(path),
            "status": "success",
        }
    except ValueError as e:
        return JSONResponse(status_code=400, content={"error": str(e)})
    except Exception as e:
        logger.error(f"Failed to save configuration: {e}")
        return JSONResponse(status_code=500, content={"error": f"Failed to save configuration: {str(e)}"})


async def reload_memory_config():
    """Explicitly reload memory service using current config.yml."""
    try:
        reset_memory_service()
        # Recreate instance
        _ = get_memory_service()
        return {"message": "Memory configuration reloaded", "status": "success"}
    except Exception as e:
        logger.error(f"Failed to reload memory configuration: {e}")
        return JSONResponse(status_code=500, content={"error": f"Failed to reload memory configuration: {str(e)}"})
