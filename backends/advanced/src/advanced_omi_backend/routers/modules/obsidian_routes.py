
import logging
import os
import uuid
import zipfile
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Body
from rq.command import send_stop_job_command
from rq.exceptions import NoSuchJobError
from rq.job import Job
from pydantic import BaseModel

from advanced_omi_backend.auth import current_active_user, current_superuser
from advanced_omi_backend.controllers.queue_controller import default_queue, redis_conn
from advanced_omi_backend.services.obsidian_job_tracker import (
    get_job_state,
    save_job_state,
    update_job_state,
)
from advanced_omi_backend.users import User
from advanced_omi_backend.services.obsidian_service import obsidian_service
from advanced_omi_backend.workers.obsidian_jobs import (
    count_markdown_files,
    ingest_obsidian_vault_job,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/obsidian", tags=["obsidian"])

class IngestRequest(BaseModel):
    vault_path: str

@router.post("/ingest")
async def ingest_obsidian_vault(
    request: IngestRequest,
    current_user: User = Depends(current_active_user)
):
    """
    Immediate/synchronous ingestion endpoint (legacy). Not recommended for UI.
    Prefer the upload_zip + start endpoints to enable progress reporting.
    """
    if not os.path.exists(request.vault_path):
        raise HTTPException(status_code=400, detail=f"Path not found: {request.vault_path}")

    try:
        result = obsidian_service.ingest_vault(request.vault_path)
        return {"message": "Ingestion complete", **result}
    except Exception as e:
        logger.error(f"Ingestion failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/upload_zip")
async def upload_obsidian_zip(
    file: UploadFile = File(...),
    current_user: User = Depends(current_superuser)
):
    """
    Upload a zipped Obsidian vault. Returns a job_id that can be started later.
    """
    if not file.filename.lower().endswith('.zip'):
        raise HTTPException(status_code=400, detail="Please upload a .zip file of your Obsidian vault")

    job_id = str(uuid.uuid4())
    base_dir = Path("/app/data/obsidian_jobs")
    base_dir.mkdir(parents=True, exist_ok=True)
    job_dir = base_dir / job_id
    job_dir.mkdir(parents=True, exist_ok=True)
    zip_path = job_dir / "vault.zip"
    extract_dir = job_dir / "vault"
    try:
        # Save
        with open(zip_path, 'wb') as out:
            out.write(await file.read())
        # Extract
        with zipfile.ZipFile(zip_path, 'r') as zf:
            zf.extractall(extract_dir)

        total = count_markdown_files(str(extract_dir))

        save_job_state(job_id, {
            "status": "ready",
            "total": total,
            "processed": 0,
            "errors": [],
            "vault_path": str(extract_dir),
            "rq_job_id": None,
        })

        return {"job_id": job_id, "vault_path": str(extract_dir), "total_files": total}
    except Exception as e:
        logger.error(f"Failed to process uploaded zip: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to process uploaded zip: {e}")


@router.post("/start")
async def start_ingestion(
    job_id: str = Body(..., embed=True),
    current_user: User = Depends(current_active_user)
):
    job = get_job_state(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.get("status") in ("queued", "running"):
        raise HTTPException(status_code=400, detail=f"Job already {job.get('status')}")
    if job.get("status") not in ("ready", "failed", "completed", "cancelled"):
        raise HTTPException(status_code=400, detail=f"Job is not in a startable state: {job.get('status')}")

    vault_path = job.get("vault_path")
    if not vault_path or not os.path.exists(vault_path):
        raise HTTPException(status_code=400, detail="Vault path not available for this job")

    rq_job = default_queue.enqueue(
        ingest_obsidian_vault_job,
        kwargs={
            "job_id": job_id,
            "vault_path": vault_path,
        },
        description=f"Obsidian ingestion for job {job_id}",
    )

    update_job_state(
        job_id,
        status="queued",
        processed=0,
        error=None,
        last_file=None,
        errors=[],
        rq_job_id=rq_job.id,
    )
    return {"message": "Ingestion started", "job_id": job_id, "rq_job_id": rq_job.id}


@router.get("/status")
async def get_status(job_id: str, current_user: User = Depends(current_active_user)):
    job = get_job_state(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    total = job.get("total", 0)
    processed = job.get("processed", 0)
    percent = int((processed / total) * 100) if total else 0
    return {**job, "percent": percent}


@router.post("/cancel")
async def cancel_job(job_id: str = Body(..., embed=True), current_user: User = Depends(current_superuser)):
    job = get_job_state(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    update_job_state(job_id, status="cancel_requested")

    rq_job_id = job.get("rq_job_id")
    if rq_job_id:
        try:
            rq_job = Job.fetch(rq_job_id, connection=redis_conn)
            rq_job.cancel()
            if rq_job.is_started:
                send_stop_job_command(redis_conn, rq_job_id)
        except NoSuchJobError:
            logger.info("RQ job %s already gone while cancelling %s", rq_job_id, job_id)
        except Exception as exc:
            logger.error("Failed to cancel RQ job %s: %s", rq_job_id, exc)

    return {"message": "Cancellation requested", "job_id": job_id}
