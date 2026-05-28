# Context Migration Guidelines

This summarizes the migration performed so far and the placement rules to follow for future migrations from the old `router -> service -> repository` layout into the modular monolith structure.

## What Changed

- Marketing was moved out of `admin_api.marketing` into `luxtj.contexts.marketing`.
- The old `luxtj.application` and `luxtj.domains` packages were removed instead of kept as compatibility wrappers.
- Domain event primitives and in-process event infrastructure were moved into `luxtj.shared_kernel`.
- Global enums were split by bounded context:
  - `luxtj.contexts.customer.domain.enums`
  - `luxtj.contexts.partner.domain.enums`
  - `luxtj.contexts.marketing.domain.enums`
  - `luxtj.contexts.reports.domain.enums`
- FastAPI apps now include the marketing router directly from the context package.

## Final Placement Rules

Use this decision rule for every moved code block:

| Code block | Final location | Reasoning |
| --- | --- | --- |
| Business entity and invariants | `luxtj.contexts.<context>.domain` | Domain objects must be transport-, database-, and framework-independent. |
| Context-owned enums/value objects | `luxtj.contexts.<context>.domain` | These are part of the domain language and should not live in a global enum dump. |
| Commands and use-case input DTOs | `luxtj.contexts.<context>.application.commands` | Commands describe application actions, not HTTP payloads. |
| Repository/client/event ports | `luxtj.contexts.<context>.application.ports` | The use case owns the abstractions it needs; infrastructure only implements them. |
| Use cases/application services | `luxtj.contexts.<context>.application.use_cases` | This layer orchestrates domain objects, ports, transactions, and events. |
| Repository implementations | `luxtj.contexts.<context>.infrastructure` | Database and external-system details are adapters, not domain/application code. |
| FastAPI routers and schemas | `luxtj.contexts.<context>.presentation.http` | HTTP is an inbound adapter; it translates requests into commands and responses. |
| Context router assembly | `luxtj.contexts.<context>.presentation.http` | Apps should include routers from the owning context directly. |
| Dependency wiring | `luxtj.contexts.<context>.bootstrap` | Concrete adapter choices belong at the composition boundary. |
| Cross-context shared primitives | `luxtj.shared_kernel` | Only stable, generic concepts used across contexts should be shared. |

## Reasoning Behind The Current Placements

Marketing campaign creation moved to `marketing.application.use_cases` because it is an application action: it builds a domain entity, persists it through a port, and publishes resulting domain events. Keeping it out of the FastAPI router makes it usable from both web requests and workers.

`MarketingCampaign` moved to `marketing.domain.campaign` because it represents domain state and behavior. It records events but does not publish them, persist itself, or know about FastAPI.

`MarketingCampaignCreated` moved to `marketing.domain.events` because domain events describe facts from the domain. The event shape is a contract that can later be consumed in-process or through a broker.

`MarketingRepository` and `AudienceResolver` live in `marketing.application.ports` because marketing use cases depend on these capabilities. The application layer owns the interfaces; infrastructure supplies implementations.

The in-memory repository moved to `marketing.infrastructure.persistence` because it is a persistence adapter. It can later be replaced by SQLAlchemy without changing the domain or use case.

FastAPI schemas and routers moved to `marketing.presentation.http` because request validation, response serialization, and route registration are HTTP concerns. They should convert to/from application commands and DTOs only.

Event publisher contracts and in-process event bus moved to `shared_kernel` because event dispatch is generic infrastructure used by multiple contexts. The shared kernel should stay small and stable.

Customer, partner, and report enums were moved out of `luxtj.domains.enums` because a global enum file hides ownership. A context should own its language. Reports keeps its own report-view enums where it is modeling reporting projections rather than source-domain entities.

## Migration Checklist

1. Pick one vertical slice.
2. Identify the bounded context that owns the behavior.
3. Move domain entities, value objects, enums, and domain events into `contexts/<context>/domain`.
4. Move use-case inputs into `contexts/<context>/application/commands.py`.
5. Move interfaces required by the use case into `contexts/<context>/application/ports.py`.
6. Move orchestration logic into `contexts/<context>/application/use_cases.py`.
7. Move concrete repositories and external clients into `contexts/<context>/infrastructure`.
8. Move FastAPI routers and schemas into `contexts/<context>/presentation/http`.
9. Wire concrete dependencies in `contexts/<context>/bootstrap.py`.
10. Update callers to import from final paths directly.
11. Delete old modules; do not add import-path compatibility wrappers.
12. Run `rg "old.import.path"` to verify no stale references remain.
13. Run Ruff and tests.

## Import Rules

Allowed:

```python
context.presentation -> context.application
context.application -> context.domain
context.infrastructure -> context.application
context.bootstrap -> context.application + context.infrastructure
context.domain -> shared_kernel.domain
```

Forbidden:

```python
context.domain -> fastapi
context.domain -> sqlalchemy
context.application -> context.infrastructure
one_context -> another_context.infrastructure
new_code -> luxtj.application
new_code -> luxtj.domains
```

## Validation Commands

Use these checks after each migration:

```powershell
rg "luxtj\.application|luxtj\.domains" src tests
uv run ruff check
uv run pytest
```

The search should return no results once a context has fully moved away from the old package structure.
