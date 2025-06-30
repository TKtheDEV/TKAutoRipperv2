"""
auth_web.py
Browser-friendly Basic-Auth dependency for HTML pages.

• Pops the standard username/password dialog on first visit
• Hashes and stores the password on first successful login
• Shares the same username/password storage as the API’s JWT auth
"""

from datetime import datetime
from typing import Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from ..core.security import (
    verify_password,
    hash_and_store_password,
    throttle,
    FAILED_LOGINS,
)
from ..core.settings import settings

basic = HTTPBasic(auto_error=False)


def _get_client_ip(request: Request) -> str:
    fwd = request.headers.get("x-forwarded-for")
    return fwd.split(",")[0].strip() if fwd else request.client.host


def require_web_auth(
    request: Request,
    credentials: Optional[HTTPBasicCredentials] = Depends(basic),
):
    ip = _get_client_ip(request)
    throttle(ip)  # reuse the same brute-force limiter as JWT

    if credentials is None:
        # No creds supplied → ask browser to prompt
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Login required",
            headers={"WWW-Authenticate": "Basic"},
        )

    # First boot: hash & store the plain password once
    if settings.password_hash is None:
        hash_and_store_password(credentials.password)

    if credentials.username == settings.username and verify_password(
        credentials.password, settings.password_hash
    ):
        return credentials.username

    # Bad creds → count failure & re-prompt
    FAILED_LOGINS.setdefault(ip, []).append(datetime.utcnow().timestamp())
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid credentials",
        headers={"WWW-Authenticate": "Basic"},
    )
