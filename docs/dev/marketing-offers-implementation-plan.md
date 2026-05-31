# Implementation Plan: Marketing Offers Feature

## Context

The marketing context currently supports Campaigns. This adds a parallel aggregate — **Offers** — covering all promotions and incentives (coupons, discounts, referral codes). The feature is scoped to creation and lifecycle management only; "apply offer to cart" is explicitly deferred.

Follows the same DDD + hexagonal architecture as `MarketingCampaign`.

---

## Files to Create or Modify

### 1. Domain Layer

#### `src/luxtj/contexts/marketing/domain/enums.py` — MODIFY
Add two new enums alongside existing campaign enums:
```
OfferTypeEnum:   Flat | PercentageOff | Bundle | Referral
OfferStatusEnum: Active | Expired | Paused | Rescinded | Deleted
```

#### `src/luxtj/contexts/marketing/domain/errors.py` — MODIFY
Add offer-specific error hierarchy:
```
OfferDomainError(MarketingDomainError)
OfferPolicyViolationError(OfferDomainError)
```

#### `src/luxtj/contexts/marketing/domain/offer_policies.py` — CREATE
Mirror pattern of `domain/policies.py`:
- `OfferCreationContext(frozen dataclass)` — carries all inputs for policy evaluation
- Abstract `OfferPolicy` base with `enforce(context)` method
- `ValidityDatesPolicy` — start_date must be in future, end_date > start_date
- `DiscountValuePolicy` — value > 0; if type is PercentageOff, value ≤ 100
- `OfferCreationPolicies` — composite: runs all policies via `enforce_all()`

#### `src/luxtj/contexts/marketing/domain/offer.py` — CREATE
`Offer` aggregate root (dataclass):

Fields:
- `id: UUID`
- `name: str`
- `code: str`
- `type: OfferTypeEnum`
- `discount_value: float`
- `min_booking_value: float`
- `min_booking_value_currency: str`
- `validity_start: datetime`
- `validity_end: datetime`
- `usage_limit_per_user: int | None` (None = unlimited)
- `applicability_on: list[str]`
- `stackable: bool`
- `auto_apply: bool`
- `status: OfferStatusEnum`
- `created_at: datetime`
- `updated_at: datetime`
- `deleted_at: datetime | None`
- `_events: list` (init=False, repr=False)

Methods:
- `create(...)` — class factory: enforces policies, sets `status=Active`, sets timestamps, generates code if null (8-char UUID hex slug)
- `pause()` — sets `status=Paused`, updates `updated_at`; raises `OfferPolicyViolationError` if not Active
- `rescind()` — sets `status=Rescinded`, updates `updated_at`; raises error if already Deleted
- `delete()` — soft delete: sets `status=Deleted`, `deleted_at=now`, `updated_at=now`; idempotent guard
- `record_event()`, `pull_events()` — standard event journal methods

#### `src/luxtj/contexts/marketing/domain/events.py` — MODIFY
Add four offer events following existing CloudEvents pattern:
- `OfferCreated`, `OfferPaused`, `OfferRescinded`, `OfferDeleted`
- Each has `from_offer(offer: Offer)` factory
- Event types: `com.luxtj.marketing.offer.created.v1`, etc.

---

### 2. Application Layer

#### `src/luxtj/contexts/marketing/application/commands.py` — MODIFY
Add frozen dataclasses:
- `CreateOfferCommand` — all creation fields (mirrors domain inputs)
- `SearchOffersCommand` — `name: str | None`, `status: OfferStatusEnum | None`, `type: OfferTypeEnum | None`
- `PauseOfferCommand` — `offer_id: UUID`
- `RescindOfferCommand` — `offer_id: UUID`
- `DeleteOfferCommand` — `offer_id: UUID`

#### `src/luxtj/contexts/marketing/application/ports.py` — MODIFY
Add `OfferRepository(Protocol)`:
- `add(offer: Offer) -> None`
- `get_by_id(offer_id: UUID) -> Offer` (raises `KeyError` if not found)
- `search(name: str | None, status: OfferStatusEnum | None, type: OfferTypeEnum | None) -> list[Offer]`
- `save(offer: Offer) -> None`

#### `src/luxtj/contexts/marketing/application/use_cases.py` — MODIFY
Add new `OffersService` class (separate from `MarketingService` to avoid coupling):
- Constructor: `__init__(self, repository: OfferRepository, event_publisher: DomainEventPublisher)`
- `create_offer(command) -> Offer`
- `search_offers(command) -> list[Offer]`
- `pause_offer(command) -> Offer`
- `rescind_offer(command) -> Offer`
- `delete_offer(command) -> Offer`

Pattern: fetch → mutate domain → save → flush events → return entity.

#### `src/luxtj/contexts/marketing/application/public.py` — MODIFY
Export `OffersService`, `OfferRepository`, all five commands, and `Offer`.

---

### 3. Infrastructure Layer

#### `src/luxtj/contexts/marketing/infrastructure/persistence/sqlalchemy_models.py` — MODIFY
Add `MarketingOfferRow(MarketingBase)`:
- Table: `marketing_offers`
- Columns mirror all Offer fields; `applicability_on` as `JSON`
- Static methods: `from_domain(offer)`, `to_domain(row)`, `update_from_domain(row, offer)`

#### `src/luxtj/contexts/marketing/infrastructure/persistence/sqlalchemy_repository.py` — MODIFY
Add `SqlAlchemyOfferRepository` implementing `OfferRepository`:
- `add`: insert new row
- `get_by_id`: SELECT by id, raise `KeyError` if missing
- `search`: SELECT with optional LIKE on name, exact filter on status/type, exclude Deleted records by default
- `save`: update existing row via `update_from_domain()`

#### `src/luxtj/contexts/marketing/infrastructure/persistence/in_memory.py` — MODIFY
Add `InMemoryOfferRepository` for testing, mirroring `InMemoryMarketingRepository`.

#### `alembic/versions/<timestamp>_add_marketing_offers_table.py` — CREATE
New migration: `marketing_offers` table with all columns, indexes on `(status)` and `(code)` (unique).

---

### 4. Presentation Layer

#### `src/luxtj/contexts/marketing/presentation/http/schemas.py` — MODIFY
Add:
- `CreateOfferBody` — Pydantic request model for offer creation
- `SearchOffersBody` — optional name/status/type filters
- `OfferSerializer` — response model with `from_offer(offer: Offer)` factory

#### `src/luxtj/contexts/marketing/presentation/http/routes/offer_commands.py` — CREATE
```
POST   /offers/create                → create_offer
POST   /offers/{offer_id}/pause      → pause_offer
POST   /offers/{offer_id}/rescind    → rescind_offer
POST   /offers/{offer_id}/delete     → delete_offer (soft)
```
- Each returns `ApiSuccessResponse[OfferSerializer]`
- Catches `OfferDomainError`, returns `ApiErrorResponse`

#### `src/luxtj/contexts/marketing/presentation/http/routes/offer_queries.py` — CREATE
```
POST /offers/search  → search_offers
```
Returns `ApiSuccessResponse[list[OfferSerializer]]`

#### `src/luxtj/contexts/marketing/presentation/http/router.py` — MODIFY
Register `offers_router` under the existing `marketing_router`.

---

### 5. Bootstrap

#### `src/luxtj/contexts/marketing/bootstrap.py` — MODIFY
Add FastAPI Depends factories:
- `build_offer_repository(session: AsyncSession) -> SqlAlchemyOfferRepository`
- `build_offers_service(session: AsyncSession) -> OffersService` (composes repo + outbox publisher)

---

## Execution Order

1. Domain enums → errors → policies → offer entity → events
2. Application commands → ports → use cases → public exports
3. Infrastructure models → repositories (SQLAlchemy + in-memory)
4. Alembic migration
5. Presentation schemas → routes (commands + queries)
6. Router registration
7. Bootstrap factories

---

## Verification

1. **Alembic**: `alembic upgrade head` — migration applies cleanly
2. **Server start**: `uvicorn` starts without import errors
3. **Create offer** (manual POST): valid payload returns 200 with `status=Active` and auto-generated code
4. **Create offer (manual code)**: provide explicit code — verify it is preserved
5. **Validation**: past start_date → returns domain error; percentage > 100 → domain error
6. **Pause**: POST `/offers/{id}/pause` → status becomes Paused
7. **Rescind**: POST `/offers/{id}/rescind` → status becomes Rescinded
8. **Delete**: POST `/offers/{id}/delete` → status=Deleted, `deleted_at` populated, record still in DB
9. **Search**: filter by name substring, by status, by type — returns matching results; deleted offers excluded by default
