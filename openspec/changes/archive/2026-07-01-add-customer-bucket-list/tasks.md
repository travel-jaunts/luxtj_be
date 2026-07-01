## 1. Schema and Persistence Foundation

- [x] 1.1 Add customer bucket list SQLAlchemy models (bucket list and bucket list items) with customer context declarative base.
- [x] 1.2 Register customer context metadata in alembic/env.py and bootstrap metadata registration.
- [x] 1.3 Create Alembic migration for bucket list tables, ownership constraints, destination uniqueness, and query indexes.
- [x] 1.4 Implement customer bucket list SQLAlchemy repository methods for create, read, update, soft-delete, and active list retrieval.

## 2. Domain and Application Layer

- [x] 2.1 Implement customer bucket list domain entities/aggregate with invariants for ownership, ideal days, ordering, and duplicate prevention.
- [x] 2.2 Add bucket list domain events for item created, item updated, and item deleted with identifying payload fields.
- [x] 2.3 Define application commands/queries and ports for bucket list lifecycle operations and destination suggestions.
- [x] 2.4 Implement use cases for suggest destinations, add item, update item, delete item, and view bucket list with event flush to publisher.

## 3. Suggestion Provider and Routing

- [x] 3.1 Implement a minimal destination suggestion provider adapter (country -> city/place recommendations, city/place -> selection + alternatives).
- [x] 3.2 Add customer context bootstrap wiring for repository, suggestion provider, event publisher, and use cases.
- [x] 3.3 Add customer bucket list HTTP request/response schemas for suggestion and lifecycle endpoints.
- [x] 3.4 Add POST-only customer bucket list routes and include router in public API composition.

## 4. Identity and Event Integration

- [x] 4.1 Add minimal account identity resolution strategy for customer bucket list endpoints (token subject extraction or explicit account_id contract).
- [x] 4.2 Ensure created/updated/deleted bucket list item events are published through outbox event publisher path.
- [x] 4.3 Validate event type naming and payload shape consistency with existing domain event conventions.

## 5. Verification and Quality

- [x] 5.1 Add domain tests for bucket list ownership, item invariants, and lifecycle transitions.
- [x] 5.2 Add repository tests for persistence behavior, uniqueness handling, ordering, and soft-delete visibility.
- [x] 5.3 Add use case tests for suggestion behavior and lifecycle workflows including event emission.
- [x] 5.4 Add API tests for suggest/add/update/delete/view endpoints and error responses.
- [x] 5.5 Run full relevant test suite and migration checks, then update tasks checkboxes for completed work during apply.
