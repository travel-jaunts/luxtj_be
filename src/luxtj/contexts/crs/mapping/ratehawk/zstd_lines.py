from __future__ import annotations

from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

import zstandard as zstd

ProgressCb = Callable[[int, int], None]


def iter_zst_lines(zst_path: str | Path) -> Iterator[str]:
    """Yield decompressed UTF-8 lines from a .zst JSONL dump without writing a full extract."""
    yield from iter_zst_lines_range(zst_path, start_line=1, max_lines=None)


def iter_zst_lines_range(
    zst_path: str | Path,
    start_line: int = 1,
    max_lines: int | None = None,
    *,
    on_compressed_progress: ProgressCb | None = None,
) -> Iterator[str]:
    """Yield up to max_lines decompressed lines, starting at start_line (1-based).

    ``on_compressed_progress(compressed_pos, compressed_total)`` is called as the
    underlying .zst file is read (best-effort byte offset into the compressed file).
    """
    if start_line < 1:
        start_line = 1
    path = Path(zst_path)
    if not path.is_file():
        raise FileNotFoundError(f"zst file not found: {path}")

    compressed_total = int(path.stat().st_size)
    dctx = zstd.ZstdDecompressor()
    line_no = 0
    yielded = 0
    with path.open("rb") as fh, dctx.stream_reader(fh) as reader:
        buffer = b""

        def _emit_progress() -> None:
            if on_compressed_progress is None:
                return
            try:
                pos = int(fh.tell())
            except Exception:  # noqa: BLE001
                return
            on_compressed_progress(pos, compressed_total)

        if on_compressed_progress is not None:
            on_compressed_progress(0, compressed_total)

        while True:
            if max_lines is not None and yielded >= max_lines:
                break
            chunk = reader.read(1024 * 1024)
            if not chunk:
                break
            _emit_progress()
            buffer += chunk
            while b"\n" in buffer:
                line, buffer = buffer.split(b"\n", 1)
                text = line.decode("utf-8", errors="replace").strip()
                if not text:
                    continue
                line_no += 1
                if line_no < start_line:
                    continue
                yield text
                yielded += 1
                if max_lines is not None and yielded >= max_lines:
                    _emit_progress()
                    return
        if buffer.strip() and (max_lines is None or yielded < max_lines):
            line_no += 1
            if line_no >= start_line:
                text = buffer.decode("utf-8", errors="replace").strip()
                if text:
                    yield text
        _emit_progress()


class ZstLineReader:
    """Sequential line reader over a .zst JSONL dump that persists across batches.

    The zstd stream stays open between reads, so consecutive batch extracts
    continue forward in O(batch) instead of re-decompressing the whole file to
    skip already-processed lines (which made extract O(n²) across a run).
    Seeking backwards reopens the stream (one full re-scan — resume only).
    Not thread-safe: callers must serialize access with their own lock.
    """

    def __init__(self, zst_path: str | Path, *, on_compressed_progress: ProgressCb | None = None) -> None:
        self.path = Path(zst_path)
        if not self.path.is_file():
            raise FileNotFoundError(f"zst file not found: {self.path}")
        self.on_compressed_progress = on_compressed_progress
        self.compressed_total = int(self.path.stat().st_size)
        self.next_line = 1  # 1-based number of the next line to be returned
        self._fh: Any = None
        self._reader: Any = None
        self._buffer = b""
        self._eof = False

    def _open(self) -> None:
        self.close()
        self._fh = self.path.open("rb")
        self._reader = zstd.ZstdDecompressor().stream_reader(self._fh)
        self._buffer = b""
        self._eof = False
        self.next_line = 1

    def close(self) -> None:
        for handle in (self._reader, self._fh):
            if handle is not None:
                try:
                    handle.close()
                except Exception:  # noqa: BLE001
                    pass
        self._reader = None
        self._fh = None
        self._buffer = b""
        self._eof = False

    def _emit_progress(self) -> None:
        if self.on_compressed_progress is None or self._fh is None:
            return
        try:
            pos = int(self._fh.tell())
        except Exception:  # noqa: BLE001
            return
        self.on_compressed_progress(pos, self.compressed_total)

    def _next_raw_line(self) -> str | None:
        """Next non-empty decompressed line, or None at EOF."""
        while True:
            idx = self._buffer.find(b"\n")
            if idx >= 0:
                line, self._buffer = self._buffer[:idx], self._buffer[idx + 1 :]
                text = line.decode("utf-8", errors="replace").strip()
                if text:
                    return text
                continue
            if self._eof:
                if self._buffer.strip():
                    text = self._buffer.decode("utf-8", errors="replace").strip()
                    self._buffer = b""
                    if text:
                        return text
                return None
            chunk = self._reader.read(1024 * 1024)
            if not chunk:
                self._eof = True
                continue
            self._emit_progress()
            self._buffer += chunk

    def seek_line(self, start_line: int) -> None:
        if start_line < 1:
            start_line = 1
        if self._fh is None or start_line < self.next_line:
            self._open()
        while self.next_line < start_line:
            if self._next_raw_line() is None:
                break
            self.next_line += 1

    def read_lines(self, start_line: int, max_lines: int | None) -> Iterator[str]:
        self.seek_line(start_line)
        yielded = 0
        while max_lines is None or yielded < max_lines:
            line = self._next_raw_line()
            if line is None:
                break
            self.next_line += 1
            yielded += 1
            yield line
        self._emit_progress()


def count_zst_lines(zst_path: str | Path) -> int:
    total = 0
    for _ in iter_zst_lines(zst_path):
        total += 1
    return total


def zst_compressed_size(zst_path: str | Path) -> int:
    path = Path(zst_path)
    return int(path.stat().st_size) if path.is_file() else 0
