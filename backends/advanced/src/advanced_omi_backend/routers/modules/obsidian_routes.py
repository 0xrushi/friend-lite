
import logging
import os
import uuid
import zipfile
import threading
from pathlib import Path
from typing import Dict, Any

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, UploadFile, File, Body
from pydantic import BaseModel

from advanced_omi_backend.auth import current_active_user, current_superuser
from advanced_omi_backend.users import User
from advanced_omi_backend.services.obsidian_service import obsidian_service

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


# Simple in-memory job tracker for progress (single-process only)
_jobs: Dict[str, Dict[str, Any]] = {}
_jobs_lock = threading.Lock()


def _count_markdown_files(vault_path: str) -> int:
    count = 0
    for root, dirs, files in os.walk(vault_path):
        dirs[:] = [d for d in dirs if not d.startswith('.')]  # skip hidden
        for f in files:
            if f.endswith('.md'):
                count += 1
    return count


def _ingest_worker(job_id: str, vault_path: str):
    try:
        # Ensure DB constraints / index exist before heavy operations
        try:
            obsidian_service.setup_database()
        except Exception as e:
            with _jobs_lock:
                _jobs[job_id] = {"status": "failed", "error": f"Database setup failed: {e}"}
            return

        total = _count_markdown_files(vault_path)
        with _jobs_lock:
            if job_id not in _jobs:
                return
            _jobs[job_id].update({
                "status": "running",
                "total": total,
                "processed": 0,
                "errors": [],
            })

        for root, dirs, files in os.walk(vault_path):
            dirs[:] = [d for d in dirs if not d.startswith('.')]
            for file in files:
                if not file.endswith('.md'):
                    continue
                try:
                    note_data = obsidian_service.parse_obsidian_note(root, file, vault_path)
                    chunks = obsidian_service.chunking_and_embedding(note_data)
                    if chunks:
                        obsidian_service.ingest_note_and_chunks(note_data, chunks)
                    with _jobs_lock:
                        if job_id in _jobs:
                            _jobs[job_id]["processed"] += 1
                            _jobs[job_id]["last_file"] = os.path.join(root, file)
                except Exception as e:
                    logger.error(f"Processing {file} failed: {e}")
                    with _jobs_lock:
                        if job_id in _jobs:
                            _jobs[job_id]["errors"].append(f"{file}: {str(e)}")

        with _jobs_lock:
            if job_id in _jobs:
                _jobs[job_id]["status"] = "completed"
    except Exception as e:
        logger.error(f"Ingest worker failed: {e}")
        with _jobs_lock:
            if job_id in _jobs:
                _jobs[job_id]["status"] = "failed"
                _jobs[job_id]["error"] = str(e)


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

        total = _count_markdown_files(str(extract_dir))

        with _jobs_lock:
            _jobs[job_id] = {
                "status": "ready",
                "total": total,
                "processed": 0,
                "errors": [],
                "vault_path": str(extract_dir),
            }

        return {"job_id": job_id, "vault_path": str(extract_dir), "total_files": total}
    except Exception as e:
        logger.error(f"Failed to process uploaded zip: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to process uploaded zip: {e}")


@router.post("/start")
async def start_ingestion(
    job_id: str = Body(..., embed=True),
    current_user: User = Depends(current_active_user)
):
    with _jobs_lock:
        job = _jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.get("status") not in ("ready", "failed", "completed"):
        raise HTTPException(status_code=400, detail=f"Job is not in a startable state: {job.get('status')}")

    vault_path = job.get("vault_path")
    if not vault_path or not os.path.exists(vault_path):
        raise HTTPException(status_code=400, detail="Vault path not available for this job")

    # Start background worker and return immediately; UI should poll status
    t = threading.Thread(target=_ingest_worker, args=(job_id, vault_path), daemon=True)
    t.start()
    with _jobs_lock:
        _jobs[job_id]["status"] = "starting"
    return {"message": "Ingestion started", "job_id": job_id}


@router.get("/status")
async def get_status(job_id: str, current_user: User = Depends(current_active_user)):
    with _jobs_lock:
        job = _jobs.get(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        # Compute percent if total>0
        total = job.get("total", 0)
        processed = job.get("processed", 0)
        percent = int((processed / total) * 100) if total else 0
        data = {**job, "percent": percent}
    return data


@router.post("/cancel")
async def cancel_job(job_id: str = Body(..., embed=True), current_user: User = Depends(current_superuser)):
    with _jobs_lock:
        job = _jobs.get(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        job["status"] = "cancel_requested"
    # Note: cooperative cancellation not implemented in worker loop
    return {"message": "Cancellation requested", "job_id": job_id}
