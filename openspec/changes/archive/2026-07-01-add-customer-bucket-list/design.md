## Context

The codebase follows a modular monolith with DDD + hexagonal patterns under luxtj.contexts. The customer context currently has enums but no implemented bucket list aggregate, persistence model, or public customer routes for this workflow. The API enforces POST-only routes, and domain events are emitted via the shared event publisher with outbox persistence.

## Goals / Non-Goals

**Goals:**
- Add a per-customer bucket list capability with a one-to-one bucket list to customer/account identity.
- Support destination suggestion flows for country and city/place selection with ideal stay day recommendations.
- Provide endpoints for suggesting destinations, adding/updating/deleting bucket list items, and viewing saved bucket list items.
- Persist bucket lists and bucket list items in PostgreSQL via Alembic migrations.
- Emit domain events for bucket list item created/updated/deleted through the existing event framework.
- Keep changes minimal and consistent with existing context bootstrap, repository, use case, and presentation patterns.

**Non-Goals:**
- Building a full destination intelligence platform with live external providers in this change.
- Introducing cross-context reporting/projections for bucket list analytics.
- Redesigning existing auth architecture beyond what is minimally required to identify customer/account for these APIs.

## Decisions

1. Identity anchor: account_id as customer key for bucket list ownership.
- Rationale: Existing auth flow issues JWT with sub=account_id and account persistence already exists.
- Alternative considered: Introduce a new customer profile identity table first.
- Why not now: Increases scope and migration complexity without changing bucket list behavior.

2. Data model: separate bucket list header and items tables.
- Rationale: Encodes one-to-one ownership with clear constraints while allowing ordered item collections.
- Alternative considered: single table keyed by account_id.
- Why not chosen: Harder to model aggregate lifecycle and future metadata expansion.

3. Item lifecycle strategy: soft delete for bucket list items.
- Rationale: Preserves history and prevents accidental hard-loss while enabling idempotent delete semantics.
- Alternative considered: hard delete.
- Why not chosen: Loses traceability and complicates event-audit consistency.

4. Suggestion provider abstraction via application port.
- Rationale: Keeps use cases stable while allowing static provider now and external provider later.
- Alternative considered: embedding suggestion logic directly in use case or router.
- Why not chosen: Violates separation of concerns and limits extensibility.

5. Event schema: dedicated customer bucket list item event types.
- Rationale: Aligns with existing cloud-event-like typing and keeps downstream filtering explicit.
- Alternative considered: generic customer-updated event.
- Why not chosen: Too coarse for projections and workflow triggers.

6. Endpoint style: POST-only endpoints under public API router.
- Rationale: Matches enforced middleware behavior and existing API conventions.
- Alternative considered: RESTful GET/PUT/DELETE mix.
- Why not chosen: Incompatible with current method enforcement.

## Risks / Trade-offs

- [Risk] Ambiguity in customer identity resolution for public endpoints. -> Mitigation: Introduce a minimal auth dependency to resolve account_id from token subject; if deferred, require explicit account_id in request payload for internal-only usage.
- [Risk] Static suggestion provider quality may be limited initially. -> Mitigation: Keep provider behind port and include deterministic fallback data for high-confidence destinations.
- [Risk] Duplicate destination entries due to casing/spacing variance. -> Mitigation: Normalize destination names for uniqueness checks and enforce DB uniqueness with normalized semantics where possible.
- [Risk] Event payload drift across create/update/delete. -> Mitigation: Define common identifying fields (account_id, bucket_list_id, item_id, destination_kind, destination_name) across all bucket list item lifecycle events.

## Migration Plan

1. Add customer context persistence models and declarative base for bucket list tables.
2. Register customer metadata in alembic/env.py target_metadata.
3. Generate and review Alembic migration for new bucket list tables, constraints, and indexes.
4. Register customer metadata in bootstrap table registration for local auto-create parity.
5. Deploy migration before enabling endpoints in production.
6. Rollback strategy: Alembic downgrade to drop new tables if no dependent production data must be retained.

## Open Questions

- Resolved: bucket list ownership is permanently mapped to account_id for this capability.
- Resolved: production destination suggestions use a third-party provider as the source of truth.
- Resolved: destination identity changes require delete plus add for audit clarity; in-place identity mutation is disallowed.

## Backward Compatibility Note

- API contract update: `accountId` is no longer accepted in request bodies for customer bucket list endpoints.
- New contract: `account_id` is supplied as a URL path parameter.
- Endpoint shape examples:
	- `POST /v1/bucket-list/{account_id}/suggestions`
	- `POST /v1/bucket-list/{account_id}/items/add`
	- `POST /v1/bucket-list/{account_id}/items/{item_id}/update`
	- `POST /v1/bucket-list/{account_id}/items/{item_id}/delete`
	- `POST /v1/bucket-list/{account_id}/view`
- Client impact: clients sending `accountId` only in JSON body must migrate to path-based account identification.
