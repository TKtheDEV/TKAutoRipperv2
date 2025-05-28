from fastapi import Request, Depends, HTTPException, APIRouter
from fastapi.responses import HTMLResponse
from app.core.auth import verify_web_auth
from app.core.job.tracker import job_tracker
from app.core.templates import templates        

router=APIRouter()

@router.get("/jobs/{job_id}", response_class=HTMLResponse, dependencies=[Depends(verify_web_auth)])
def job_details_page(request: Request, job_id: str):
    job = job_tracker.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return templates.TemplateResponse("job_details.html", {"request": request, "job": job})


@router.get("/api/jobs/{job_id}")
def get_job(job_id: str):
    job = job_tracker.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job.to_dict()

@router.get("/api/jobs")
def list_jobs():
    return [job.to_dict() for job in job_tracker.list_jobs()]