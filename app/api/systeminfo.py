from fastapi import APIRouter, Depends
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from app.api.auth import require_auth
from app.core.systeminfo import get_system_info

router = APIRouter()

@router.get("/api/system-info", dependencies=[Depends(require_auth)])
def system_info():
    return get_system_info()
