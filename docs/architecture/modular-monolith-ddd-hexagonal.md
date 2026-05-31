# Modular Monolith Architecture

This document defines the target organization for LuxTJ backend code using Domain Driven Design and hexagonal architecture. The goal is a modular monolith that can later be split into independently deployed services with minimal code movement.

## Goals

- Keep business rules in domain modules, independent of FastAPI, Celery, SQLAlchemy, HTTP clients, or message broker SDKs.
- Keep each subdomain isolated behind application ports and published events.
- Allow the same domain and application logic to run from an HTTP server, a background worker, a scheduled job, or tests.
- Support in-process domain event handling today and external message queues later.
- Prevent infrastructure from one domain being imported by another domain.

## Current State

The current codebase is mostly organized as:

```text
admin_api/<area>/<feature>/router.py
admin_api/<area>/<feature>/service.py
admin_api/<area>/<feature>/domainmodel.py
```

There is also an early DDD structure under `src/luxtj`:

```text
luxtj/application
luxtj/domains
luxtj/infrastructure
```

The next architecture should move toward bounded contexts as the primary unit of organization. The `admin_api` package should become a delivery adapter, not the owner of business services or domain models.

## Target Package Layout

Use one package per bounded context under `luxtj/contexts`. Each context owns its domain, use cases, ports, adapters, and event handlers.

```text
src/luxtj/
  bootstrap/
    api.py
    worker.py
    container.py

  shared_kernel/
    domain/
      events.py
      ids.py
      money.py
      errors.py
    application/
      ports.py
      unit_of_work.py
      event_bus.py
    infrastructure/
      events/
        in_process.py
        outbox.py
        message_broker.py
      persistence/
        sqlalchemy_session.py

  contexts/
    marketing/
      domain/
        campaign.py
        events.py
        policies.py
        value_objects.py
        errors.py
      application/
        commands.py
        queries.py
        use_cases.py
        ports.py
        handlers.py
      infrastructure/
        persistence/
          sqlalchemy_models.py
          sqlalchemy_repositories.py
        messaging/
          event_publishers.py
      presentation/
        http/
          router.py
          schemas.py
        worker/
          tasks.py
      bootstrap.py

    finance/
      domain/
      application/
      infrastructure/
      presentation/
      bootstrap.py

    reports/
      domain/
      application/
      infrastructure/
      presentation/
      bootstrap.py
```

`admin_api` can remain temporarily as a compatibility package, but it should delegate to context presentation adapters or be gradually replaced by `luxtj.contexts.<context>.presentation.http`.

## Dependency Rule

Dependencies point inward.

```text
presentation -> application -> domain
infrastructure -> application/domain
bootstrap -> presentation/application/infrastructure
```

Rules:

- `domain` imports only Python standard library, domain-local modules, and `shared_kernel.domain`.
- `application` imports its own `domain` and shared application ports. It defines use cases and outbound ports.
- `presentation` imports application use cases and converts transport DTOs to commands or queries.
- `infrastructure` implements application ports. It may import SQLAlchemy, Redis, HTTP clients, broker SDKs, and other technical dependencies.
- `bootstrap` wires concrete adapters into use cases.
- One context must not import another context's infrastructure.
- Cross-context reads go through application ports or stable published read models.
- Cross-context writes go through commands on the owning context or events, never through another context's repository.

## Bounded Contexts

Initial context boundaries should be:

| Context | Owns | Does not own |
| --- | --- | --- |
| `marketing` | campaigns, audiences, marketing offers, campaign events | finance ledgers, customer identity storage |
| `finance` | payments, refunds, payouts, ledger facts, finance events | marketing campaign rules, report formatting |
| `customer` | customer profiles, support tickets, customer bookings | partner onboarding, finance ledger internals |
| `partner` | partner profiles, properties, partner offers, approvals | customer profile internals |
| `reports` | report definitions, report read models, analytics projections | source-of-truth transactional writes |
| `audit` | audit log events and immutable audit views | source domain behavior |

Reports are a separate bounded context because reports compose data from other contexts. Reports should depend on reporting ports or projections, not on finance or marketing repositories.

## Context Public API

Each context exposes a deliberately small Python API from its `application` layer. Other modules can depend on this API, not on internal files.

Example:

```text
luxtj.contexts.marketing.application.public
  CampaignQueryService
  CreateCampaignCommand
  CampaignSummary
```

Avoid imports such as:

```python
from luxtj.contexts.marketing.infrastructure.persistence.sqlalchemy_repositories import ...
from luxtj.contexts.marketing.domain.campaign import MarketingCampaign
```

from another context. Domain entities are not integration contracts.

## Domain Layer

Domain objects model business concepts and invariants. They should not know how they are stored, serialized over HTTP, or published to a broker.

Use entities and value objects:

```python
from dataclasses import dataclass, field
from datetime import date
from uuid import UUID

from luxtj.shared_kernel.domain.events import DomainEvent


@dataclass
class Campaign:
    id: UUID
    name: str
    starts_on: date
    events: list[DomainEvent] = field(default_factory=list, init=False)

    def activate(self) -> None:
        if self.starts_on < date.today():
            raise CampaignCannotStartInPast()
        self.events.append(CampaignActivated(campaign_id=self.id))
```

Domain methods should raise domain errors and record domain events. They should not call repositories, SQLAlchemy sessions, HTTP clients, or event publishers.

## Application Layer

Application use cases orchestrate domain objects, repositories, transactions, and event publication.

```python
from dataclasses import dataclass
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True)
class CreateCampaignCommand:
    name: str
    starts_on: date


class CampaignRepository(Protocol):
    async def add(self, campaign: Campaign) -> None: ...
    async def get(self, campaign_id: UUID) -> Campaign | None: ...


class UnitOfWork(Protocol):
    campaigns: CampaignRepository

    async def commit(self) -> None: ...
    async def rollback(self) -> None: ...


class EventPublisher(Protocol):
    async def publish_many(self, events: list[DomainEvent]) -> None: ...


class CreateCampaign:
    def __init__(self, uow: UnitOfWork, event_publisher: EventPublisher):
        self.uow = uow
        self.event_publisher = event_publisher

    async def __call__(self, command: CreateCampaignCommand) -> CampaignDTO:
        campaign = Campaign.create(name=command.name, starts_on=command.starts_on)
        await self.uow.campaigns.add(campaign)
        await self.uow.commit()
        await self.event_publisher.publish_many(campaign.events)
        return CampaignDTO.from_domain(campaign)
```

This use case can be called from FastAPI, Celery, a CLI script, or a test without modification.

## Ports

Ports are `Protocol` interfaces owned by the application layer of the context that needs them.

Examples:

```python
class CampaignRepository(Protocol):
    async def get(self, campaign_id: CampaignId) -> Campaign | None: ...
    async def save(self, campaign: Campaign) -> None: ...


class FinanceMetricsReader(Protocol):
    async def revenue_for_campaign(self, campaign_id: str) -> Money: ...


class EventPublisher(Protocol):
    async def publish_many(self, events: list[DomainEvent]) -> None: ...
```

The consumer owns the port. If reports needs finance data, `reports.application.ports` defines `FinanceReportDataReader`. A monolith adapter may call finance application queries. A distributed adapter may call finance over HTTP or consume a projection.

## Infrastructure Layer

Infrastructure contains replaceable adapters:

- SQLAlchemy repositories
- Unit of work implementations
- HTTP clients for external systems
- Message broker publishers and consumers
- In-process event buses
- Outbox processors
- Read model projectors

Infrastructure can depend on application ports and domain models, but domain and application cannot depend on infrastructure.

Example:

```python
class SqlAlchemyCampaignRepository(CampaignRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, campaign_id: CampaignId) -> Campaign | None:
        row = await self.session.get(CampaignRow, campaign_id.value)
        return campaign_from_row(row) if row else None
```

Do not place SQLAlchemy models in `domain`. ORM classes are persistence models, not domain entities. Mapping functions belong in infrastructure.

## Presentation Layer

HTTP routers and worker tasks are inbound adapters. They should:

- Validate transport input.
- Convert requests into commands or queries.
- Call one application use case.
- Convert application DTOs into response schemas.

They should not:

- Open database sessions directly.
- Import repositories directly.
- Contain business rules.
- Publish domain events directly.

FastAPI adapter:

```python
router = APIRouter(prefix="/campaigns")


@router.post("")
async def create_campaign(
    body: CreateCampaignBody,
    use_case: Annotated[CreateCampaign, Depends(resolve_create_campaign)],
) -> CampaignResponse:
    result = await use_case(body.to_command())
    return CampaignResponse.from_dto(result)
```

Worker adapter:

```python
async def create_campaign_task(payload: dict) -> None:
    command = CreateCampaignCommand(**payload)
    use_case = container.resolve(CreateCampaign)
    await use_case(command)
```

The worker and API share the same use case.

## Dependency Injection

Each context has a local bootstrap module that wires its adapters. The application root selects which adapters to use.

```python
def build_marketing_module(settings: Settings, session_factory: SessionFactory) -> MarketingModule:
    uow = SqlAlchemyMarketingUnitOfWork(session_factory)

    if settings.EVENT_TRANSPORT == "in_process":
        publisher = InProcessEventPublisher()
    else:
        publisher = OutboxEventPublisher(uow)

    return MarketingModule(
        create_campaign=CreateCampaign(uow=uow, event_publisher=publisher),
        list_campaigns=ListCampaigns(uow=uow),
    )
```

FastAPI `Depends` should resolve use cases from the composition root. It should not construct repositories in router packages.

## Domain Events

Use CloudEvents-compatible envelopes at the shared boundary. Keep events immutable and versioned.

```python
@dataclass(frozen=True)
class DomainEvent:
    id: str
    type: str
    source: str
    subject: str | None
    occurred_at: datetime
    data: Mapping[str, object]
    version: int = 1
```

Event naming:

```text
com.luxtj.<context>.<aggregate>.<event>.v<version>
```

Examples:

```text
com.luxtj.marketing.campaign.created.v1
com.luxtj.finance.payment.refunded.v1
com.luxtj.partner.approval.approved.v1
```

Guidelines:

- Domain events describe facts that already happened.
- Events should contain stable IDs and the data consumers need, not ORM objects.
- Event payloads are contracts. Version them when shape or meaning changes.
- Domain objects record events. Application services publish events after commit.
- Consumers must be idempotent.

## In-process And External Event Consumers

Use the same `EventPublisher` port for both in-process and external delivery.

```text
Application use case
  -> EventPublisher port
      -> InProcessEventBus adapter today
      -> Outbox + broker adapter later
```

In-process adapter:

```python
class InProcessEventBus(EventPublisher):
    def __init__(self, handlers: Mapping[str, list[EventHandler]]):
        self.handlers = handlers

    async def publish_many(self, events: list[DomainEvent]) -> None:
        for event in events:
            for handler in self.handlers.get(event.type, []):
                await handler(event)
```

External adapter:

```python
class BrokerEventPublisher(EventPublisher):
    async def publish_many(self, events: list[DomainEvent]) -> None:
        for event in events:
            await self.producer.publish(topic=event.type, payload=to_cloudevent(event))
```

For durable external publishing, prefer the transactional outbox:

1. Use case changes aggregates.
2. Unit of work saves aggregates and outbox rows in one transaction.
3. Outbox processor publishes rows to the broker.
4. Processor marks rows as published.

This avoids losing events when the database commit succeeds but broker publishing fails.

## Reports Context

Reports should not import domain models from marketing, finance, customer, or partner. Reports has its own report models and read ports.

```python
class MarketingReportDataReader(Protocol):
    async def campaign_performance(self, query: CampaignPerformanceQuery) -> list[CampaignMetric]: ...


class FinanceReportDataReader(Protocol):
    async def finance_summary(self, query: FinanceSummaryQuery) -> FinanceSummary: ...
```

In the monolith, adapters can be:

- Direct application query adapters, calling public query services from other contexts.
- SQL read model adapters, reading denormalized reporting tables.
- In-memory adapters for tests and local development.

When split into services, replace those adapters with HTTP clients, gRPC clients, or projections fed by events. Report use cases do not change.

## Migration Plan

Migrate one vertical slice at a time. Marketing campaigns are the best first slice because they already have a repository protocol and event publisher.

1. Create `luxtj/contexts/marketing`.
2. Move campaign domain entity and events into `marketing/domain`.
3. Move `CreateCampaignDTO` into `marketing/application/commands.py` or `dto.py`.
4. Move `MarketingService` into `marketing/application/use_cases.py`.
5. Move repository protocol into `marketing/application/ports.py`.
6. Move in-memory and SQLAlchemy repositories into `marketing/infrastructure/persistence`.
7. Move FastAPI router and schemas into `marketing/presentation/http`.
8. Add `marketing/bootstrap.py` to wire use cases.
9. Keep old `admin_api.marketing.campaigns` imports as compatibility wrappers if needed.
10. Repeat for finance, customer, partner, reports, and audit.

## Import Rules To Enforce

Add import-linting later, but follow these rules immediately:

Allowed:

```python
luxtj.contexts.marketing.presentation -> luxtj.contexts.marketing.application
luxtj.contexts.marketing.application -> luxtj.contexts.marketing.domain
luxtj.contexts.marketing.infrastructure -> luxtj.contexts.marketing.application
luxtj.contexts.reports.infrastructure -> luxtj.contexts.finance.application.public
luxtj.bootstrap -> any context bootstrap
```

Forbidden:

```python
luxtj.contexts.marketing.domain -> fastapi
luxtj.contexts.marketing.domain -> sqlalchemy
luxtj.contexts.marketing.application -> luxtj.contexts.marketing.infrastructure
luxtj.contexts.reports.application -> luxtj.contexts.finance.infrastructure
luxtj.contexts.marketing -> admin_api
luxtj.contexts.finance.infrastructure -> luxtj.contexts.marketing.infrastructure
```

## Domain Policies

A **domain policy** (also called a business rule or guard) is a named check that must hold true before a domain operation is allowed. Policies enforce invariants that cross multiple fields or depend on external domain facts (e.g. "the date must be in the future"). They differ from field-level validation in that they express **why** a value is rejected in domain language, not just that it is malformed.

### Where Policies Live

Policies live in `domain/policies.py` of the owning context. They may only import from:

- Python standard library
- `domain/errors.py` (same context)
- `domain/enums.py` (same context)
- `shared_kernel.domain`

They must not import from application, infrastructure, or presentation layers.

### Error Hierarchy

Each context defines its own domain error hierarchy in `domain/errors.py`:

```python
class MarketingDomainError(Exception):
    pass


class CampaignPolicyViolationError(MarketingDomainError):
    pass


class StartDateInPastError(CampaignPolicyViolationError):
    pass


class RecurringScheduleRequiredError(CampaignPolicyViolationError):
    pass
```

The base `CampaignPolicyViolationError` acts as a catch-all for the presentation layer. Specific subclasses let tests and callers react to individual violations without relying on error message strings.

### Policy Base Class

Define a single abstract base for all policies within an aggregate operation. Use a **context object** (a frozen dataclass) to carry all data that policies might inspect. This keeps policy signatures stable as new rules are added — new fields go on the context, not on every policy's method signature.

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class CampaignCreationContext:
    """All data available to creation policies. Extend this to expose new inputs to future rules."""

    start_date: date
    frequency: ScheduleFrequencyEnum
    frequency_schedule: str | None


class CampaignPolicy(ABC):
    @abstractmethod
    def enforce(self, ctx: CampaignCreationContext) -> None:
        """Raise CampaignPolicyViolationError if the rule is violated."""
```

### Implementing a Policy

Each policy is a small class with a single `enforce` method. Policies should be stateless; instantiate them once and reuse them.

```python
class StartDatePolicy(CampaignPolicy):
    def enforce(self, ctx: CampaignCreationContext) -> None:
        if ctx.start_date < date.today():
            raise StartDateInPastError(
                f"start_date must be today or in the future, got {ctx.start_date}"
            )
```

### Composing Policies

Group related policies into a composite class. Add new policies to `_policies` without touching callers.

```python
class CampaignCreationPolicies:
    _policies: tuple[CampaignPolicy, ...] = (
        StartDatePolicy(),
        RecurringSchedulePolicy(),
    )

    def enforce_all(self, ctx: CampaignCreationContext) -> None:
        for policy in self._policies:
            policy.enforce(ctx)


_creation_policies = CampaignCreationPolicies()
```

### Applying Policies in Domain Factory Methods

Call `enforce_all` at the top of the domain factory method, before constructing the entity. If any policy raises, the entity is never created and no state change occurs.

```python
@classmethod
def create(cls, *, start_date: date, frequency: ScheduleFrequencyEnum, ...) -> MarketingCampaign:
    _creation_policies.enforce_all(
        CampaignCreationContext(
            start_date=start_date,
            frequency=frequency,
            frequency_schedule=frequency_schedule,
        )
    )
    # entity construction only reaches here if all policies passed
    return cls(status=CampaignStatusEnum.SCHEDULED, ...)
```

Domain methods that mutate an existing entity follow the same pattern: build a context from the incoming change, run the relevant policies, then apply the change.

### Handling Policy Violations in the Presentation Layer

Presentation adapters catch the base policy violation type and convert it to the appropriate transport response. They must not catch specific subclasses unless they need to map each violation to a different HTTP status or response field.

```python
try:
    campaign = await marketing_service.create_campaign(command)
except CampaignPolicyViolationError as exc:
    return ApiErrorResponse(error_message=str(exc))
```

The application layer (use cases) should let `CampaignPolicyViolationError` propagate naturally. Use cases orchestrate, they do not own business rules.

### Adding a New Policy

1. Add new domain error subclasses to `domain/errors.py` if needed.
2. Extend `CampaignCreationContext` (or the relevant context dataclass) with any new fields required.
3. Implement the new `CampaignPolicy` subclass in `domain/policies.py`.
4. Add an instance to the `_policies` tuple of the relevant composite.
5. Write a pure unit test in `tests/contexts/marketing/domain/` — no database, no FastAPI.

No other files need to change.

### Testing Policies

Policy tests are pure unit tests. They test the policy class directly; they do not need the full entity or an application use case.

```python
def test_start_date_in_past_raises():
    policy = StartDatePolicy()
    ctx = CampaignCreationContext(
        start_date=date(2000, 1, 1),
        frequency=ScheduleFrequencyEnum.ONE_TIME,
        frequency_schedule=None,
    )
    with pytest.raises(StartDateInPastError):
        policy.enforce(ctx)


def test_start_date_today_is_valid():
    policy = StartDatePolicy()
    ctx = CampaignCreationContext(
        start_date=date.today(),
        frequency=ScheduleFrequencyEnum.ONE_TIME,
        frequency_schedule=None,
    )
    policy.enforce(ctx)  # must not raise
```

Domain entity tests verify that `create()` delegates to policies correctly; they do not re-test individual policy logic.



Test by layer:

- Domain tests: pure unit tests, no FastAPI, no database.
- Application tests: use fake repositories, fake unit of work, fake event publisher.
- Infrastructure tests: verify SQLAlchemy mappings, repository behavior, broker adapters.
- Presentation tests: use FastAPI TestClient with dependency overrides.
- Contract tests: verify event payloads and public application DTOs.

The most important tests for future service extraction are application tests and event contract tests.

## Definition Of Done For A Context

A context follows this architecture when:

- Domain code has no FastAPI, SQLAlchemy, Celery, HTTP, or broker imports.
- Use cases depend only on ports, not concrete repositories or clients.
- Repositories are implemented in infrastructure.
- HTTP routers and worker tasks call application use cases.
- Events are emitted through an `EventPublisher` port after successful persistence.
- Cross-context interactions use public application APIs, ports, read models, or events.
- No other context imports this context's infrastructure.
