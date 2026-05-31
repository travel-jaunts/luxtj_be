# Action Centre — Implementation Plan

## Context

The admin dashboard needs an **Action Centre** page that surfaces pending approvals (KYC, Content, and future workflows) as clickable cards. Each card shows a count for one workflow; clicking it deep-links to the relevant filtered list page in the dashboard. Today there is no unified source for "what is awaiting an admin's attention" — each workflow owns its own pending state, and the dashboard would have to fan out N calls to show a summary. This epic introduces a single, workflow-agnostic backend surface that any future approval workflow can plug into, plus a read model that keeps the dashboard fast.

Driving principles (per `.claude/CLAUDE.md`): build the minimum that solves the problem, make the contract explicit, and keep workflows decoupled from the Action Centre.

## Design decisions (confirmed)

- **Delivery**: REST polling. Dashboard calls one endpoint on an interval.
- **Granularity**: Aggregated cards per workflow (count + metadata). No per-item payload in v1.
- **Source of truth**: Materialised `action_centre_items` table, written by event projectors.
- **Deep links**: Backend returns `workflow` key + optional `filter` payload. Frontend owns the route map.

## Architecture

```
┌──────────────┐  domain event   ┌────────────────┐   upsert    ┌──────────────────────┐
│ KYC module   │ ───────────────▶│  ActionCentre  │ ──────────▶ │ action_centre_items  │
│ Content mod. │   (pending /    │   projector    │             │ (workflow, entity_id,│
│ <future>     │    resolved)    │ (event handler)│             │  status, created_at) │
└──────────────┘                 └────────────────┘             └──────────┬───────────┘
                                                                            │ aggregate
                                                                            ▼
                                                          GET /action-centre/summary
                                                                            │
                                                                            ▼
                                                                  Dashboard cards
```

### Contracts

**Event (internal, raised by each workflow):**
```json
{
  "event": "action_centre.item.pending" | "action_centre.item.resolved",
  "workflow": "kyc_approval",
  "entity_id": "uuid",
  "occurred_at": "iso8601",
  "metadata": { "priority": "normal", "assignee_role": "compliance_admin" }
}
```

Workflows raise these two events only. They never write to the Action Centre table directly.

**API: `GET /api/v1/action-centre/summary`**

Response:
```json
{
  "cards": [
    {
      "workflow": "kyc_approval",
      "label": "KYC Approvals",
      "count": 12,
      "oldest_pending_at": "2026-05-30T09:12:00Z",
      "filter": { "status": "pending" }
    },
    {
      "workflow": "content_review",
      "label": "Content Reviews",
      "count": 5,
      "oldest_pending_at": "2026-05-31T14:00:00Z",
      "filter": { "status": "pending" }
    }
  ],
  "generated_at": "2026-06-01T10:00:00Z"
}
```

The dashboard maintains a static map `{workflow → route}` (e.g. `kyc_approval → /admin/kyc?status=pending`) and constructs the URL using `filter` as query params. Adding a new workflow = one map entry on the frontend + one event producer on the backend.

### Data model

`action_centre_items`
| column            | type        | notes                                  |
|-------------------|-------------|----------------------------------------|
| id                | uuid (pk)   |                                        |
| workflow          | text        | indexed                                |
| entity_id         | text        | unique together with workflow          |
| status            | enum        | `pending` \| `resolved`                |
| metadata          | jsonb       | priority, assignee role, etc.          |
| created_at        | timestamptz |                                        |
| resolved_at       | timestamptz | nullable                               |

Index: `(workflow, status)` for the summary aggregate.

`workflow_registry` (config, not necessarily a table — can be a Python enum/dict):
- `workflow` key → human-readable `label`. Used to populate `cards[].label` so the dashboard doesn't hardcode display strings.

## Implementation steps

1. **Domain module: `action_centre`** (new modular-monolith module per `docs/architecture/modular-monolith-ddd-hexagonal.md`)
   - `domain/`: `ActionItem` aggregate, `Workflow` value object, `Status` enum.
   - `application/`: `RecordPendingItem`, `ResolveItem`, `GetSummary` use cases (async).
   - `infrastructure/`: SQLAlchemy async repo for `action_centre_items`; in-process event subscriber.
   - `interfaces/http/`: FastAPI router exposing `GET /api/v1/action-centre/summary`.

2. **Event contract**
   - Define `ActionCentrePendingEvent` / `ActionCentreResolvedEvent` in a shared `events` package.
   - Document the contract; each workflow module imports and publishes via the existing async event bus.

3. **Projector**
   - Async handler subscribes to both events. Upserts on pending, marks resolved on resolved. Idempotent on `(workflow, entity_id)`.

4. **Workflow producers** (one PR per workflow, can ship independently)
   - KYC module raises `pending` when a KYC enters review, `resolved` on approve/reject.
   - Content module raises `pending` on submission, `resolved` on moderation decision.

5. **Workflow registry**
   - Add a config dict mapping `workflow → label` consumed by `GetSummary`.

6. **Backfill**
   - One-off async script: for each registered workflow, query its existing pending rows and emit `pending` events so the read model is hydrated on first deploy.

## Critical files to create / touch

- `src/modules/action_centre/` (new module — full DDD layout)
- `src/shared/events/action_centre.py` (event dataclasses)
- `src/modules/kyc/.../approval_service.py` (publish events)
- `src/modules/content/.../moderation_service.py` (publish events)
- Alembic migration for `action_centre_items`
- `scripts/backfill_action_centre.py`

(Exact paths depend on the repo's module layout — to be confirmed during implementation when reading the codebase.)

## Marking items as completed

Items are **not** marked complete by the Action Centre directly — completion is derived from the owning workflow.

Flow:
1. Admin clicks the KYC card → lands on the KYC page → approves/rejects a KYC.
2. The KYC module emits `action_centre.item.resolved` as part of that transaction (same unit of work as the status change).
3. The projector flips the `action_centre_items` row to `resolved` and stamps `resolved_at`.
4. Next `GET /summary` poll reflects the lower count.

**Why this way:** the workflow owns truth. If the Action Centre had its own "dismiss" endpoint, an item could be marked done in the centre while still pending in KYC — silent drift. Tying resolution to the workflow's terminal transition makes the two impossible to desync.

**Edge cases the projector must handle:**
- **Idempotency**: upsert on `(workflow, entity_id)`; a duplicate `resolved` event is a no-op.
- **Out-of-order delivery**: if `resolved` arrives before `pending`, create the row in `resolved` state so a late `pending` doesn't resurrect it. Use `occurred_at` to break ties.
- **Bulk actions**: one event per entity, even when an admin approves N items at once. Keeps the contract uniform and the projector simple.

## Out of scope (v1)

- Per-item drill / inline preview list.
- Push delivery (SSE/WebSocket).
- Per-user assignment, snoozing, dismissal.
- Notification persistence beyond "pending vs resolved".

## Verification

1. **Unit**: projector upsert + resolve is idempotent across duplicate events.
2. **Integration**: publish a `pending` event → row appears → `GET /summary` count increments → publish `resolved` → count decrements.
3. **Backfill**: run script against a seeded DB with N pending KYCs; confirm `count == N`.
4. **End-to-end (manual)**: in the dashboard, trigger a KYC submission, poll `GET /summary`, click the card, confirm it lands on `/admin/kyc?status=pending`.
