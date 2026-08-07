"""CLI entry for full RateHawk hotel stream mapping."""

from __future__ import annotations

import argparse
import os
import sys

from . import config, db, stream_mapper, streaming_state
from .credentials import load_ratehawk_api


def cmd_start(*, force_new: bool = False) -> int:
    creds = load_ratehawk_api()
    booking_source_id = str(creds["booking_source_id"])

    if not force_new:
        resumable_id = db.find_resumable_full_stream_run(booking_source_id)
        if resumable_id:
            print(f"Resuming incomplete run #{resumable_id}", flush=True)
            return cmd_resume(resumable_id)

    if db.has_active_parent_run(booking_source_id):
        print("A full hotel mapping run is already active.", file=sys.stderr)
        return 1

    run_id = db.create_parent_run(booking_source_id, source="admin")
    print(f"Created run #{run_id}", flush=True)
    db.update_run(run_id, status="running", started_at=db._utc_now())

    mapper = stream_mapper.StreamMapper(run_id, booking_source_id)
    try:
        zst_path = mapper.prepare_download()
        mapper.init_streaming(zst_path)
        mapper.run_until_complete()
    except Exception as exc:
        stream_mapper.fail_run(run_id, str(exc))
        raise

    run = db.fetch_run(run_id)
    print(f"Run #{run_id} finished with status: {(run or {}).get('status')}", flush=True)
    return 0 if (run or {}).get("status") == "completed" else 1


def cmd_resume(run_id: str) -> int:
    run = db.fetch_run(run_id)
    if not run or run.get("parent_run_id"):
        print(f"Parent run {run_id} not found.", file=sys.stderr)
        return 1
    if run.get("status") == "completed":
        print(f"Run #{run_id} is already completed.")
        return 0

    creds = load_ratehawk_api()
    booking_source_id = str(creds["booking_source_id"])
    db.update_run(run_id, status="running", finished_at=None, error_message=None)
    db.merge_meta(
        run_id,
        "hotel_mapping_runs",
        {
            "phase": "streaming",
            "engine": "python",
            "mode": "python_stream",
            "process_pid": os.getpid(),
            "resumed_at": db._iso_now(),
        },
    )

    mapper = stream_mapper.StreamMapper(run_id, booking_source_id)
    try:
        zst_path = str(run.get("zst_path") or (config.storage_path() / "hotels.zst"))
        if not run.get("zst_path") or not __import__("pathlib").Path(zst_path).is_file():
            zst_path = mapper.prepare_download()
        state = streaming_state.load(run_id)
        if not state.get("zst_path"):
            mapper.init_streaming(zst_path)
        mapper.run_until_complete()
    except Exception as exc:
        stream_mapper.fail_run(run_id, str(exc))
        raise

    run = db.fetch_run(run_id)
    return 0 if (run or {}).get("status") == "completed" else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="RateHawk hotel stream worker")
    parser.add_argument("command", choices=["start", "resume"])
    parser.add_argument("run_id", nargs="?", default="")
    parser.add_argument("--force-new", action="store_true")
    args = parser.parse_args()
    if args.command == "start":
        return cmd_start(force_new=args.force_new)
    if not args.run_id:
        print("resume requires run_id", file=sys.stderr)
        return 1
    return cmd_resume(args.run_id)


if __name__ == "__main__":
    raise SystemExit(main())
