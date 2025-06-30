import ipaddress
from pathlib import Path
from typing import Any, Optional

import yaml
from pydantic_settings import BaseSettings, SettingsConfigDict

CFG_PATH = Path("~/TKAutoRipper/config/TKAutoRipper.conf").expanduser()

def _yaml_defaults() -> dict[str, Any]:
    """
    Flatten TKAutoRipper.conf into {'Section.key': value}.
    Also copy Advanced.host/port to plain 'host' and 'port'
    so the Settings model picks them up.
    """
    if not CFG_PATH.exists():
        return {}

    data = yaml.safe_load(CFG_PATH.read_text()) or {}
    flat: dict[str, Any] = {}
    for section, mapping in data.items():
        for key, meta in mapping.items():
            # each leaf is a dict with 'value', or a raw scalar
            val = meta.get("value") if isinstance(meta, dict) else meta
            if val in (None, ""):
                continue

            flat[f"{section}.{key}"] = val

            # ── promotion ─────────────────────────────
            if section.lower() == "advanced" and key.lower() in {"host", "port"}:
                flat[key.lower()] = val        # → 'host' or 'port'
    return flat

class Settings(BaseSettings):
    # ── Networking ────────────────────────────────
    host: str = "::"
    port: int = 8000
    base_url: Optional[str] = None
    tls_cert: Path = Path("~/TKAutoRipper/config/cert.pem").expanduser()
    tls_key: Path = Path("~/TKAutoRipper/config/key.pem").expanduser()
    tls_verify: bool = True

    # ── Auth (unchanged) ─────────────────────────
    username: str = "admin"
    password_hash: Optional[str] = None
    jwt_secret: str = "CHANGE_ME"
    jwt_exp_minutes: int = 15
    login_max_attempts: int = 5
    login_window_sec: int = 900

    # ── Misc (unchanged) ─────────────────────────
    temp_dir: Path = Path("~/TKAutoRipper/temp").expanduser()
    output_dir: Path = Path("~/TKAutoRipper/output").expanduser()

    model_config = SettingsConfigDict(
        env_prefix="TKAR_",
        case_sensitive=False,
        extra="ignore",
    )


# apply YAML first, then env overrides
settings = Settings(_secrets_dir=None, **_yaml_defaults())

# ── robust base_url fallback ─────────────────────────────────────
if settings.base_url is None:
    # If host is wildcard ("[::]" or "0.0.0.0") choose loopback
    stripped = settings.host.strip("[]")
    if stripped in {"", "::", "0.0.0.0"}:
        stripped = "::1"
    settings.base_url = f"https://[{stripped}]:{settings.port}"
