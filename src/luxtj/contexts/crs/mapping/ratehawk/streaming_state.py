from __future__ import annotations

from copy import deepcopy
from typing import Any

from . import db


def default_state(run_id: str, zst_path: str = "", total_estimate: int | None = None) -> dict[str, Any]:
    return {
        "version": 1,
        "run_id": run_id,
        "zst_path": zst_path,
        "zst_next_line": 1,
        "zst_lines_total": 0,
        "zst_lines_total_estimate": total_estimate,
        "zst_lines_total_is_estimate": False,
        "zst_bytes_total": 0,
        "zst_bytes_read": 0,
        "current_batch": empty_batch(0),
        "totals": {
            "processed_lines": 0,
            "inserted_hotels": 0,
            "skipped": 0,
            "rooms_synced": 0,
        },
        "updated_at": db._iso_now(),
    }


def empty_batch(index: int) -> dict[str, Any]:
    return {
        "index": index,
        "zst_start_line": 0,
        "extract_target": 0,
        "extract_done": 0,
        "batch_lines_done": 0,
        "batch_size_cap": 0,
        "phase": "extract",
        "hotels_staged": 0,
        "hotels_promoted": 0,
        "rooms_staged": 0,
        "rooms_promoted": 0,
    }


def wiped_state(run_id: str) -> dict[str, Any]:
    """Zeroed streaming checkpoint used after CRS wipe (mapping UI shows 0%)."""
    state = default_state(run_id, zst_path="")
    state["current_batch"] = {**empty_batch(0), "phase": "idle"}
    return state


def mark_runs_streaming_wiped(booking_source_id: str, *, limit: int = 50) -> int:
    """Invalidate full-stream checkpoints and zero progress after wipe."""
    import json

    with db.db_cursor() as (_, cur):
        cur.execute(
            """
            SELECT id, meta FROM hotel_mapping_runs
            WHERE booking_source_id = %s
              AND parent_run_id IS NULL
              AND dump_type = 'full'
            ORDER BY created_at DESC
            LIMIT %s
            """,
            (booking_source_id, limit),
        )
        rows = cur.fetchall()
    n = 0
    for rid, meta_raw in rows:
        meta = meta_raw if isinstance(meta_raw, dict) else (json.loads(meta_raw) if meta_raw else {})
        meta["streaming_wiped"] = True
        meta["stream_phase"] = "wiped"
        meta["phase"] = "wiped"
        meta["streaming"] = wiped_state(str(rid))
        meta.pop("download_bytes", None)
        meta.pop("download_total", None)
        db.update_run(str(rid), meta=meta, zst_path=None)
        n += 1
    return n


def load(run_id: str) -> dict[str, Any]:
    run = db.fetch_run(run_id)
    if not run:
        return default_state(run_id)
    meta = run.get("meta") or {}
    if isinstance(meta, str):
        import json

        meta = json.loads(meta) if meta else {}
    streaming = meta.get("streaming")
    if not isinstance(streaming, dict) or not streaming:
        return default_state(run_id, str(run.get("zst_path") or ""))
    base = default_state(run_id)
    merged = deepcopy(base)
    merged.update({k: v for k, v in streaming.items() if k in merged or k in streaming})
    merged["current_batch"] = {**empty_batch(0), **(streaming.get("current_batch") or {})}
    merged["totals"] = {**base["totals"], **(streaming.get("totals") or {})}
    merged["run_id"] = run_id
    return merged


def save(run_id: str, patch: dict[str, Any]) -> dict[str, Any]:
    run = db.fetch_run(run_id)
    if not run:
        raise RuntimeError(f"Run {run_id} not found")
    meta = run.get("meta") or {}
    if isinstance(meta, str):
        import json

        meta = json.loads(meta) if meta else {}
    state = load(run_id)
    _deep_merge(state, patch)
    state["run_id"] = run_id
    state["updated_at"] = db._iso_now()
    batch = state.get("current_batch") or {}
    meta["streaming"] = state
    meta["stream_phase"] = str(batch.get("phase") or meta.get("stream_phase") or "extract")
    meta["heartbeat_at"] = db._iso_now()
    db.update_run(run_id, meta=meta)
    return state


def _deep_merge(target: dict[str, Any], patch: dict[str, Any]) -> None:
    for key, value in patch.items():
        if key == "current_batch" and isinstance(value, dict):
            batch = target.setdefault("current_batch", empty_batch(0))
            batch.update(value)
        elif key == "totals" and isinstance(value, dict):
            totals = target.setdefault("totals", {})
            totals.update(value)
        else:
            target[key] = value
