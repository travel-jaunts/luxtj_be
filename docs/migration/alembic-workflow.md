# Database Migration Workflow

This project uses [Alembic](https://alembic.sqlalchemy.org/) for schema migrations against a PostgreSQL database (Supabase). All schema changes must go through a migration file — `LTJBE_DATABASE_AUTO_CREATE` must be `false` in staging and production.

## Key files

| Path | Purpose |
|---|---|
| `alembic.ini` | Alembic config (DB URL is NOT stored here — read from env) |
| `alembic/env.py` | Async engine setup; imports `SharedKernelBase` and `MarketingBase` |
| `alembic/versions/` | Versioned migration files, one per schema change |

## Environment variable

Alembic reads the DB URL from `LTJBE_DATABASE_URL`. Use `.dev.env` locally:

```bash
uv run --env-file .dev.env alembic <command>
```

## Adding a new context with its own DeclarativeBase

When a new bounded context introduces a new `DeclarativeBase`, register its metadata in `alembic/env.py`:

```python
# alembic/env.py
from luxtj.contexts.my_context.infrastructure.persistence.sqlalchemy_models import MyContextBase

target_metadata = [SharedKernelBase.metadata, MarketingBase.metadata, MyContextBase.metadata]
```

Also register it in `src/luxtj/bootstrap/api.py` → `get_registered_metadata()` for local dev auto-create.

## Ongoing workflow

### 1. Change the SQLAlchemy model

Edit the relevant `sqlalchemy_models.py` file. Do not run the app to create columns — Alembic owns all schema changes after the initial setup.

### 2. Generate the migration

```bash
uv run --env-file .dev.env alembic revision --autogenerate -m "short description of change"
```

A new file is created in `alembic/versions/`. **Always review it before committing** — autogenerate is not perfect. Common issues to watch for:
- It may miss changes to `JSON` column contents or custom types.
- It may generate spurious `alter_column` ops for type affinity differences.
- Check that `upgrade()` and `downgrade()` are both correct.

### 3. Commit model and migration together

The model change and its migration file must be in the same commit (or at minimum the same PR). Merging a model change without its migration is what causes the class of failure this workflow prevents.

### 4. Apply on deploy

```bash
alembic upgrade head
```

Run this as part of the deploy process before the app starts. In CI/CD, this should run against the target environment's DB using the appropriate `LTJBE_DATABASE_URL`.

## Useful commands

```bash
# Show full migration history
uv run --env-file .dev.env alembic history

# Show current DB revision(s)
uv run --env-file .dev.env alembic current

# Apply all pending migrations
uv run --env-file .dev.env alembic upgrade head

# Revert the last migration
uv run --env-file .dev.env alembic downgrade -1

# Generate a blank migration (for data migrations or manual DDL)
uv run --env-file .dev.env alembic revision -m "description"
```

## Bootstrapping a new database

On a fresh DB, run:

```bash
uv run --env-file .dev.env alembic upgrade head
```

This runs all migrations from the beginning, creating all tables in order.

## Handling an existing DB that predates Alembic

If a DB already has tables that were created outside Alembic (e.g. via `DATABASE_AUTO_CREATE`), stamp it at the last migration that reflects its current state, then upgrade from there:

```bash
# Mark the DB as being at a specific revision without running migrations
uv run --env-file .dev.env alembic stamp <revision_id>

# Apply any revisions after that point
uv run --env-file .dev.env alembic upgrade head
```
