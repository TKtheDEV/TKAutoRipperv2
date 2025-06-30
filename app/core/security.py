from datetime import datetime, timedelta
from typing import Dict

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer
from passlib.hash import bcrypt

from .settings import settings

bearer_scheme = HTTPBearer(auto_error=False)
FAILED_LOGINS: Dict[str, list[float]] = {}          # ip → timestamps


def create_access_token(username: str) -> str:
    exp = datetime.utcnow() + timedelta(minutes=settings.jwt_exp_minutes)
    return jwt.encode(
        {"sub": username, "exp": exp},
        settings.jwt_secret,
        algorithm="HS256",
    )


def verify_password(plain_pw: str, hashed: str) -> bool:
    return bcrypt.verify(plain_pw, hashed)


def hash_and_store_password(plain_pw: str) -> None:
    hashed = bcrypt.hash(plain_pw)
    settings.password_hash = hashed
    # TODO: persist to disk (yaml/json) once config refactor hits
    # For now we just keep it in memory for this boot.


def throttle(ip: str) -> None:
    window = settings.login_window_sec
    now = datetime.utcnow().timestamp()
    attempts = [ts for ts in FAILED_LOGINS.get(ip, []) if now - ts <= window]
    if len(attempts) >= settings.login_max_attempts:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many failed logins, try later",
        )
    FAILED_LOGINS[ip] = attempts  # prune old entries
