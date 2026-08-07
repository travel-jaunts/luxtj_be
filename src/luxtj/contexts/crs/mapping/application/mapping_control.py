"""Admin control plane for RateHawk region/hotel stream mapping."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from luxtj.contexts.crs.mapping.ratehawk import config, db
from luxtj.contexts.crs.mapping.ratehawk.credentials import load_ratehawk_api
from luxtj.contexts.integration.infrastructure.registry_cache import get_integration_registry


def _backend_root() -> Path:
    # application → mapping → crs → contexts → luxtj → src → luxtj_be
    return Path(__file__).resolve().parents[6]


def _spawn(module: str, *args: str) -> int:
    env = os.environ.copy()
    root = _backend_root()
    src = root / "src"
    env["PYTHONPATH"] = f"{src}{os.pathsep}{env.get('PYTHONPATH', '')}"
    cmd = [sys.executable, "-m", module, *args]
    proc = subprocess.Popen(  # noqa: S603
        cmd,
        cwd=str(root),
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    return proc.pid


def resolve_ratehawk_ready() -> dict[str, Any]:
    registry = get_integration_registry()
    api = registry.resolve_booking_api("ratehawk", sub_module="HOTEL") or registry.resolve_booking_api(
        "ratehawk"
    )
    if api is None or not api.status:
        return {"ready": False, "bookingSourceId": None, "error": "RateHawk inactive"}
    return {"ready": True, "bookingSourceId": str(api.id), "error": ""}


def _serialize_run(run: dict[str, Any] | None) -> dict[str, Any] | None:
    if not run:
        return None
    meta = run.get("meta") or {}
    if isinstance(meta, str):
        meta = json.loads(meta) if meta else {}
    out = {
        "id": run.get("id"),
        "status": run.get("status"),
        "source": run.get("source"),
        "errorMessage": run.get("error_message"),
        "startedAt": run.get("started_at").isoformat() if run.get("started_at") else None,
        "finishedAt": run.get("finished_at").isoformat() if run.get("finished_at") else None,
        "createdAt": run.get("created_at").isoformat() if run.get("created_at") else None,
        "meta": meta,
    }
    for key in (
        "processed_count",
        "matched_count",
        "skipped_count",
        "cities_count",
        "dump_type",
        "zst_path",
    ):
        if key in run:
            camel = "".join(
                w.capitalize() if i else w for i, w in enumerate(key.split("_"))
            )
            out[camel] = run.get(key)
    return out


def region_status() -> dict[str, Any]:
    ready = resolve_ratehawk_ready()
    if not ready["ready"]:
        return {**ready, "mappedCount": 0, "run": None, "hasRegionsZst": False}
    bid = ready["bookingSourceId"]
    storage = config.storage_path()
    zst = storage / "regions.zst"
    return {
        **ready,
        "mappedCount": db.count_region_mappings(bid),
        "run": _serialize_run(db.latest_region_run(bid)),
        "hasRegionsZst": zst.is_file() and zst.stat().st_size > 0,
        "zstBytes": zst.stat().st_size if zst.is_file() else 0,
    }


def region_start() -> dict[str, Any]:
    ready = resolve_ratehawk_ready()
    if not ready["ready"]:
        raise RuntimeError(ready["error"])
    bid = ready["bookingSourceId"]
    # Prefer DB credentials check
    load_ratehawk_api()
    if db.has_active_region_run(bid):
        raise RuntimeError("A region mapping run is already active")
    run_id = db.create_region_run(bid, source="admin")
    pid = _spawn("luxtj.contexts.crs.mapping.ratehawk.region_worker", run_id)
    db.merge_meta(run_id, "region_mapping_runs", {"spawn_pid": pid, "phase": "queued"})
    return {"runId": run_id, "pid": pid}


def region_stop() -> dict[str, Any]:
    ready = resolve_ratehawk_ready()
    if not ready["ready"]:
        raise RuntimeError(ready["error"])
    n = db.cancel_active_region_runs(ready["bookingSourceId"])
    return {"cancelled": n}


def region_wipe() -> dict[str, Any]:
    ready = resolve_ratehawk_ready()
    if not ready["ready"]:
        raise RuntimeError(ready["error"])
    bid = ready["bookingSourceId"]
    cancelled = db.cancel_active_region_runs(bid)
    deleted = db.clear_region_mappings(bid)
    return {"cancelled": cancelled, "deleted": deleted}


def hotel_status() -> dict[str, Any]:
    ready = resolve_ratehawk_ready()
    if not ready["ready"]:
        return {
            **ready,
            "run": None,
            "wipe": None,
            "wiping": False,
            "hasHotelsZst": False,
            "mappedRegions": 0,
        }
    bid = ready["bookingSourceId"]
    storage = config.storage_path()
    zst = storage / "hotels.zst"
    run = db.latest_hotel_run(bid)
    wipe = db.active_wipe_run(bid) or db.latest_wipe_run(bid)
    wipe_serialized = _serialize_run(wipe)
    wiping = bool(wipe and wipe.get("status") in ("pending", "running"))
    serialized = _serialize_run(run)
    meta = (serialized or {}).get("meta") or {}
    if not isinstance(meta, dict):
        meta = {}
    # After wipe, never surface stale dump progress from the previous full run.
    streaming: dict[str, Any] = {}
    if not meta.get("streaming_wiped"):
        streaming = meta.get("streaming") if isinstance(meta.get("streaming"), dict) else {}
    wipe_meta = (wipe_serialized or {}).get("meta") or {}
    return {
        **ready,
        "run": serialized,
        "wipe": wipe_serialized,
        "wiping": wiping,
        "hasHotelsZst": zst.is_file() and zst.stat().st_size > 0,
        "zstBytes": zst.stat().st_size if zst.is_file() else 0,
        "mappedRegions": db.count_region_mappings(bid),
        "stagingHotels": db.count_staging_hotels(str(run["id"])) if run else 0,
        "stagingRooms": db.count_staging_rooms(str(run["id"])) if run else 0,
        "progress": {
            "zstBytesRead": int(streaming.get("zst_bytes_read") or 0),
            "zstBytesTotal": int(streaming.get("zst_bytes_total") or 0),
            "zstNextLine": int(streaming.get("zst_next_line") or 1),
            "zstLinesTotal": int(streaming.get("zst_lines_total") or 0),
            "zstLinesTotalIsEstimate": bool(streaming.get("zst_lines_total_is_estimate")),
            "currentBatch": streaming.get("current_batch") or {},
            "totals": streaming.get("totals") or {},
        },
        "wipeProgress": {
            "phase": wipe_meta.get("wipe_phase") or wipe_meta.get("phase") or None,
            "stats": wipe_meta.get("wipe_stats") or {},
            "message": wipe_meta.get("wipe_message"),
        },
    }


def hotel_start(*, force_new: bool = False) -> dict[str, Any]:
    ready = resolve_ratehawk_ready()
    if not ready["ready"]:
        raise RuntimeError(ready["error"])
    bid = ready["bookingSourceId"]
    load_ratehawk_api()
    if db.has_active_wipe_run(bid):
        raise RuntimeError("CRS wipe is in progress; wait for it to finish")
    if db.count_region_mappings(bid) < 1:
        raise RuntimeError("Map regions first before hotel stream")

    if not force_new:
        resumable = db.find_resumable_full_stream_run(bid)
        if resumable:
            pid = _spawn(
                "luxtj.contexts.crs.mapping.ratehawk.stream_batch_worker",
                "resume",
                resumable,
            )
            return {"runId": resumable, "pid": pid, "resumed": True}

    if db.has_active_parent_run(bid):
        raise RuntimeError("A hotel mapping run is already active")

    run_id = db.create_parent_run(bid, source="admin")
    pid = _spawn(
        "luxtj.contexts.crs.mapping.ratehawk.stream_batch_worker",
        "resume",
        run_id,
    )
    return {"runId": run_id, "pid": pid, "resumed": False}


def hotel_stop() -> dict[str, Any]:
    ready = resolve_ratehawk_ready()
    if not ready["ready"]:
        raise RuntimeError(ready["error"])
    n = db.cancel_active_hotel_runs(ready["bookingSourceId"])
    return {"cancelled": n}


def _mark_full_runs_streaming_wiped(booking_source_id: str, *, limit: int = 50) -> int:
    """Invalidate stream checkpoints and zero progress so the UI resets after wipe."""
    from luxtj.contexts.crs.mapping.ratehawk import streaming_state

    return streaming_state.mark_runs_streaming_wiped(booking_source_id, limit=limit)


def hotel_wipe_restart() -> dict[str, Any]:
    """Cancel active mapping, then wipe CRS/staging in a background worker.

    Returns immediately so the API/event loop does not hang on large deletes.
    """
    ready = resolve_ratehawk_ready()
    if not ready["ready"]:
        raise RuntimeError(ready["error"])
    bid = ready["bookingSourceId"]

    active_wipe = db.active_wipe_run(bid)
    if active_wipe:
        alive = _wipe_worker_alive(active_wipe)
        if alive:
            killed = _kill_stale_stream_workers(bid, exclude_run_id=str(active_wipe["id"]))
            return {
                "runId": active_wipe["id"],
                "pid": None,
                "cancelled": 0,
                "async": True,
                "alreadyRunning": True,
                "killedStalePids": killed,
            }
        # Orphan wipe row (worker died while holding locks) — mark failed and continue.
        db.update_run(
            str(active_wipe["id"]),
            status="failed",
            finished_at=db._utc_now(),
            error_message="Wipe worker process died; restarted",
        )
        db.merge_meta(
            str(active_wipe["id"]),
            "hotel_mapping_runs",
            {
                "wipe_phase": "failed",
                "phase": "failed",
                "stream_phase": "wipe_failed",
            },
        )

    cancelled = db.cancel_active_hotel_runs(bid)
    killed = _kill_stale_stream_workers(bid)
    _mark_full_runs_streaming_wiped(bid)

    run_id = db.create_wipe_run(bid, source="admin")
    pid = _spawn("luxtj.contexts.crs.mapping.ratehawk.wipe_worker", run_id)
    db.merge_meta(
        run_id,
        "hotel_mapping_runs",
        {"spawn_pid": pid, "process_pid": pid, "wipe_phase": "queued", "phase": "wiping"},
    )
    return {
        "runId": run_id,
        "pid": pid,
        "cancelled": cancelled,
        "async": True,
        "alreadyRunning": False,
        "killedStalePids": killed,
        "keptHotelsZst": (config.storage_path() / "hotels.zst").is_file(),
    }


def _wipe_worker_alive(wipe: dict[str, Any]) -> bool:
    from luxtj.contexts.crs.mapping.ratehawk import process_kill

    meta = wipe.get("meta") or {}
    if isinstance(meta, str):
        meta = json.loads(meta) if meta else {}
    pids = process_kill.pids_from_meta(meta)
    if pids:
        for pid in pids:
            try:
                os.kill(pid, 0)
                return True
            except ProcessLookupError:
                continue
            except OSError:
                return True
        return False

    # No pid recorded yet — only treat as alive if the run was just queued.
    created = wipe.get("created_at")
    if wipe.get("status") == "pending" and created is not None:
        if getattr(created, "tzinfo", None) is None:
            created = created.replace(tzinfo=db._utc_now().tzinfo)
        age = (db._utc_now() - created).total_seconds()
        return age < 20
    return False


def _kill_stale_stream_workers(
    booking_source_id: str,
    *,
    exclude_run_id: str | None = None,
) -> list[int]:
    """Best-effort kill of leftover stream worker PIDs from recent runs."""
    from luxtj.contexts.crs.mapping.ratehawk import process_kill

    with db.db_cursor() as (_, cur):
        cur.execute(
            """
            SELECT id, meta FROM hotel_mapping_runs
            WHERE booking_source_id = %s
              AND parent_run_id IS NULL
              AND dump_type = 'full'
            ORDER BY created_at DESC
            LIMIT 30
            """,
            (booking_source_id,),
        )
        rows = cur.fetchall()
    pids: list[int] = []
    for rid, meta_raw in rows:
        if exclude_run_id and str(rid) == str(exclude_run_id):
            continue
        meta = meta_raw if isinstance(meta_raw, dict) else (json.loads(meta_raw) if meta_raw else {})
        pids.extend(process_kill.pids_from_meta(meta))
    return process_kill.kill_pids(pids)
