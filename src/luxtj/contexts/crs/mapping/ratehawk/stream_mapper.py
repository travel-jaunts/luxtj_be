"""Full hotel dump stream: download → extract/stage → promote with DB checkpoints."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from . import api_client, config, crs_promote, db, storage_cleanup, streaming_state
from .parser import parse_for_staging
from .zstd_lines import ZstLineReader, count_zst_lines, zst_compressed_size


def _log(msg: str) -> None:
    print(f"[ratehawk-hotel] {msg}", flush=True)


def _hotel_region_code(hotel: dict[str, Any]) -> str:
    """RateHawk hotel dump nests the id under region.id (not top-level region_id)."""
    region = hotel.get("region") if isinstance(hotel.get("region"), dict) else {}
    raw = region.get("id")
    if raw is None or raw == "":
        raw = hotel.get("region_id") or hotel.get("regionId")
    return str(raw).strip() if raw is not None and str(raw).strip() else ""


def _lines_total_from_state(state: dict[str, Any]) -> int:
    return int(state.get("zst_lines_total") or 0)


def _batch_target(*, remaining: int, batch_cap: int) -> int:
    """Use remaining when smaller than cap; otherwise cap; last batch = remaining."""
    if remaining <= 0:
        return 0
    return min(batch_cap, remaining)


class StreamMapper:
    def __init__(self, run_id: str, booking_source_id: str) -> None:
        self.run_id = run_id
        self.booking_source_id = booking_source_id
        self.storage = config.storage_path()
        self.storage.mkdir(parents=True, exist_ok=True)
        self._zst_reader: ZstLineReader | None = None
        self._region_map: dict[str, str] | None = None

    def batch_jsonl_path(self) -> Path:
        return self.storage / f"run_{self.run_id}_current_batch.jsonl"

    def run_until_complete(self) -> None:
        _log(f"run #{self.run_id} starting pipeline loop")
        while True:
            run = db.fetch_run(self.run_id)
            if not run or db.is_cancelled(run):
                _log(f"run #{self.run_id} cancelled or missing — stop")
                return

            state = streaming_state.load(self.run_id)
            batch = state.get("current_batch") or {}
            phase = str(batch.get("phase") or "extract")
            _log(
                f"run #{self.run_id} phase={phase} "
                f"batch=#{int(batch.get('index') or 0)} "
                f"line={int(state.get('zst_next_line') or 1)}"
            )

            if phase == "complete":
                self._finalize()
                return

            if phase == "extract":
                if not self._extract_batch(state):
                    return
                continue

            if phase == "stage":
                self._stage_batch()
                continue

            if phase in ("hotels", "rooms", "promote"):
                self._promote_pipeline(state)
                continue

            if phase == "cleanup":
                self._cleanup_batch(state)
                continue

            streaming_state.save(self.run_id, {"current_batch": streaming_state.empty_batch(0)})

    def prepare_download(self) -> str:
        zst_path = str(self.storage / "hotels.zst")
        run = db.fetch_run(self.run_id)
        if run and run.get("zst_path") and Path(str(run["zst_path"])).is_file():
            zst_path = str(run["zst_path"])

        db.update_run(
            self.run_id,
            status="running",
            meta=db.merge_meta(
                self.run_id,
                "hotel_mapping_runs",
                {
                    "phase": "downloading",
                    "mode": "python_stream",
                    "engine": "python",
                    "process_pid": os.getpid(),
                },
            ),
        )

        if not Path(zst_path).is_file() or Path(zst_path).stat().st_size < 1:
            _log(f"run #{self.run_id} downloading hotels dump → {zst_path}")
            dump_url = api_client.fetch_full_hotel_dump_url()
            db.update_run(self.run_id, dump_url=dump_url, zst_path=zst_path)

            def on_progress(downloaded: int, total: int) -> None:
                db.merge_meta(
                    self.run_id,
                    "hotel_mapping_runs",
                    {
                        "download_bytes": downloaded,
                        "download_total": total,
                        "heartbeat_at": db._iso_now(),
                    },
                )

            api_client.download_to_file(dump_url, zst_path, on_progress=on_progress)
            _log(f"run #{self.run_id} download complete")
        else:
            _log(f"run #{self.run_id} reusing existing dump {zst_path}")

        estimate = config.stream_total_lines_estimate()
        streaming_state.save(
            self.run_id,
            {
                "zst_path": zst_path,
                "zst_lines_total_estimate": estimate if estimate > 0 else None,
                "zst_bytes_total": zst_compressed_size(zst_path),
                "zst_bytes_read": 0,
                "current_batch": streaming_state.empty_batch(0),
            },
        )
        db.update_run(self.run_id, zst_path=zst_path)
        db.merge_meta(
            self.run_id,
            "hotel_mapping_runs",
            {"phase": "streaming", "stream_phase": "extract"},
        )
        return zst_path

    def init_streaming(self, zst_path: str) -> None:
        estimate = config.stream_total_lines_estimate()
        streaming_state.save(
            self.run_id,
            {
                "zst_path": zst_path,
                "zst_next_line": 1,
                "zst_lines_total_estimate": estimate if estimate > 0 else None,
                "zst_bytes_total": zst_compressed_size(zst_path),
                "zst_bytes_read": 0,
                "current_batch": streaming_state.empty_batch(0),
            },
        )

    def _region_lookup(self) -> dict[str, str]:
        if self._region_map is None:
            self._region_map = db.load_region_map(self.booking_source_id)
        return self._region_map

    def _reader(self, zst_path: str) -> ZstLineReader:
        if self._zst_reader is None:

            def on_progress(pos: int, total: int) -> None:
                state = streaming_state.load(self.run_id)
                prev = int(state.get("zst_bytes_read") or 0)
                if pos >= prev:
                    streaming_state.save(
                        self.run_id,
                        {"zst_bytes_read": pos, "zst_bytes_total": total},
                    )

            self._zst_reader = ZstLineReader(zst_path, on_compressed_progress=on_progress)
        return self._zst_reader

    def _ensure_lines_total(self, state: dict[str, Any], zst_path: str) -> int:
        known = _lines_total_from_state(state)
        if known > 0:
            return known

        estimate = (
            int(state.get("zst_lines_total_estimate") or 0) or config.stream_total_lines_estimate()
        )
        if estimate > 0:
            streaming_state.save(
                self.run_id,
                {
                    "zst_lines_total": estimate,
                    "zst_lines_total_estimate": estimate,
                    "zst_lines_total_is_estimate": True,
                },
            )
            _log(f"run #{self.run_id} using line estimate={estimate}")
            return estimate

        _log(f"run #{self.run_id} counting dump lines (one-time)…")
        db.merge_meta(
            self.run_id,
            "hotel_mapping_runs",
            {"stream_phase": "counting", "phase": "streaming"},
        )
        total = count_zst_lines(zst_path)
        streaming_state.save(
            self.run_id,
            {
                "zst_lines_total": total,
                "zst_lines_total_is_estimate": False,
            },
        )
        db.merge_meta(self.run_id, "hotel_mapping_runs", {"stream_phase": "extract"})
        _log(f"run #{self.run_id} dump lines total={total}")
        return total

    def _extract_batch(self, state: dict[str, Any]) -> bool:
        zst_path = str(state.get("zst_path") or "")
        if not zst_path or not Path(zst_path).is_file():
            fail_run(self.run_id, "hotels.zst missing")
            return False

        lines_total = self._ensure_lines_total(state, zst_path)
        # reload after possible count write
        state = streaming_state.load(self.run_id)
        start_line = int(state.get("zst_next_line") or 1)
        remaining = max(0, lines_total - (start_line - 1))
        batch_cap = config.stream_extract_lines()
        target = _batch_target(remaining=remaining, batch_cap=batch_cap)
        batch_index = int((state.get("current_batch") or {}).get("index") or 0)

        if target <= 0:
            streaming_state.save(
                self.run_id,
                {
                    "current_batch": {
                        "index": batch_index,
                        "phase": "complete",
                        "extract_done": 0,
                        "extract_target": 0,
                        "batch_lines_done": 0,
                        "batch_size_cap": batch_cap,
                    }
                },
            )
            return True

        region_map = self._region_lookup()
        path = self.batch_jsonl_path()
        path.parent.mkdir(parents=True, exist_ok=True)

        streaming_state.save(
            self.run_id,
            {
                "current_batch": {
                    "index": batch_index,
                    "phase": "extract",
                    "zst_start_line": start_line,
                    "extract_target": target,
                    "extract_done": 0,
                    "batch_lines_done": 0,
                    "batch_size_cap": batch_cap,
                }
            },
        )
        _log(
            f"run #{self.run_id} extract batch=#{batch_index} "
            f"start={start_line} target={target} remaining={remaining} cap={batch_cap}"
        )

        extracted = 0
        skipped = 0
        lines_read = 0
        reader = self._reader(zst_path)
        with path.open("w", encoding="utf-8") as out:
            for line in reader.read_lines(start_line, target):
                lines_read += 1
                if lines_read % 500 == 0:
                    run = db.fetch_run(self.run_id)
                    if db.is_cancelled(run):
                        return False
                    streaming_state.save(
                        self.run_id,
                        {
                            "current_batch": {
                                "index": batch_index,
                                "phase": "extract",
                                "extract_done": extracted,
                                "extract_target": target,
                                "batch_lines_done": lines_read,
                                "batch_size_cap": batch_cap,
                                "zst_start_line": start_line,
                            }
                        },
                    )
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    skipped += 1
                    continue
                if not isinstance(obj, dict):
                    skipped += 1
                    continue
                region_code = _hotel_region_code(obj)
                region_id = region_map.get(region_code) if region_code else None
                if not region_id:
                    skipped += 1
                    continue
                parsed = parse_for_staging(obj, region_id)
                if not parsed:
                    skipped += 1
                    continue
                out.write(json.dumps(parsed, ensure_ascii=False) + "\n")
                extracted += 1

        next_line = reader.next_line
        # If estimate was high and we hit EOF early, correct the total.
        hit_eof = bool(getattr(reader, "_eof", False)) and lines_read < target
        if hit_eof:
            actual_total = start_line - 1 + lines_read
            streaming_state.save(
                self.run_id,
                {
                    "zst_lines_total": actual_total,
                    "zst_lines_total_is_estimate": False,
                },
            )
            lines_total = actual_total
            target = max(lines_read, 1) if lines_read else 0

        if lines_read == 0:
            streaming_state.save(
                self.run_id,
                {
                    "zst_next_line": next_line,
                    "current_batch": {
                        "index": batch_index,
                        "phase": "complete",
                        "extract_done": 0,
                        "extract_target": 0,
                        "batch_lines_done": 0,
                        "batch_size_cap": batch_cap,
                    },
                },
            )
            return True

        # Batch progress denominator = actual lines this batch (last batch shrinks)
        batch_target = lines_read if lines_read < target or hit_eof else target

        streaming_state.save(
            self.run_id,
            {
                "zst_next_line": next_line,
                "zst_lines_total": lines_total,
                "current_batch": {
                    "index": batch_index,
                    "phase": "stage" if extracted > 0 else "cleanup",
                    "extract_done": extracted,
                    "extract_target": batch_target,
                    "batch_lines_done": lines_read,
                    "batch_size_cap": batch_cap,
                    "zst_start_line": start_line,
                    "hotels_staged": 0,
                    "rooms_staged": 0,
                },
                "totals": {
                    "processed_lines": int((state.get("totals") or {}).get("processed_lines") or 0)
                    + lines_read,
                    "skipped": int((state.get("totals") or {}).get("skipped") or 0) + skipped,
                },
            },
        )
        db.merge_meta(
            self.run_id,
            "hotel_mapping_runs",
            {"stream_phase": "stage" if extracted > 0 else "cleanup"},
        )
        if extracted == 0 and next_line > start_line:
            # progressed but nothing staged (all skipped) — continue extract
            streaming_state.save(
                self.run_id,
                {
                    "current_batch": {
                        "index": batch_index + 1,
                        "phase": "extract",
                        "extract_done": 0,
                        "extract_target": 0,
                        "batch_lines_done": 0,
                        "batch_size_cap": batch_cap,
                    }
                },
            )
        return True

    def _stage_batch(self) -> None:
        path = self.batch_jsonl_path()
        if not path.is_file():
            streaming_state.save(self.run_id, {"current_batch": {"phase": "extract"}})
            return
        hotel_batch: list[dict[str, Any]] = []
        room_batch: list[dict[str, Any]] = []
        hotels_staged = rooms_staged = 0
        flush_size = config.stream_stage_batch()
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    parsed = json.loads(line)
                except json.JSONDecodeError:
                    continue
                staging = parsed.get("staging") if isinstance(parsed, dict) else None
                rooms = parsed.get("rooms") if isinstance(parsed, dict) else None
                if not isinstance(staging, dict):
                    continue
                hotel_batch.append(staging)
                if isinstance(rooms, list):
                    room_batch.extend(rooms)
                if len(hotel_batch) >= flush_size:
                    db.flush_staging(self.run_id, 0, hotel_batch, room_batch)
                    hotels_staged += len(hotel_batch)
                    rooms_staged += len(room_batch)
                    hotel_batch = []
                    room_batch = []
        if hotel_batch or room_batch:
            db.flush_staging(self.run_id, 0, hotel_batch, room_batch)
            hotels_staged += len(hotel_batch)
            rooms_staged += len(room_batch)

        streaming_state.save(
            self.run_id,
            {
                "current_batch": {
                    "phase": "promote",
                    "hotels_staged": hotels_staged,
                    "rooms_staged": rooms_staged,
                    "hotels_promoted": 0,
                    "rooms_promoted": 0,
                }
            },
        )
        db.merge_meta(self.run_id, "hotel_mapping_runs", {"stream_phase": "promote"})

    def _promote_pipeline(self, state: dict[str, Any]) -> None:
        """2 hotel + 2 room workers with SKIP LOCKED claims (Teenva parity)."""
        import threading
        import time
        from concurrent.futures import ThreadPoolExecutor

        staged = int(
            (state.get("current_batch") or {}).get("hotels_staged")
            or db.count_staging_hotels(self.run_id)
        )
        left_hotels = crs_promote.count_unpromoted_hotels(self.run_id)
        left_rooms = crs_promote.count_pending_room_hotels(self.run_id)
        if staged > 0 and left_hotels <= 0 and left_rooms <= 0:
            _log(f"run #{self.run_id} promote already done → cleanup")
            streaming_state.save(self.run_id, {"current_batch": {"phase": "cleanup"}})
            db.merge_meta(self.run_id, "hotel_mapping_runs", {"stream_phase": "cleanup"})
            return

        hotel_workers = max(1, int(config.promote_hotel_workers()))
        room_workers = max(1, int(config.promote_room_workers()))
        state_lock = threading.Lock()
        totals_box = {
            "inserted": int((state.get("totals") or {}).get("inserted_hotels") or 0),
            "rooms_synced": int((state.get("totals") or {}).get("rooms_synced") or 0),
        }
        stop_status = threading.Event()
        errors: list[BaseException] = []

        def publish() -> None:
            hotels_promoted = crs_promote.count_hotels_promoted(self.run_id)
            rooms_promoted = crs_promote.count_rooms_promoted(self.run_id)
            with state_lock:
                streaming_state.save(
                    self.run_id,
                    {
                        "totals": {
                            "inserted_hotels": totals_box["inserted"],
                            "rooms_synced": totals_box["rooms_synced"],
                        },
                        "current_batch": {
                            "hotels_staged": staged,
                            "hotels_promoted": hotels_promoted,
                            "rooms_promoted": rooms_promoted,
                            "phase": "promote",
                        },
                    },
                )
                db.merge_meta(
                    self.run_id,
                    "hotel_mapping_runs",
                    {"stream_phase": "promote", "heartbeat_at": db._iso_now()},
                )
            _log(
                f"run #{self.run_id} STATUS hotels={hotels_promoted}/{staged} "
                f"rooms={rooms_promoted}/{staged} workers=H{hotel_workers}/R{room_workers}"
            )

        def status_worker() -> None:
            while not stop_status.wait(5.0):
                try:
                    publish()
                except Exception as exc:
                    _log(f"run #{self.run_id} status publish error: {exc}")

        def hotel_worker(worker_id: int) -> None:
            try:
                while True:
                    run = db.fetch_run(self.run_id) or {}
                    if db.is_cancelled(run):
                        break
                    stats = crs_promote.promote_hotels_once(self.run_id, self.booking_source_id)
                    promoted_n = int(stats.get("promoted") or 0)
                    if promoted_n > 0:
                        with state_lock:
                            totals_box["inserted"] += int(stats.get("inserted") or 0)
                        _log(f"run #{self.run_id} HOTEL w{worker_id} +{promoted_n}")
                        continue
                    if crs_promote.count_unpromoted_hotels(self.run_id) <= 0:
                        break
                    time.sleep(0.1)
            except BaseException as exc:
                errors.append(exc)
                raise

        def room_worker(worker_id: int) -> None:
            try:
                while True:
                    run = db.fetch_run(self.run_id) or {}
                    if db.is_cancelled(run):
                        break
                    stats = crs_promote.promote_rooms_once(self.run_id, self.booking_source_id)
                    promoted_n = int(stats.get("promoted") or 0)
                    if promoted_n > 0:
                        with state_lock:
                            totals_box["rooms_synced"] += int(stats.get("rooms_synced") or 0)
                        _log(f"run #{self.run_id} ROOM w{worker_id} +{promoted_n}")
                        continue
                    # Wait for hotels to finish promoting before exiting if rooms still pending
                    left_h = crs_promote.count_unpromoted_hotels(self.run_id)
                    left_r = crs_promote.count_pending_room_hotels(self.run_id)
                    if left_h <= 0 and left_r <= 0:
                        break
                    time.sleep(0.15)
            except BaseException as exc:
                errors.append(exc)
                raise

        total_workers = hotel_workers + room_workers + 1
        _log(f"run #{self.run_id} promote parallel hotels={hotel_workers} rooms={room_workers}")
        with ThreadPoolExecutor(max_workers=total_workers, thread_name_prefix="rh-promote") as pool:
            futures = [pool.submit(status_worker)]
            futures.extend(pool.submit(hotel_worker, i) for i in range(hotel_workers))
            futures.extend(pool.submit(room_worker, i) for i in range(room_workers))
            # Wait for hotel+room workers (not status)
            for fut in futures[1:]:
                fut.result()
            stop_status.set()
            futures[0].result()

        if errors:
            raise errors[0]

        publish()
        streaming_state.save(self.run_id, {"current_batch": {"phase": "cleanup"}})
        db.merge_meta(self.run_id, "hotel_mapping_runs", {"stream_phase": "cleanup"})

    def _cleanup_batch(self, state: dict[str, Any]) -> None:
        path = self.batch_jsonl_path()
        path.unlink(missing_ok=True)
        batch = state.get("current_batch") or {}
        next_index = int(batch.get("index") or 0) + 1
        # If extract returned nothing useful at EOF, phase already complete
        zst_next = int(state.get("zst_next_line") or 1)
        zst_path = str(state.get("zst_path") or "")
        # Heuristic: if last extract_done was 0 and we already cleaned, check EOF via reader
        if self._zst_reader and self._zst_reader._eof:
            streaming_state.save(
                self.run_id,
                {"current_batch": {"index": next_index, "phase": "complete"}},
            )
            return
        streaming_state.save(
            self.run_id,
            {
                "current_batch": streaming_state.empty_batch(next_index),
            },
        )
        db.merge_meta(self.run_id, "hotel_mapping_runs", {"stream_phase": "extract"})
        del zst_next, zst_path

    def _finalize(self) -> None:
        if self._zst_reader:
            self._zst_reader.close()
            self._zst_reader = None
        # Promote any remaining staging
        crs_promote.promote_until_empty(self.run_id, self.booking_source_id)
        state = streaming_state.load(self.run_id)
        totals = state.get("totals") if isinstance(state.get("totals"), dict) else {}
        inserted = int(totals.get("inserted_hotels") or 0)
        skipped = int(totals.get("skipped") or 0)
        processed = int(totals.get("processed_lines") or 0)
        if inserted <= 0 and processed > 0 and skipped >= processed:
            fail_run(
                self.run_id,
                "No hotels staged: every dump row was skipped (check region map / region.id matching).",
            )
            return

        staging_stats = db.delete_staging_for_run(self.run_id)
        zst_path = str(state.get("zst_path") or "") or None
        run = db.fetch_run(self.run_id)
        if not zst_path and run:
            zst_path = str(run.get("zst_path") or "") or None
        file_stats = storage_cleanup.cleanup_hotel_run_files(
            self.run_id,
            zst_path=zst_path,
            delete_dump=True,
        )
        _log(
            f"run #{self.run_id} cleanup staging="
            f"{staging_stats.get('stagingHotelsDeleted', 0)}h/"
            f"{staging_stats.get('stagingRoomsDeleted', 0)}r "
            f"files={file_stats.get('removedCount', 0)} "
            f"dump_removed={file_stats.get('dumpRemoved')}"
        )
        db.update_run(
            self.run_id,
            status="completed",
            finished_at=db._utc_now(),
            zst_path=None,
            meta=db.merge_meta(
                self.run_id,
                "hotel_mapping_runs",
                {
                    "phase": "completed",
                    "stream_phase": "completed",
                    "cleanup": {
                        **staging_stats,
                        **file_stats,
                    },
                },
            ),
        )
        _log(f"run #{self.run_id} completed")


def fail_run(run_id: str, message: str) -> None:
    db.update_run(
        run_id,
        status="failed",
        finished_at=db._utc_now(),
        error_message=message,
        meta=db.merge_meta(
            run_id, "hotel_mapping_runs", {"phase": "failed", "stream_phase": "failed"}
        ),
    )
