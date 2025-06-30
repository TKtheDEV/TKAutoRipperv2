# app/api/jobs.py
#
# Adds resumable-jobs discovery + resume endpoint.

from pathlib import Path
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse

from app.api.auth import require_auth
from app.core.job.tracker import job_tracker
from app.core.job.job import Job
from app.core.job.runner import JobRunner
from app.core.templates import templates

router = APIRouter()

# ──────────────────────────────────────────────────────────
@router.get("/jobs/{job_id}", response_class=HTMLResponse,
            dependencies=[Depends(require_auth)])
def job_details_page(request: Request, job_id: str):
    job = job_tracker.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return templates.TemplateResponse("job_details.html",
                                      {"request": request, "job": job})

# live jobs
@router.get("/api/jobs", dependencies=[Depends(require_auth)])
def list_jobs():
    return [j.to_dict() for j in job_tracker.list_jobs()]

# single live job
@router.get("/api/jobs/{job_id}", dependencies=[Depends(require_auth)])
def get_job(job_id: str):
    job = job_tracker.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job.to_dict()

# ───── RESUMABLE JOB DISCOVERY ───────────────────────────
RESUME_ROOT = Path("~/TKAutoRipper/temp").expanduser()

def _find_resume_files() -> List[Path]:
    return list(RESUME_ROOT.glob("*/.resume.json"))

@router.get("/api/jobs/resumable", dependencies=[Depends(require_auth)])
def list_resumable_jobs():
    jobs = []
    for file_path in _find_resume_files():
        try:
            job = Job.from_resume_file(file_path)
            # Only resumable if first step completed
            if job.steps and job.steps[0]["completed"]:
                jobs.append(job.to_dict())
        except Exception:
            continue
    return jobs

# ───── RESUME ENDPOINT ───────────────────────────────────
@router.post("/api/jobs/{job_id}/resume", dependencies=[Depends(require_auth)])
def resume_job(job_id: str):
    resume_file = RESUME_ROOT / job_id / ".resume.json"
    if not resume_file.exists():
        raise HTTPException(status_code=404, detail="No resume info")

    job = Job.from_resume_file(resume_file)
    job.job_status = "Queued"
    job_tracker.add_job(job)

    runner = JobRunner(job)
    runner.run()

    return {"status": "resumed", "job_id": job_id}
