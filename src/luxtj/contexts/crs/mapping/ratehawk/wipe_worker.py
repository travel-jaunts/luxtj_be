"""CLI: batched wipe of RateHawk CRS + staging for one mapping wipe run."""

from __future__ import annotations

import argparse
import os
import sys
from typing import Any

from . import config, crs_reset, db, streaming_state


class WipeCancelled(Exception):
    """Raised when the wipe run is cancelled from the admin UI."""


def _clear_batch_files() -> int:
    storage = config.storage_path()
    removed = 0
    if storage.is_dir():
        for path in storage.glob("run_*_current_batch.jsonl"):
            path.unlink(missing_ok=True)
            removed += 1
    return removed


def _is_cancelled(run_id: str) -> bool:
    run = db.fetch_run(run_id)
    if not run:
        return True
    if run.get("status") == "cancelled":
        return True
    meta = run.get("meta") or {}
    if isinstance(meta, str):
        import json

        meta = json.loads(meta) if meta else {}
    return bool(meta.get("cancelled"))


def _publish(run_id: str, phase: str, stats: dict[str, Any], **extra: Any) -> None:
    if _is_cancelled(run_id):
        raise WipeCancelled(f"Wipe run {run_id} cancelled")
    db.merge_meta(
        run_id,
        "hotel_mapping_runs",
        {
            "phase": "wiping",
            "stream_phase": "wiping",
            "mode": "wipe",
            "wipe_phase": phase,
            "wipe_stats": stats,
            "process_pid": os.getpid(),
            "heartbeat_at": db._iso_now(),
            **extra,
        },
    )


def run_wipe(run_id: str) -> int:
    run = db.fetch_run(run_id)
    if not run:
        print(f"Wipe run {run_id} not found", file=sys.stderr)
        return 1
    if run.get("parent_run_id"):
        print(f"Run {run_id} is not a parent wipe run", file=sys.stderr)
        return 1
    if run.get("dump_type") != "wipe":
        print(f"Run {run_id} dump_type is not wipe", file=sys.stderr)
        return 1

    booking_source_id = str(run["booking_source_id"])
    db.update_run(
        run_id,
        status="running",
        started_at=db._utc_now(),
        finished_at=None,
        error_message=None,
    )
    _publish(run_id, "start", {})

    def on_progress(phase: str, stats: dict[str, Any]) -> None:
        _publish(run_id, phase, dict(stats))

    try:
        result = crs_reset.reset_supplier_crs(
            booking_source_id,
            on_progress=on_progress,
        )
        if _is_cancelled(run_id):
            raise WipeCancelled(f"Wipe run {run_id} cancelled")

        removed = _clear_batch_files()
        # Ensure mapping page progress is 0 after CRS data is gone.
        streaming_state.mark_runs_streaming_wiped(booking_source_id)
        db.merge_meta(
            run_id,
            "hotel_mapping_runs",
            {
                "phase": "wiped",
                "stream_phase": "wiped",
                "mode": "wipe",
                "wipe_phase": "done",
                "wipe_stats": result.get("stats") or {},
                "wipe_message": result.get("message"),
                "removedBatchFiles": removed,
                "keptHotelsZst": (config.storage_path() / "hotels.zst").is_file(),
                "heartbeat_at": db._iso_now(),
            },
        )
        db.update_run(
            run_id,
            status="completed",
            finished_at=db._utc_now(),
            error_message=None,
        )
        print(f"Wipe run #{run_id} completed: {result.get('message')}", flush=True)
        return 0
    except WipeCancelled:
        db.merge_meta(
            run_id,
            "hotel_mapping_runs",
            {
                "phase": "cancelled",
                "stream_phase": "wipe_cancelled",
                "mode": "wipe",
                "wipe_phase": "cancelled",
                "heartbeat_at": db._iso_now(),
            },
        )
        # Status already set to cancelled by cancel_active_hotel_runs; ensure finished_at.
        run_now = db.fetch_run(run_id) or {}
        if run_now.get("status") != "cancelled":
            db.update_run(run_id, status="cancelled", finished_at=db._utc_now())
        elif not run_now.get("finished_at"):
            db.update_run(run_id, finished_at=db._utc_now())
        print(f"Wipe run #{run_id} cancelled", flush=True)
        return 0
    except Exception as exc:
        db.merge_meta(
            run_id,
            "hotel_mapping_runs",
            {
                "phase": "failed",
                "stream_phase": "wipe_failed",
                "mode": "wipe",
                "wipe_phase": "failed",
                "heartbeat_at": db._iso_now(),
            },
        )
        db.update_run(
            run_id,
            status="failed",
            finished_at=db._utc_now(),
            error_message=str(exc),
        )
        print(f"Wipe run #{run_id} failed: {exc}", file=sys.stderr, flush=True)
        return 1


def main() -> int:
    parser = argparse.ArgumentParser(description="RateHawk CRS wipe worker")
    parser.add_argument("run_id")
    args = parser.parse_args()
    return run_wipe(args.run_id)


if __name__ == "__main__":
    raise SystemExit(main())
