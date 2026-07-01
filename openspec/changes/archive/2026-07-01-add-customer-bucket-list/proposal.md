## Why

Customers need a structured way to save destinations they aspire to visit and to receive guided suggestions while building those plans. This change adds that core planning experience now so the customer context can support a persistent, evented bucket list workflow end-to-end.

## What Changes

- Add a customer bucket list domain model with one bucket list per customer/account and multiple bucket list items.
- Add destination suggestion support for the add-item flow:
  - If a country is selected, return recommended cities/places with ideal stay days.
  - If a city/place is selected, return that destination with ideal stay days and alternatives.
- Add APIs to suggest destinations, add/update/delete bucket list items, and view saved bucket list items.
- Persist bucket list and bucket list items in PostgreSQL with constraints and indexes for identity, ordering, and duplicate prevention.
- Emit domain events through the built-in event framework when bucket list items are created, updated, and deleted.

## Capabilities

### New Capabilities
- `customer-bucket-list`: Manage a per-customer bucket list with destination suggestions, item lifecycle operations, persistence, and event emission.

### Modified Capabilities
- None.

## Impact

- Affected areas: `luxtj.contexts.customer` (new domain/application/infrastructure/presentation modules), `luxtj.bootstrap.api`, Alembic migration files, and OpenSpec specs/tasks artifacts.
- API surface: New customer-facing bucket list endpoints in public API routing.
- Database: New bucket list tables and indexes in PostgreSQL.
- Events: New bucket list item lifecycle event types published to outbox/in-process pathways.
