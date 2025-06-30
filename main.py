import ssl
from pathlib import Path
import subprocess

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
import uvicorn

from app.api import auth
from app.core import discdetection
import app.core.drive
from app.api import drives
from app.api import jobs
from app.core import settings as cfg
from app.api import settings as settings_api
from app.api import systeminfo
from app.api import ui
from app.api import ws_log

app = FastAPI(title="TKAutoRipper")
app.include_router(auth.router)
app.include_router(drives.router)
app.include_router(jobs.router)
app.include_router(settings_api.router)
app.include_router(systeminfo.router)
app.include_router(ui.router)
app.include_router(ws_log.router)

app.add_middleware(HTTPSRedirectMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _ensure_cert():
    cert, key = cfg.settings.tls_cert, cfg.settings.tls_key
    cert.parent.mkdir(parents=True, exist_ok=True)
    if cert.exists() and key.exists():
        return
    print("[TLS] Generating self-signed certificate…")
    try:
        subprocess.check_call(
            [
                "openssl",
                "req",
                "-x509",
                "-nodes",
                "-days",
                "3650",
                "-newkey",
                "rsa:4096",
                "-keyout",
                str(key),
                "-out",
                str(cert),
                "-subj",
                "/CN=TKAutoRipper",
            ]
        )
    except FileNotFoundError:
        raise RuntimeError(
            "OpenSSL not found. Install openssl or provide cert.pem/key.pem."
        )


def run():
    _ensure_cert()

    print(cfg.settings.host, cfg.settings.port)

    uvicorn.run(
        "main:app",
        host=cfg.settings.host,
        port=cfg.settings.port,
        ssl_certfile=str(cfg.settings.tls_cert),
        ssl_keyfile=str(cfg.settings.tls_key),
        proxy_headers=True,
    )


if __name__ == "__main__":
    run()
