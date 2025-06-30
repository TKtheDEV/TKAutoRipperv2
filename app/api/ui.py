from pathlib import Path

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

# browser-friendly Basic-Auth (pops the username/password dialog)
from .auth_web import require_web_auth

BASE_DIR = Path(__file__).resolve().parent.parent  # -> app/
templates = Jinja2Templates(directory=BASE_DIR / "frontend" / "templates")

router = APIRouter(tags=["ui"])

@router.get("/", response_class=HTMLResponse,
            dependencies=[Depends(require_web_auth)])
def dashboard(request: Request):
    return templates.TemplateResponse("dashboard.html",
                                      {"request": request})

@router.get("/settings", response_class=HTMLResponse,
            dependencies=[Depends(require_web_auth)])
def settings_page(request: Request):
    return templates.TemplateResponse("settings.html",
                                      {"request": request})

@router.get("/job/{job_id}", response_class=HTMLResponse,
            dependencies=[Depends(require_web_auth)])
def job_page(job_id: str, request: Request):
    return templates.TemplateResponse("job_details.html",
                                      {"request": request,
                                       "job_id": job_id})
