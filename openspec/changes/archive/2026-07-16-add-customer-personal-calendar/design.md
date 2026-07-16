## Context

The customer context already implements bucket-list capability using a DDD + hexagonal pattern (domain aggregate, application commands/use cases, SQLAlchemy repository/models, bootstrap wiring, POST-only FastAPI routes, and tests across layers). Personal calendar should follow this same pattern to remain consistent with the modular monolith architecture and existing customer API behavior.

The requested feature introduces date-centric planning primitives that are not covered by bucket-list destination entries:
- Personal events: birthday, anniversary, other special occasion.
- Vacation/holiday periods with fixed/flexible dates.
- Shared holiday preference tags from a predefined list for recommendation intent.

## Goals / Non-Goals

**Goals:**
- Add per-account personal calendar ownership in customer context.
- Support creating personal event items with type-specific required fields and validation.
- Support creating vacation/holiday period items with date-range and flexibility semantics.
- Enforce holiday-type selection from a constrained list with up to three values.
- Expose a backend-owned holiday-type catalog endpoint so clients fetch allowed values from server source of truth.
- Apply validation of holiday types on operations that consume holiday types (not globally on unrelated operations).
- Expose POST create endpoints under `/v1/personal-calendar/{account_id}/...` consistent with bucket-list style.
- Expose a POST consolidated-view endpoint for account-level event+period retrieval.
- Persist data with appropriate constraints and indexes through Alembic + SQLAlchemy.
- Add domain/application/repository/http tests for create flows and validation failures.

**Non-Goals:**
- Implementing update/delete/view endpoints in this change.
- Building recommendation generation logic in this change.
- Cross-context analytics/projections or reporting for calendar data.
- Backfilling historical customer data.

## Decisions

1. Account-scoped root aggregate: `PersonalCalendar` keyed by `account_id`.
- Rationale: Reuses bucket-list ownership model and simplifies customer context consistency.
- Alternative: Keep only item tables keyed directly by account_id.
- Why not chosen: Weakens aggregate semantics and future lifecycle/event modeling.

2. Separate item tables for events and periods.
- Rationale: Event and period shapes are materially different; split tables improves validation and query clarity.
- Alternative: Single polymorphic item table with sparse columns.
- Why not chosen: More nullable fields, weaker DB constraints, higher complexity.

3. Event-type constrained schema in domain.
- Rationale: Enforce required fields by event type:
  - Birthday: relation + person name + event date.
  - Anniversary: relation + person1 + person2 + event date.
  - Special occasion: event name + event date.
- Alternative: Validate only at HTTP layer.
- Why not chosen: Domain invariants should hold regardless of entry point.

4. Holiday type enforcement as enum-backed list with max 3 entries.
- Rationale: Keeps downstream recommendation input standardized and bounded.
- Alternative: Free-text tags.
- Why not chosen: Inconsistent data and poor interoperability.

5. Holiday type source of truth served by backend endpoint.
- Rationale: Keeps allowed values centrally controlled and avoids stale hardcoded client lists.
- Alternative: Ship list only through static client configuration.
- Why not chosen: Weak governance and drift risk across clients.

6. Validation scope is targeted to consumers of holiday types.
- Rationale: Enforce veracity where values enter the system (event/period creation and relevant updates later), without adding unnecessary checks to unrelated operations.
- Alternative: Blanket validation middleware on all customer operations.
- Why not chosen: Noisy and irrelevant for operations that do not touch holiday types.

7. Endpoint contract mirrors bucket-list POST patterns.
- Rationale: API middleware is POST-only and existing clients follow this route shape.
- Alternative: RESTful GET/PUT/DELETE patterns.
- Why not chosen: Incompatible with current middleware and context conventions.

8. Consolidated view is computed in application layer from aggregate state.
- Rationale: Repository already hydrates both events and periods; combining/sorting in use case keeps persistence layer simple and allows response-shape evolution without DB coupling.
- Alternative: Add dedicated SQL union query for timeline projection.
- Why not chosen: unnecessary complexity for current scope.

9. Validation-first persistence constraints.
- Rationale: Combine domain checks with DB constraints for defense in depth (date range, not-null essentials, indexed account/date lookups).
- Alternative: Application-only validation.
- Why not chosen: Less robust against invalid writes and future integration errors.

## Risks / Trade-offs

- [Risk] Ambiguity in “any 3” interpretation for holiday types (exactly 3 vs up to 3) -> Mitigation: implement as maximum 3 for create permissiveness; document contract explicitly in schemas/spec and holiday-types endpoint docs.
- [Risk] Date-only UTC semantics can be misunderstood at boundaries -> Mitigation: store as date type (not datetime) and document UTC/date-only behavior in API contract.
- [Risk] Event schema may expand (e.g., reminders, recurrence) -> Mitigation: keep aggregate and DTO design extensible, with clearly separated event/period entities.
- [Risk] Duplicate event entries for same person/date -> Mitigation: keep duplicates allowed initially unless business asks dedupe; add optional uniqueness constraints in a future scoped change.
- [Risk] Catalog changes may break older clients -> Mitigation: clients fetch holiday types from API at runtime and submit only returned values.
- [Risk] Consolidated ordering could be ambiguous when dates match -> Mitigation: define deterministic ordering in use case (start date, then created timestamp).

## Migration Plan

1. Add SQLAlchemy models for:
   - `customer_personal_calendars`
   - `customer_personal_calendar_events`
   - `customer_personal_calendar_periods`
2. Add Alembic migration with keys, foreign keys, indexes, and check constraints (including period date ordering).
3. Implement repository mapping between rows and domain aggregate/entities.
4. Add commands/use cases/schemas/router and bootstrap wiring, including holiday-type list and consolidated-view endpoints.
5. Add centralized holiday-type validation utility reused by create operations that accept holiday types.
6. Add tests across domain, repository, use cases, and HTTP layers, including holiday-type fetch endpoint, consolidated view endpoint, and invalid holiday type rejection.
7. Run customer-context test suite and full relevant tests.
8. Rollback strategy: Alembic downgrade drops new calendar tables if rollback is needed before dependent production usage.

## Open Questions

- Should holiday type selection be exactly three or up to three values? (Current design assumes up to three.)
- Should duplicate events for same relation/person/date be prevented at domain/DB level?
- Should create endpoints emit domain events now, or defer until recommendation workflows consume them?
