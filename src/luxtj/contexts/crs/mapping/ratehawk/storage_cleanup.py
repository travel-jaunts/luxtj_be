"""Delete RateHawk dump / batch files after a mapping run finishes successfully."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from . import config


def _is_under(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def _unlink(path: Path, removed: list[str]) -> None:
    if not path.is_file():
        return
    path.unlink(missing_ok=True)
    removed.append(str(path))


def cleanup_hotel_run_files(
    run_id: str,
    *,
    zst_path: str | Path | None = None,
    delete_dump: bool = True,
) -> dict[str, Any]:
    """Remove per-run batch JSONL and (optionally) the hotels.zst dump.

    Only deletes files under the RateHawk storage directory.
    """
    storage = config.storage_path()
    storage.mkdir(parents=True, exist_ok=True)
    removed: list[str] = []

    for path in storage.glob(f"run_{run_id}_*"):
        if path.is_file():
            _unlink(path, removed)

    dump_removed = False
    if delete_dump:
        dump = Path(zst_path) if zst_path else (storage / "hotels.zst")
        if dump.is_file() and _is_under(dump, storage):
            _unlink(dump, removed)
            dump_removed = True

    return {
        "removedFiles": removed,
        "removedCount": len(removed),
        "dumpRemoved": dump_removed,
        "storagePath": str(storage),
    }


def cleanup_region_run_files(
    *,
    zst_path: str | Path | None = None,
    delete_dump: bool = True,
) -> dict[str, Any]:
    """Remove regions.zst after a successful region mapping run."""
    storage = config.storage_path()
    storage.mkdir(parents=True, exist_ok=True)
    removed: list[str] = []
    dump_removed = False

    if delete_dump:
        dump = Path(zst_path) if zst_path else (storage / "regions.zst")
        if dump.is_file() and _is_under(dump, storage):
            _unlink(dump, removed)
            dump_removed = True

    return {
        "removedFiles": removed,
        "removedCount": len(removed),
        "dumpRemoved": dump_removed,
        "storagePath": str(storage),
        "pid": os.getpid(),
    }
