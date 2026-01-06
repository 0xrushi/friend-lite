"""
Worker Registry

Builds the complete list of worker definitions with conditional logic.
Reuses model_registry.py for config.yml parsing.
"""

import os
import logging
from typing import List

from .config import WorkerDefinition, WorkerType

logger = logging.getLogger(__name__)


def get_default_stt_provider() -> str:
    """
    Query config.yml for the default STT provider.

    Returns:
        Provider name (e.g., "deepgram", "parakeet") or empty string if not configured
    """
    try:
        from advanced_omi_backend.model_registry import get_models_registry

        registry = get_models_registry()
        if registry and registry.defaults:
            stt_model = registry.get_default("stt")
            if stt_model:
                return stt_model.model_provider or ""
    except Exception as e:
        logger.warning(f"Failed to read STT provider from config.yml: {e}")

    return ""


def should_start_deepgram_batch() -> bool:
    """
    Check if Deepgram batch worker should start.

    Conditions:
    - DEFAULT_STT provider is "deepgram" (from config.yml)
    - DEEPGRAM_API_KEY is set in environment
    """
    stt_provider = get_default_stt_provider()
    has_api_key = bool(os.getenv("DEEPGRAM_API_KEY"))

    enabled = stt_provider == "deepgram" and has_api_key

    if stt_provider == "deepgram" and not has_api_key:
        logger.warning(
            "Deepgram configured as default STT but DEEPGRAM_API_KEY not set - worker disabled"
        )

    return enabled


def should_start_parakeet() -> bool:
    """
    Check if Parakeet stream worker should start.

    Conditions:
    - DEFAULT_STT provider is "parakeet" (from config.yml)
    """
    stt_provider = get_default_stt_provider()
    return stt_provider == "parakeet"


def build_worker_definitions() -> List[WorkerDefinition]:
    """
    Build the complete list of worker definitions.

    Returns:
        List of WorkerDefinition objects, including conditional workers
    """
    workers = []

    # 6x RQ Workers - Multi-queue workers (transcription, memory, default)
    for i in range(1, 7):
        workers.append(
            WorkerDefinition(
                name=f"rq-worker-{i}",
                command=[
                    "uv",
                    "run",
                    "python",
                    "-m",
                    "advanced_omi_backend.workers.rq_worker_entry",
                    "transcription",
                    "memory",
                    "default",
                ],
                worker_type=WorkerType.RQ_WORKER,
                queues=["transcription", "memory", "default"],
                restart_on_failure=True,
            )
        )

    # Audio Persistence Worker - Single-queue worker (audio queue)
    workers.append(
        WorkerDefinition(
            name="audio-persistence",
            command=[
                "uv",
                "run",
                "python",
                "-m",
                "advanced_omi_backend.workers.rq_worker_entry",
                "audio",
            ],
            worker_type=WorkerType.RQ_WORKER,
            queues=["audio"],
            restart_on_failure=True,
        )
    )

    # Deepgram Batch Worker - Conditional (if DEFAULT_STT=deepgram + API key)
    workers.append(
        WorkerDefinition(
            name="deepgram-batch",
            command=[
                "uv",
                "run",
                "python",
                "-m",
                "advanced_omi_backend.workers.audio_stream_deepgram_worker",
            ],
            worker_type=WorkerType.STREAM_CONSUMER,
            enabled_check=should_start_deepgram_batch,
            restart_on_failure=True,
        )
    )

    # Parakeet Stream Worker - Conditional (if DEFAULT_STT=parakeet)
    workers.append(
        WorkerDefinition(
            name="parakeet-stream",
            command=[
                "uv",
                "run",
                "python",
                "-m",
                "advanced_omi_backend.workers.audio_stream_parakeet_worker",
            ],
            worker_type=WorkerType.STREAM_CONSUMER,
            enabled_check=should_start_parakeet,
            restart_on_failure=True,
        )
    )

    # Log worker configuration
    stt_provider = get_default_stt_provider()
    logger.info(f"STT Provider from config.yml: {stt_provider or 'none'}")

    enabled_workers = [w for w in workers if w.is_enabled()]
    disabled_workers = [w for w in workers if not w.is_enabled()]

    logger.info(f"Total workers configured: {len(workers)}")
    logger.info(f"Enabled workers: {len(enabled_workers)}")
    logger.info(
        f"Enabled worker names: {', '.join([w.name for w in enabled_workers])}"
    )

    if disabled_workers:
        logger.info(
            f"Disabled workers: {', '.join([w.name for w in disabled_workers])}"
        )

    return enabled_workers
