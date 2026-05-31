# Worker Framework

This document defines the architecture for background worker processes in LuxTJ. Workers handle domain event processing (outbox relay), async processing pipelines, and scheduled jobs. They are separate OS processes from the HTTP API, packaged as Docker images, sharing the same codebase and domain logic.

## Goals

- Run async processing pipelines (multi-step, long-running) outside the request/response cycle.
- Relay domain events from the transactional outbox to consumers across bounded contexts.
- Execute scheduled/periodic jobs (report generation, data sync, cleanup).
- Reuse the same domain, application, and infrastructure layers as the HTTP API — no logic duplication.
- Deploy workers independently: scale, restart, and version them without touching the API process.
- Maintain the hexagonal dependency rule: worker tasks are presentation-layer adapters that call application use cases.

## Technology Choice

| | Taskiq + taskiq-pg | Celery | Custom |
|---|---|---|---|
| Async native | Yes (`async def` tasks) | No (sync-first, requires wrapping) | Yes |
| PostgreSQL broker | `AsyncpgBroker` (LISTEN/NOTIFY) | Not supported natively | Manual polling |
| Result backend | `AsyncpgResultBackend` | Redis/Postgres via kombu | Manual |
| DI integration | `taskiq-fastapi` bridges FastAPI Depends | None | Manual |
| Scheduling | `LabelScheduleSource` (cron labels) | Celery Beat | Custom |
| Dependency surface | Small (taskiq, taskiq-pg, asyncpg) | Large (kombu, billiard, vine, amqp) | Minimal |

**Decision:** Taskiq + taskiq-pg. It is async-native, uses the existing PostgreSQL instance (no new infrastructure), and integrates with FastAPI's dependency injection — aligning with the codebase's async patterns and hexagonal DI wiring.

## Package Layout

Following the target structure from `modular-monolith-ddd-hexagonal.md`:

```text
src/luxtj/
  bootstrap/
    api.py                          # existing — HTTP server factory
    worker.py                       # NEW — taskiq broker, scheduler, startup hooks
    config.py                       # extended with worker-specific env vars

  shared_kernel/
    infrastructure/
      events/
        outbox.py                   # existing — OutboxEventPublisher (writes to outbox)
        outbox_relay.py             # NEW — task that polls outbox and dispatches to handlers
      persistence/
        outbox_model.py             # existing — DomainEventOutboxRow

  contexts/
    marketing/
      presentation/
        http/                       # existing — FastAPI routes
        worker/
          tasks.py                  # NEW — marketing-specific async tasks
          handlers.py               # NEW — domain event handlers for marketing events
      bootstrap.py                  # extended — register worker tasks/handlers
```

Each context owns its worker tasks in `presentation/worker/`. These are inbound adapters — they deserialize messages, call application use cases, and report results. They must not contain business logic.

## Core Concepts

### 1. Outbox Relay (Domain Event Fan-out)

The outbox relay is a periodic task that:

1. Queries `domain_event_outbox WHERE published_at IS NULL ORDER BY created_at LIMIT N`.
2. For each row, dispatches to registered event handlers (taskiq tasks) by event `type`.
3. Marks rows `published_at = now()` after successful dispatch.
4. On handler failure, leaves `published_at` NULL for retry on next poll cycle.

```python
# shared_kernel/infrastructure/events/outbox_relay.py

@broker.task(schedule=[{"cron": "*/10 * * * * *"}])  # every 10 seconds
async def relay_outbox_events(
    session: AsyncSession = TaskiqDepends(),
    handler_registry: EventHandlerRegistry = TaskiqDepends(),
) -> int:
    rows = await session.scalars(
        select(DomainEventOutboxRow)
        .where(DomainEventOutboxRow.published_at.is_(None))
        .order_by(DomainEventOutboxRow.created_at)
        .limit(100)
        .with_for_update(skip_locked=True)
    )
    published = 0
    for row in rows:
        await handler_registry.dispatch(row.type, row.payload)
        row.published_at = timeutils.datetime_now()
        published += 1
    await session.commit()
    return published
```

The `SELECT ... FOR UPDATE SKIP LOCKED` pattern allows multiple relay workers to run concurrently without double-processing.

### 2. Async Processing Pipelines

For multi-step workflows that don't fit the event-handler pattern (e.g. data enrichment, ETL, report generation), define pipeline tasks that chain or fan-out:

```python
# contexts/reports/presentation/worker/tasks.py

@broker.task
async def generate_monthly_report(
    month: str,
    report_service: ReportService = TaskiqDepends(),
) -> str:
    report = await report_service.generate(month)
    return str(report.id)


@broker.task
async def enrich_partner_data(
    partner_id: str,
    enrichment_service: EnrichmentService = TaskiqDepends(),
) -> dict:
    return await enrichment_service.enrich(partner_id)
```

Pipeline composition uses taskiq's kick mechanism:

```python
# Kick a task programmatically (from API handler or another task)
await generate_monthly_report.kiq(month="2026-05")

# Chain: after enrichment, trigger validation
result = await enrich_partner_data.kiq(partner_id="p-123")
```

For complex multi-step pipelines, define an orchestrator task that awaits intermediate results:

```python
@broker.task
async def run_partner_onboarding_pipeline(partner_id: str) -> None:
    enrichment_result = await enrich_partner_data.kiq(partner_id)
    await enrichment_result.wait_result()
    await validate_partner.kiq(partner_id)
```

### 3. Scheduled Jobs

Use `LabelScheduleSource` for cron-based periodic tasks:

```python
@broker.task(schedule=[{"cron": "0 2 * * *"}])  # daily at 2am
async def cleanup_expired_campaigns(
    marketing_service: MarketingService = TaskiqDepends(),
) -> int:
    return await marketing_service.archive_expired()
```

The scheduler process reads these labels and enqueues tasks at the defined intervals. Only one scheduler instance should run (enforced by deployment).

## Dependency Injection

`taskiq-fastapi` bridges the existing FastAPI dependency graph into worker context. This means workers can reuse:

- `AsyncSession` (via session factory)
- Repository implementations
- Application services (MarketingService, etc.)
- External HTTP clients

### Setup

```python
# bootstrap/worker.py

from taskiq_fastapi import init as taskiq_fastapi_init
from taskiq_pg import AsyncpgBroker, AsyncpgResultBackend

broker = AsyncpgBroker(config.DATABASE_URL).with_result_backend(
    AsyncpgResultBackend(config.DATABASE_URL)
)

# Bridge FastAPI deps into worker — resolves Depends() chains in task signatures
taskiq_fastapi_init(broker, "luxtj.bootstrap.api:server_factory")
```

### Task-level Dependencies

```python
from taskiq import TaskiqDepends
from luxtj.contexts.marketing.application.use_cases import MarketingService

@broker.task
async def handle_campaign_created(
    event_payload: dict,
    marketing_service: MarketingService = TaskiqDepends(),
) -> None:
    ...
```

`TaskiqDepends` resolves through the same DI graph that FastAPI uses. The session factory, repos, and services are constructed per-task-execution, matching the per-request lifecycle of HTTP handlers.

## Event Handler Registry

A thin registry maps event types to handler tasks:

```python
# shared_kernel/infrastructure/events/handler_registry.py

class EventHandlerRegistry:
    def __init__(self):
        self._handlers: dict[str, list[AsyncTaskiqTask]] = {}

    def register(self, event_type: str, task: AsyncTaskiqTask) -> None:
        self._handlers.setdefault(event_type, []).append(task)

    async def dispatch(self, event_type: str, payload: dict) -> None:
        for task in self._handlers.get(event_type, []):
            await task.kiq(event_payload=payload)
```

Contexts register their handlers during bootstrap:

```python
# contexts/marketing/bootstrap.py (worker section)

def register_marketing_event_handlers(registry: EventHandlerRegistry) -> None:
    from luxtj.contexts.marketing.presentation.worker.handlers import (
        on_campaign_created,
        on_campaign_paused,
    )
    registry.register("com.luxtj.marketing.campaign.created.v1", on_campaign_created)
    registry.register("com.luxtj.marketing.campaign.paused.v1", on_campaign_paused)
```

## Configuration

Extend `bootstrap/config.py`:

```python
# Worker-specific settings (same env-var pattern)
WORKER_CONCURRENCY: int = int(os.getenv("LTJBE_WORKER_CONCURRENCY", "10"))
WORKER_OUTBOX_BATCH_SIZE: int = int(os.getenv("LTJBE_WORKER_OUTBOX_BATCH_SIZE", "100"))
WORKER_OUTBOX_POLL_SECONDS: int = int(os.getenv("LTJBE_WORKER_OUTBOX_POLL_SECONDS", "10"))
```

## CLI / Process Startup

```bash
# Start worker (executes tasks)
taskiq worker luxtj.bootstrap.worker:broker --workers 4

# Start scheduler (enqueues periodic tasks — single instance)
taskiq scheduler luxtj.bootstrap.worker:scheduler
```

Both commands use the same `bootstrap/worker.py` entrypoint but run different process roles.

## Docker Packaging

```dockerfile
# Dockerfile.worker
FROM python:3.14-slim
WORKDIR /app
COPY . .
RUN pip install -e ".[worker]"

# Default: run worker. Override CMD for scheduler.
CMD ["taskiq", "worker", "luxtj.bootstrap.worker:broker", "--workers", "4"]
```

The `[worker]` extra in `pyproject.toml` adds taskiq dependencies:

```toml
[project.optional-dependencies]
worker = [
    "taskiq>=0.11",
    "taskiq-pg>=0.2",
    "taskiq-fastapi>=0.3",
]
```

This keeps the HTTP API image lean — it doesn't install taskiq unless building the worker image.

## Example: Marketing Campaign Created Pipeline

End-to-end flow:

1. **API request** → `MarketingService.create_campaign()` → domain records `MarketingCampaignCreated` event → `OutboxEventPublisher` writes to `domain_event_outbox` → transaction commits.

2. **Outbox relay task** (periodic, every 10s) → picks up the row → looks up `com.luxtj.marketing.campaign.created.v1` in registry → dispatches to `on_campaign_created` task.

3. **Handler task** executes:

```python
# contexts/marketing/presentation/worker/handlers.py

@broker.task
async def on_campaign_created(
    event_payload: dict,
    notification_service: NotificationService = TaskiqDepends(),
) -> None:
    campaign_id = event_payload["data"]["campaign_id"]
    await notification_service.notify_team_of_new_campaign(campaign_id)
```

4. If the handler fails, taskiq retries per configured policy. The outbox row's `published_at` was already marked (dispatch succeeded), so the retry is at the task level, not the relay level.

## Failure & Retry Strategy

| Failure point | Behavior |
|---|---|
| Outbox relay can't reach DB | Task fails, scheduler retries on next cron tick |
| Handler task raises exception | Taskiq retries (configurable: max retries, backoff) |
| Worker process crashes mid-task | Task remains unacked, picked up by another worker |
| Duplicate delivery | Handlers must be idempotent (use event `id` as idempotency key) |

## Idempotency

All event handlers and pipeline tasks must be idempotent. Use the event's CloudEvent `id` field as a deduplication key. For pipeline tasks, store a processed-events set or use database constraints to prevent double-application.

## Observability

- Taskiq supports middleware for logging, metrics, and tracing.
- Add OpenTelemetry middleware to propagate trace context from the originating HTTP request through outbox → relay → handler.
- Use the existing `LTJBE_OTLP_ENDPOINT` config for export.

## Implementation Order

1. Add `taskiq`, `taskiq-pg`, `taskiq-fastapi` to `pyproject.toml` `[worker]` extra.
2. Create `bootstrap/worker.py` with broker + scheduler + FastAPI bridge setup.
3. Create `shared_kernel/infrastructure/events/outbox_relay.py` (periodic relay task).
4. Create `shared_kernel/infrastructure/events/handler_registry.py`.
5. Create `contexts/marketing/presentation/worker/` with first handler.
6. Add `Dockerfile.worker` and `docker-compose` service.
7. Extend `config.py` with worker env vars.
8. Write integration test: create campaign via API → verify handler task executes.
