# LuxTJ BE

FastAPI modular monolith for LuxTJ / Travel Jaunts.

## Stack

| Concern | Choice |
|---------|--------|
| Language | Python ≥ 3.14 |
| API | FastAPI + uvicorn |
| DB | PostgreSQL (async SQLAlchemy + asyncpg) |
| Migrations | Alembic |
| Package manager | uv |
| Admin ledger currency | `INR` (`LTJBE_ADMIN_CURRENCY`) |
| Integration registry cache | In-process maps (invalidate on admin save) |

## Package map

```text
src/luxtj/
  bootstrap/          # app factory, config, lifespan
  shared_kernel/      # events, persistence, HTTP helpers, money
  contexts/
    identity/         # RBAC, admin auth
    marketing/        # campaigns, offers
    account/          # OTP auth
    customer/         # bucket list, calendar
    acquisition/      # waitlist
    action_centre/    # workflow inbox
    integration/      # capability catalog + modules / booking_apis / gateways
    currency/         # admin currency + active currencies + FX
    hotel/            # hotel provider SPI + search/booking (in progress)
    crs/              # hotel CRS inventory + supplier mapping
    payment/          # payment gateway SPI
```

## Schema authority

Hotel / CRS / booking / registry table shapes and **required indexes** come from
`../architecture-docs/` (especially `architecture-hotel-crs-schemas.md`).
Do not blind-copy Laravel migrations from `backend-reference/`.

## Hotel B2C API style (later phases)

Dispatcher: `POST /v1/hotel/service/{requestType}` (Teenva-compatible).
Admin APIs remain `POST /v1/admin/...` with RBAC.

## Architecture docs

- [Modular Monolith](docs/architecture/modular-monolith-ddd-hexagonal.md)
- [Implementation plan](../architecture-docs/IMPLEMENTATION-PLAN.md)

## Local run

```bash
# Postgres must be running; set LTJBE_DATABASE_URL (and optional LTJBE_CRS_DATABASE_URL) in .dev.env
uv sync --group dev
uv run --env-file .dev.env alembic upgrade head
uv run --env-file .dev.env alembic -c alembic_crs.ini upgrade head

# macOS / Linux
./dev.sh

# Windows
.\dev.bat
# or: .\dev.ps1
```

`./dev.sh` defaults to `http://127.0.0.1:9001` (override with `LTJBE_DEV_HOST` / `LTJBE_DEV_PORT`).

Hotel CRS + region catalogue tables live in **`LTJBE_CRS_DATABASE_URL`** (falls back to the main DB URL). Booking tables stay on the main DB and store soft codes (`hotel_crs_hotel_code`, `hotel_crs_room_code`) instead of CRS foreign keys. CRS Alembic tracks revisions in `alembic_version_crs` so it can share a Postgres instance with the main app.

## RateHawk CRS mapping (Path B)

Admin UI: **CRS Mapping** — region catalogue worker + full hotel stream (status polled from DB).

```bash
# Apply main + CRS migrations
uv run --env-file .dev.env alembic upgrade head
uv run --env-file .dev.env alembic -c alembic_crs.ini upgrade head

# Optional CLI (same workers the admin UI spawns; uses CRS DB)
export PYTHONPATH=src
uv run --env-file .dev.env python -m luxtj.contexts.crs.mapping.ratehawk.region_worker <run_id>
uv run --env-file .dev.env python -m luxtj.contexts.crs.mapping.ratehawk.stream_batch_worker start
uv run --env-file .dev.env python -m luxtj.contexts.crs.mapping.ratehawk.stream_batch_worker resume <run_id>
```

Dump files default to `storage/ratehawk/` (`LTJBE_RATEHAWK_STORAGE_PATH` to override). Activate RateHawk under Integrations first.
