import logging
import requests
from requests.exceptions import RequestException
from .settings import settings

log = logging.getLogger("api_helpers")

def post_api(path: str, json: dict, *, verify: bool | None = None):
    url = settings.base_url.rstrip("/") + path
    try:
        resp = requests.post(
            url,
            json=json,
            timeout=30,
            verify=settings.tls_verify if verify is None else verify,
        )
        resp.raise_for_status()
        return resp.json()
    except RequestException as exc:
        log.warning("POST %s failed: %s (non-fatal)", url, exc)
        return None