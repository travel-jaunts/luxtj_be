"""RateHawk dump API client for sync workers."""

from __future__ import annotations

import base64
import json
import time
from collections.abc import Callable
from pathlib import Path

import httpx

from .credentials import load_ratehawk_api

ProgressCb = Callable[[int, int], None]


def _auth_header(key_id: str, api_key: str) -> dict[str, str]:
    token = base64.b64encode(f"{key_id}:{api_key}".encode()).decode("ascii")
    return {"Authorization": f"Basic {token}"}


def fetch_dump_url(endpoint: str, method: str = "GET", body: dict | None = None) -> str:
    creds = load_ratehawk_api()
    headers = {
        **_auth_header(creds["key_id"], creds["api_key"]),
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    with httpx.Client(timeout=120.0) as client:
        resp = client.request(
            method.upper(),
            endpoint,
            headers=headers,
            content=json.dumps(body if body is not None else {})
            if method.upper() == "POST"
            else None,
        )
        resp.raise_for_status()
        payload = resp.json()
    dump_url = str(payload.get("data", {}).get("url") or payload.get("url") or "")
    if not dump_url:
        raise RuntimeError("Dump URL missing in API response")
    return dump_url


def fetch_region_dump_url() -> str:
    creds = load_ratehawk_api()
    return fetch_dump_url(f"{creds['base_url']}/b2b/v3/hotel/region/dump/", "GET")


def fetch_full_hotel_dump_url() -> str:
    creds = load_ratehawk_api()
    return fetch_dump_url(
        f"{creds['base_url']}/b2b/v3/hotel/info/dump/",
        "POST",
        {"inventory": "all", "language": "en"},
    )


def download_to_file(
    dump_url: str,
    dest_path: str | Path,
    on_progress: ProgressCb | None = None,
    progress_interval_sec: float = 2.0,
) -> int:
    path = Path(dest_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with httpx.stream("GET", dump_url, timeout=None) as resp:
        resp.raise_for_status()
        total = int(resp.headers.get("Content-Length") or 0)
        downloaded = 0
        last_tick = 0.0
        with path.open("wb") as fh:
            for chunk in resp.iter_bytes(chunk_size=1024 * 1024):
                if not chunk:
                    continue
                fh.write(chunk)
                downloaded += len(chunk)
                now = time.monotonic()
                if on_progress and (
                    now - last_tick >= progress_interval_sec or downloaded == total
                ):
                    on_progress(downloaded, total)
                    last_tick = now
        if on_progress:
            on_progress(downloaded, total or downloaded)
    return downloaded
