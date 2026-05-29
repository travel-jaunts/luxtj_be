# Migration: src/api and src/common into luxtj

**Date:** 2026-05-29
**Branch:** dev/marketing-apis

## What Changed

`src/api` and `src/common` were deleted. Their code was redistributed into `luxtj` following the modular-monolith DDD/hexagonal architecture.

## File Mapping

| Old path | New path | Notes |
| --- | --- | --- |
| `src/api/version.py` | `src/luxtj/_version.py` | Module-level version constant |
| `src/api/config.py` | `src/luxtj/bootstrap/config.py` | Imports version from `luxtj._version` |
| `src/api/main.py` | `src/luxtj/bootstrap/api.py` | Merged with `kernellib.py` (see below) |
| `src/common/kernellib.py` | `src/luxtj/bootstrap/api.py` | Merged into `bootstrap/api.py`; `init_app_state`, `health_check`, table-creation helpers all live there |
| `src/common/serializerlib.py` | `src/luxtj/shared_kernel/presentation/http/schemas.py` | Shared Pydantic schemas and response envelopes |
| `src/common/middlewarelib.py` | `src/luxtj/shared_kernel/presentation/http/middleware.py` | `EnforcePostMethodOnly`, `EndpointExceptionHandler` |
| `src/common/injectorlib.py` | `src/luxtj/shared_kernel/presentation/http/dependencies.py` | FastAPI `Depends` helpers; state access inlined directly on `request.app.state` (removed intermediate `get_*` functions) |
| `src/common/loglib.py` | `src/luxtj/shared_kernel/infrastructure/logging.py` | `get_logger_handle` |
| `src/common/service/metadata.py` | `src/luxtj/shared_kernel/application/pagination.py` | `PaginationMeta` dataclass |
| `src/common/tourradar/auth.py` | `src/luxtj/shared_kernel/infrastructure/tourradar/auth.py` | Moved as-is; **NOTE: still imports from `app.core.*` which does not exist in this project — needs integration work** |

## New Packages Created

```
src/luxtj/
  _version.py
  bootstrap/
    config.py
    api.py
  shared_kernel/
    presentation/
      __init__.py
      http/
        __init__.py
        schemas.py
        middleware.py
        dependencies.py
    application/
      pagination.py
    infrastructure/
      logging.py
      tourradar/
        __init__.py
        auth.py
```

## Design Decisions

### bootstrap/api.py merges api/main.py and common/kernellib.py

Both files were tightly coupled: `api/main.py` called `init_app_state` from `kernellib.py`, and `kernellib.py` read `api.config`. Keeping them separate was artificial. In the target architecture `bootstrap/` owns composition-root concerns (lifespan, dependency wiring, settings). All of `init_app_state`, `health_check`, `server_factory`, `create_required_tables`, and the lifespan context manager are now co-located.

### dependencies.py accesses request.app.state directly

The old `injectorlib.py` imported helper functions from `kernellib.py` (`get_http_client`, `get_domain_event_publisher`, etc.) which would have created a circular dependency after merging kernellib into `bootstrap/api.py`. The state accessor helpers were one-liners returning `app.state.*`. The new `dependencies.py` accesses `request.app.state.*` directly and has no import from `bootstrap/`.

### Shared-kernel placement for schemas, middleware, and dependencies

These modules are HTTP presentation concerns but are shared across contexts (admin_api, marketing, future contexts). Per the architecture guidelines, cross-context shared primitives belong in `shared_kernel`. Presentation-layer shared primitives go in `shared_kernel/presentation/http/`.

### admin_api imports updated

The user instruction was to not move admin_api business logic. However, since `common` was deleted, all `from common.*` import lines in `admin_api/` were updated to point to their new `luxtj.*` locations. Business logic, routers, and domain models in `admin_api/` are untouched.

## Entry Point Change

The uvicorn entry point changed:

```
# before
uv run uvicorn api.main:server_factory --factory

# after
uv run uvicorn luxtj.bootstrap.api:server_factory --factory
```

`admin_api/main.py` remains an independent app factory that also imports `init_app_state` and `health_check` from `luxtj.bootstrap.api`.

## Files Updated (import-only changes)

### luxtj context files
- `luxtj/contexts/marketing/bootstrap.py`
- `luxtj/contexts/marketing/presentation/http/schemas.py`
- `luxtj/contexts/marketing/presentation/http/router.py`

### admin_api files (52 files — only import lines changed)
All `admin_api/` router, serializer, and service files that previously imported from `common.serializerlib`, `common.service.metadata`, or `common.injectorlib`.

## Known Issues

`luxtj/shared_kernel/infrastructure/tourradar/auth.py` imports from `app.core.bases`, `app.core.config`, and `app.core.logging`. These packages do not exist in this project. This code was already broken before this migration. It needs to be integrated with the project's own config and logging before it can be used.

## Validation

```powershell
# Verify no stale imports remain
rg "from common\.|from api\." src/

# Lint
uv run ruff check

# Tests
uv run pytest
```
