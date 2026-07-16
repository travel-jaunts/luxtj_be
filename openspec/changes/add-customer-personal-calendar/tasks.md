## 1. Domain Model and Validation

- [x] 1.1 Add personal calendar domain aggregate/entities for calendar ownership, event items, and period items in customer context.
- [x] 1.2 Add customer domain enums for event types, birthday/anniversary relation types, and `HOLIDAY_TYPE_LIST` values.
- [x] 1.3 Add and wire domain errors for invalid event payload shape, invalid holiday type selections, and invalid period date ranges.
- [x] 1.4 Implement domain create methods for birthday, anniversary, special occasion, and vacation period with invariant enforcement.
- [x] 1.5 Add shared holiday-type validation helper and apply it to domain/application operations that accept holiday-type input.

## 2. Persistence and Migration

- [x] 2.1 Add SQLAlchemy models for `customer_personal_calendars`, `customer_personal_calendar_events`, and `customer_personal_calendar_periods`.
- [x] 2.2 Add repository interface and SQLAlchemy repository implementation for load/create/save of personal calendar aggregate.
- [x] 2.3 Create Alembic migration with foreign keys, account/date indexes, and check constraints for period date validity and required fields.
- [x] 2.4 Verify metadata registration and auto-create coverage for customer context persistence.

## 3. Application Use Cases

- [x] 3.1 Add commands for creating event items and creating period items.
- [x] 3.2 Add DTOs for event and period create responses aligned with API serializer shapes.
- [x] 3.3 Implement `AddPersonalCalendarEvent` use case with load-or-create behavior by `account_id`.
- [x] 3.4 Implement `AddPersonalCalendarPeriod` use case with load-or-create behavior by `account_id`.

## 4. HTTP API and Bootstrap Wiring

- [x] 4.1 Add request body schemas for event create (type-discriminated fields) and period create validation.
- [x] 4.2 Add response serializers for created event and created period items using existing API response wrappers.
- [x] 4.3 Add POST endpoints `POST /v1/personal-calendar/{account_id}/events/add` and `POST /v1/personal-calendar/{account_id}/periods/add`.
- [x] 4.4 Add POST endpoint `POST /v1/personal-calendar/holiday-types/view` to fetch backend-controlled allowed holiday types.
- [x] 4.5 Add dependency builders in customer bootstrap and include the personal-calendar router in public API composition.
- [x] 4.6 Add POST endpoint `POST /v1/personal-calendar/{account_id}/view` returning consolidated events and periods for an account.

## 5. Verification

- [x] 5.1 Add domain tests for valid create flows and invalid-input invariants across all event types and period ranges.
- [x] 5.2 Add repository tests for persistence/reload behavior of event and period items.
- [x] 5.3 Add use case tests for account-scoped load-or-create behavior and create responses.
- [x] 5.4 Add HTTP tests for success and validation-error responses for both create endpoints.
- [x] 5.5 Add HTTP tests for holiday-type fetch endpoint and ensure list matches backend source of truth.
- [x] 5.6 Add use-case and HTTP tests for consolidated account view response behavior.
- [x] 5.7 Run relevant customer-context tests and confirm no regressions before apply completion.
