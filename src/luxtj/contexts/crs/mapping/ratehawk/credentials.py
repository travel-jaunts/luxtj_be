"""Load RateHawk credentials from booking_apis for sync workers."""

from __future__ import annotations

import json
from contextlib import contextmanager
from typing import Any, Iterator

from .config import main_database_url


def _credential(configs: dict[str, Any], *keys: str) -> str:
    for key in keys:
        val = configs.get(key)
        if val is not None and str(val).strip():
            return str(val).strip()
    # normalized keys (spaces → underscores)
    for key in keys:
        nk = key.replace(" ", "_")
        val = configs.get(nk)
        if val is not None and str(val).strip():
            return str(val).strip()
    return ""


@contextmanager
def _main_db_cursor() -> Iterator[Any]:
    import psycopg

    conn = psycopg.connect(main_database_url())
    try:
        with conn.cursor() as cur:
            yield cur
        conn.commit()
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        raise
    finally:
        conn.close()


def load_ratehawk_api() -> dict[str, Any]:
    try:
        with _main_db_cursor() as cur:
            cur.execute(
                """
                SELECT id, configuration
                FROM booking_apis
                WHERE code = 'ratehawk'
                  AND status IS TRUE
                ORDER BY id ASC
                LIMIT 1
                """
            )
            row = cur.fetchone()
    except RuntimeError:
        raise
    except Exception as exc:
        raise RuntimeError(f"Failed to load RateHawk credentials: {exc}") from exc

    if not row:
        raise RuntimeError("RateHawk booking API is not configured or inactive")
    api_id = str(row[0])
    raw_config = row[1]
    if isinstance(raw_config, str):
        config = json.loads(raw_config) if raw_config else {}
    elif isinstance(raw_config, dict):
        config = raw_config
    else:
        config = {}

    configs = config.get("configs") if isinstance(config.get("configs"), dict) else config
    if not isinstance(configs, dict):
        configs = {}
    base_url = _credential(configs, "EndPointUrl", "EndPointUrl").rstrip("/") or (
        "https://api.worldota.net/api"
    )
    key_id = _credential(configs, "API key ID", "API_key_ID")
    api_key = _credential(configs, "API key access token", "API_key_access_token")
    if not key_id or not api_key:
        raise RuntimeError("RateHawk API credentials missing in booking_apis.configuration")

    return {
        "booking_source_id": api_id,
        "base_url": base_url,
        "key_id": key_id,
        "api_key": api_key,
    }
