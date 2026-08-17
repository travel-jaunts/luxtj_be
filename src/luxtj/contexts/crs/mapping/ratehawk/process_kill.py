"""Terminate RateHawk mapping worker processes (stream / wipe)."""

from __future__ import annotations

import os
import signal
import time
from typing import Any


def pids_from_meta(meta: dict[str, Any] | None) -> list[int]:
    if not meta:
        return []
    out: list[int] = []
    for key in ("process_pid", "spawn_pid"):
        raw = meta.get(key)
        if raw is None or raw == "":
            continue
        try:
            pid = int(raw)
        except TypeError, ValueError:
            continue
        if pid > 1:
            out.append(pid)
    # Preserve order, unique
    seen: set[int] = set()
    uniq: list[int] = []
    for pid in out:
        if pid not in seen:
            seen.add(pid)
            uniq.append(pid)
    return uniq


def _signal_pid(pid: int, sig: signal.Signals) -> bool:
    try:
        os.killpg(pid, sig)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        pass
    except OSError:
        pass
    try:
        os.kill(pid, sig)
        return True
    except ProcessLookupError:
        return False
    except OSError:
        return False


def _alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False


def kill_pids(pids: list[int], *, wait_s: float = 1.0) -> list[int]:
    """SIGTERM then SIGKILL worker PIDs (process-group aware). Returns killed PIDs."""
    targets = sorted({int(p) for p in pids if int(p) > 1 and int(p) != os.getpid()})
    if not targets:
        return []

    signaled: list[int] = []
    for pid in targets:
        if _signal_pid(pid, signal.SIGTERM):
            signaled.append(pid)

    deadline = time.monotonic() + max(0.1, wait_s)
    while time.monotonic() < deadline:
        if not any(_alive(pid) for pid in signaled):
            break
        time.sleep(0.1)

    for pid in signaled:
        if _alive(pid):
            _signal_pid(pid, signal.SIGKILL)

    return signaled
