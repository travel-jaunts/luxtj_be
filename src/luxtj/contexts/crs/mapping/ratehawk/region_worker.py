"""Region mapping worker — catalogue + booking_source_region_map."""

from __future__ import annotations

import json
import os
import sys
from typing import Any
from uuid import uuid4

from . import api_client, config, db, region_parser, storage_cleanup, zstd_lines
from .credentials import load_ratehawk_api


def flush_region_batches(
    booking_source_id: str,
    catalogue_batch: dict[str, dict[str, Any]],
    map_batch: list[dict[str, Any]],
    existing_codes: dict[str, str],
    mapped_region_ids: set[str],
) -> int:
    inserted = 0
    now = db._utc_now()
    with db.db_cursor() as (_, cur):
        for dedupe_key, row in catalogue_batch.items():
            cur.execute(
                """
                INSERT INTO new_cities_n_regions (
                    id, name, type, iata, latitude, longitude,
                    country_name, country_code, dedupe_key, created_at, updated_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (dedupe_key) DO NOTHING
                """,
                (
                    str(uuid4()),
                    row["name"],
                    row["type"],
                    row.get("iata"),
                    row.get("latitude"),
                    row.get("longitude"),
                    row["country_name"],
                    row["country_code"],
                    dedupe_key,
                    now,
                    now,
                ),
            )

        dedupe_keys = list({item["_dedupe_key"] for item in map_batch})
        id_by_dedupe: dict[str, str] = {}
        if dedupe_keys:
            placeholders = ",".join(["%s"] * len(dedupe_keys))
            cur.execute(
                f"SELECT id, dedupe_key FROM new_cities_n_regions WHERE dedupe_key IN ({placeholders})",
                tuple(dedupe_keys),
            )
            for region_id, dedupe_key in cur.fetchall():
                id_by_dedupe[str(dedupe_key)] = str(region_id)

        for item in map_batch:
            region_id = id_by_dedupe.get(item["_dedupe_key"]) or ""
            code = str(item["booking_source_region_code"])
            if not region_id or region_id in mapped_region_ids or code in existing_codes:
                continue
            cur.execute(
                """
                INSERT INTO booking_source_region_map (
                    id, booking_source_id, new_cities_n_region_id, booking_source_region_code,
                    created_at, updated_at
                ) VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (booking_source_id, booking_source_region_code) DO NOTHING
                """,
                (str(uuid4()), booking_source_id, region_id, code, now, now),
            )
            if cur.rowcount:
                existing_codes[code] = region_id
                mapped_region_ids.add(region_id)
                inserted += 1
    return inserted


def run_region(run_id: str) -> None:
    run = db.fetch_region_run(run_id)
    if not run:
        raise RuntimeError(f"Region run {run_id} not found")

    creds = load_ratehawk_api()
    booking_source_id = str(creds["booking_source_id"])
    storage = config.storage_path()
    storage.mkdir(parents=True, exist_ok=True)
    zst_path = str(storage / "regions.zst")
    batch_size = config.region_batch_size()

    db.update_region_run(
        run_id,
        status="running",
        started_at=db._utc_now(),
        meta=db.merge_meta(
            run_id,
            "region_mapping_runs",
            {
                "phase": "downloading",
                "engine": "python",
                "process_pid": os.getpid(),
            },
        ),
    )

    try:
        from pathlib import Path

        dump_url = api_client.fetch_region_dump_url()
        db.update_region_run(run_id, dump_url=dump_url, zst_path=zst_path)

        if not Path(zst_path).is_file() or Path(zst_path).stat().st_size < 1:

            def on_progress(downloaded: int, total: int) -> None:
                db.merge_meta(
                    run_id,
                    "region_mapping_runs",
                    {
                        "download_bytes": downloaded,
                        "download_total": total,
                        "heartbeat_at": db._iso_now(),
                    },
                )

            api_client.download_to_file(dump_url, zst_path, on_progress=on_progress)

        db.merge_meta(
            run_id, "region_mapping_runs", {"phase": "mapping", "heartbeat_at": db._iso_now()}
        )

        existing_codes = db.load_region_map(booking_source_id)
        mapped_region_ids = set(existing_codes.values())
        processed = matched = skipped = map_inserted = 0
        catalogue_batch: dict[str, dict[str, Any]] = {}
        map_batch: list[dict[str, Any]] = []
        now = db._utc_now()

        for line in zstd_lines.iter_zst_lines(zst_path):
            if db.is_cancelled(db.fetch_region_run(run_id)):
                return
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(row, dict):
                continue
            code = str(row.get("id") or "")
            if not code:
                continue
            processed += 1
            if code in existing_codes:
                skipped += 1
                matched += 1
                continue

            parsed = region_parser.parse_region_row(row)
            if parsed is None:
                continue

            dedupe_key = region_parser.build_dedupe_key(
                parsed["name"],
                parsed["type"],
                parsed["country_name"],
                parsed["country_code"],
            )

            with db.db_cursor() as (_, cur):
                cur.execute(
                    "SELECT id FROM new_cities_n_regions WHERE dedupe_key = %s",
                    (dedupe_key,),
                )
                found = cur.fetchone()
            catalogue_id = str(found[0]) if found else ""
            if catalogue_id and catalogue_id in mapped_region_ids:
                skipped += 1
                matched += 1
                continue

            if not catalogue_id:
                catalogue_batch[dedupe_key] = {
                    **parsed,
                    "dedupe_key": dedupe_key,
                    "created_at": now,
                    "updated_at": now,
                }
            map_batch.append(
                {
                    "booking_source_region_code": code,
                    "_dedupe_key": dedupe_key,
                    "created_at": now,
                    "updated_at": now,
                }
            )

            if len(map_batch) >= batch_size:
                mi = flush_region_batches(
                    booking_source_id,
                    catalogue_batch,
                    map_batch,
                    existing_codes,
                    mapped_region_ids,
                )
                map_inserted += mi
                matched += mi
                catalogue_batch = {}
                map_batch = []
                db.update_region_run(
                    run_id,
                    processed_count=processed,
                    matched_count=map_inserted,
                    skipped_count=skipped,
                    meta=db.merge_meta(
                        run_id, "region_mapping_runs", {"heartbeat_at": db._iso_now()}
                    ),
                )

        if catalogue_batch or map_batch:
            mi = flush_region_batches(
                booking_source_id,
                catalogue_batch,
                map_batch,
                existing_codes,
                mapped_region_ids,
            )
            map_inserted += mi
            matched += mi

        file_stats = storage_cleanup.cleanup_region_run_files(
            zst_path=zst_path,
            delete_dump=True,
        )
        print(
            f"[ratehawk-region] cleaned dump files removed={file_stats.get('removedCount', 0)} "
            f"dump_removed={file_stats.get('dumpRemoved')}",
            flush=True,
        )

        db.update_region_run(
            run_id,
            status="completed",
            finished_at=db._utc_now(),
            processed_count=processed,
            matched_count=map_inserted,
            skipped_count=skipped,
            cities_count=processed,
            zst_path=None,
            meta=db.merge_meta(
                run_id,
                "region_mapping_runs",
                {
                    "phase": "completed",
                    "heartbeat_at": db._iso_now(),
                    "cleanup": file_stats,
                },
            ),
        )
        print(
            f"[ratehawk-region] completed run={run_id} processed={processed} "
            f"inserted={map_inserted} skipped={skipped}",
            flush=True,
        )
    except Exception as exc:
        db.update_region_run(
            run_id,
            status="failed",
            finished_at=db._utc_now(),
            error_message=str(exc),
            meta=db.merge_meta(run_id, "region_mapping_runs", {"phase": "failed"}),
        )
        raise


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: python -m luxtj.contexts.crs.mapping.ratehawk.region_worker <run_id>", file=sys.stderr)
        return 1
    run_region(sys.argv[1])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
