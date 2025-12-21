"""
Utilities for tracking Obsidian ingestion job state in Redis.
"""

import json
import logging
from typing import Any, Dict, Optional

from advanced_omi_backend.controllers.queue_controller import redis_conn

logger = logging.getLogger(__name__)

_JOB_KEY_PREFIX = "obsidian_job:"


def _job_key(job_id: str) -> str:
    return f"{_JOB_KEY_PREFIX}{job_id}"


def get_job_state(job_id: str) -> Optional[Dict[str, Any]]:
    """Load job state JSON from Redis."""
    raw = redis_conn.get(_job_key(job_id))
    if not raw:
        return None
    try:
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8")
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        logger.error("Failed to decode job state for %s: %s", job_id, exc)
        return None


def save_job_state(job_id: str, state: Dict[str, Any]) -> None:
    """Persist the entire state dict."""
    redis_conn.set(_job_key(job_id), json.dumps(state))


def update_job_state(job_id: str, **updates) -> Dict[str, Any]:
    """Update specific keys on the job state and persist."""
    state = get_job_state(job_id) or {}
    state.update(updates)
    save_job_state(job_id, state)
    return state


def append_job_error(job_id: str, message: str) -> Dict[str, Any]:
    """Append an error message to the job state."""
    state = get_job_state(job_id) or {}
    errors = state.get("errors") or []
    errors.append(message)
    state["errors"] = errors
    save_job_state(job_id, state)
    return state


def delete_job_state(job_id: str) -> None:
    """Remove the job state from Redis."""
    redis_conn.delete(_job_key(job_id))
