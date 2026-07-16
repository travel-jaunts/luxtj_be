## Why

Customers need a structured personal calendar to capture milestone dates (birthdays, anniversaries, special occasions) and planned vacation periods, then use those dates as intent signals for travel recommendations. Building this now extends the existing customer planning journey beyond bucket list destinations into time-aware trip planning.

## What Changes

- Add a customer personal calendar capability with one calendar per customer account.
- Add create flows for personal calendar event items:
  - Birthday event with constrained relationship type and person name.
  - Anniversary event with constrained relationship type and two person names.
  - Other special occasion with custom event name.
- Add create flow for vacation/holiday period items with start/end dates and fixed/flexible date preference.
- Add standardized holiday-type selection support (up to 3 selections) for both events and periods, based on a defined `HOLIDAY_TYPE_LIST`.
- Add API support to fetch the backend-controlled `HOLIDAY_TYPE_LIST` so clients always use server-approved values.
- Add targeted validation on operations that accept holiday types to ensure submitted values are valid against the backend-controlled list.
- Add POST HTTP endpoints in customer context for creating personal calendar events and vacation periods, following the bucket-list endpoint style.
- Add POST HTTP endpoint to return a consolidated account-level view combining personal calendar events and vacation periods.
- Persist calendar, event, and period records in customer context persistence with constraints and indexes.
- Add tests across domain, repository, use case, and HTTP layers for create behaviors and validation errors.

## Capabilities

### New Capabilities
- `customer-personal-calendar`: Manage per-customer personal travel calendar items (events and vacation periods) with validated create APIs and persistence.

### Modified Capabilities
- None.

## Impact

- Affected code: `src/luxtj/contexts/customer` (domain, application, infrastructure, presentation, bootstrap), `src/luxtj/bootstrap/api.py`, `alembic/versions`, and `tests/luxtj/contexts/customer`.
- API surface: new customer endpoints under `/v1/personal-calendar/{account_id}/...` for create and consolidated-view operations, plus holiday-type list fetch endpoint.
- Database: new customer personal calendar tables and related constraints/indexes.
- No new third-party dependencies expected.
