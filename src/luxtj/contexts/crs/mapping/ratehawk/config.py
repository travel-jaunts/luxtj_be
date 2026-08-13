"""RateHawk mapping worker config (sync process)."""

from __future__ import annotations

import os
from pathlib import Path


def _backend_root() -> Path:
    # .../luxtj_be/src/luxtj/contexts/crs/mapping/ratehawk/config.py → luxtj_be
    return Path(__file__).resolve().parents[6]


def storage_path() -> Path:
    raw = os.getenv("LTJBE_RATEHAWK_STORAGE_PATH", "").strip()
    if raw:
        path = Path(raw)
        if not path.is_absolute():
            path = _backend_root() / path
        return path
    return _backend_root() / "storage" / "ratehawk"


def _to_sync_psycopg_url(url: str) -> str:
    # Workers use sync psycopg; strip asyncpg driver if present.
    if url.startswith("postgresql+asyncpg://"):
        return "postgresql://" + url.removeprefix("postgresql+asyncpg://")
    if url.startswith("postgres+asyncpg://"):
        return "postgresql://" + url.removeprefix("postgres+asyncpg://")
    return url


def database_url() -> str:
    """CRS / regions database used by RateHawk mapping workers."""
    url = os.getenv("LTJBE_CRS_DATABASE_URL", "").strip() or os.getenv(
        "LTJBE_DATABASE_URL", ""
    ).strip()
    if not url:
        raise RuntimeError(
            "LTJBE_CRS_DATABASE_URL (or LTJBE_DATABASE_URL) is required for RateHawk mapping workers"
        )
    return _to_sync_psycopg_url(url)


def main_database_url() -> str:
    """Main app DB — booking_apis / integrations live here, not on the CRS DB."""
    url = os.getenv("LTJBE_DATABASE_URL", "").strip()
    if not url:
        raise RuntimeError("LTJBE_DATABASE_URL is required to load RateHawk credentials")
    return _to_sync_psycopg_url(url)


def region_batch_size() -> int:
    return int(os.getenv("LTJBE_RATEHAWK_REGION_BATCH_SIZE", "3000"))


def stream_extract_lines() -> int:
    return 20000


def stream_stage_batch() -> int:
    return 1500


def promote_batch_size() -> int:
    return 500


def promote_hotel_workers() -> int:
    return 2


def promote_room_workers() -> int:
    return 2


def stream_total_lines_estimate() -> int:
    return int(os.getenv("LTJBE_RATEHAWK_STREAM_TOTAL_LINES_ESTIMATE", "0"))
