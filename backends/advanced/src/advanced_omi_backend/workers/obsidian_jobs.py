"""
RQ job definitions for Obsidian ingestion.
"""

import logging
import os

from rq import get_current_job

from advanced_omi_backend.services.obsidian_service import obsidian_service
from advanced_omi_backend.services.obsidian_job_tracker import (
    append_job_error,
    get_job_state,
    update_job_state,
)

logger = logging.getLogger(__name__)


class JobCancelled(Exception):
    """Raised when the user requested cancellation."""


def count_markdown_files(vault_path: str) -> int:
    """Recursively count markdown files in a vault."""
    count = 0
    for root, dirs, files in os.walk(vault_path):
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        for filename in files:
            if filename.endswith(".md"):
                count += 1
    return count


def _check_cancel_requested(job_id: str) -> None:
    state = get_job_state(job_id)
    if state and state.get("status") == "cancel_requested":
        raise JobCancelled()


def ingest_obsidian_vault_job(job_id: str, vault_path: str) -> None:
    """
    Long-running ingestion job enqueued on the default RQ queue.
    """
    logger.info("Starting Obsidian ingestion job %s", job_id)
    state = get_job_state(job_id) or {}
    if not state:
        logger.warning("No existing job metadata for %s. Initializing state.", job_id)
        update_job_state(
            job_id,
            status="running",
            processed=0,
            errors=[],
            vault_path=vault_path,
        )
    else:
        update_job_state(job_id, status="running", processed=0, error=None)

    try:
        obsidian_service.setup_database()
    except Exception as exc:
        logger.exception("Database setup failed for job %s: %s", job_id, exc)
        update_job_state(job_id, status="failed", error=f"Database setup failed: {exc}")
        raise

    if not os.path.exists(vault_path):
        msg = f"Vault path not found: {vault_path}"
        logger.error(msg)
        update_job_state(job_id, status="failed", error=msg)
        return

    total = count_markdown_files(vault_path)
    update_job_state(job_id, total=total)

    current_job = get_current_job()
    if current_job:
        current_job.meta = current_job.meta or {}
        current_job.meta["total_files"] = total
        current_job.save_meta()

    processed = 0
    try:
        for root, dirs, files in os.walk(vault_path):
            dirs[:] = [d for d in dirs if not d.startswith(".")]
            for filename in files:
                if not filename.endswith(".md"):
                    continue

                _check_cancel_requested(job_id)

                try:
                    note_data = obsidian_service.parse_obsidian_note(root, filename, vault_path)
                    chunks = obsidian_service.chunking_and_embedding(note_data)
                    if chunks:
                        obsidian_service.ingest_note_and_chunks(note_data, chunks)
                    processed += 1
                    update_job_state(
                        job_id,
                        processed=processed,
                        last_file=os.path.join(root, filename),
                    )
                except Exception as exc:
                    logger.error("Processing %s failed: %s", filename, exc)
                    append_job_error(job_id, f"{filename}: {exc}")

        update_job_state(job_id, status="completed")
    except JobCancelled:
        logger.info("Obsidian ingestion job %s cancelled by user", job_id)
        update_job_state(job_id, status="cancelled")
    except Exception as exc:
        logger.exception("Ingestion worker failed for job %s: %s", job_id, exc)
        update_job_state(job_id, status="failed", error=str(exc))
        raise
