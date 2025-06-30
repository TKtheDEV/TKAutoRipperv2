from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from fastapi.security import HTTPBasic, HTTPBasicCredentials, HTTPBearer, HTTPAuthorizationCredentials
import jwt

from ..core.security import (
    bearer_scheme,
    create_access_token,
    hash_and_store_password,
    throttle,
    verify_password,
    FAILED_LOGINS,
)
from ..core.settings import settings

router = APIRouter(tags=["auth"])
basic = HTTPBasic(auto_error=False)

# ───────────────── helper ─────────────────────────────────────────
def _get_client_ip(request: Request) -> str:
    fwd = request.headers.get("x-forwarded-for")
    return fwd.split(",")[0].strip() if fwd else request.client.host

# ───────────────── /login route ───────────────────────────────────
@router.post("/login", response_model=None, status_code=status.HTTP_204_NO_CONTENT)
def login(
    request: Request,
    credentials: HTTPBasicCredentials = Depends(basic),
):
    ip = _get_client_ip(request)
    throttle(ip)

    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    if settings.password_hash is None:
        hash_and_store_password(credentials.password)

    if credentials.username != settings.username or not verify_password(
        credentials.password, settings.password_hash
    ):
        FAILED_LOGINS.setdefault(ip, []).append(datetime.utcnow().timestamp())
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    token = create_access_token(credentials.username)
    resp = Response(status_code=status.HTTP_204_NO_CONTENT)
    resp.set_cookie(
        "access_token",
        token,
        httponly=True,
        secure=True,
        samesite="strict",
        max_age=settings.jwt_exp_minutes * 60,
    )
    return resp

# ───────────────── dependency for protected endpoints ─────────────
from fastapi.security import HTTPAuthorizationCredentials

bearer_scheme_opt = HTTPBearer(auto_error=False)

def require_auth(
    request: Request,
    bearer: HTTPAuthorizationCredentials | None = Depends(bearer_scheme_opt),
):
    # Accept either Bearer header or cookie
    token = bearer.credentials if bearer else request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
        return payload["sub"]
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")