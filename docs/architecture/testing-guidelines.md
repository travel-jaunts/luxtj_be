# Testing Guidelines

This document defines how to write tests for the `luxtj` module. All test code must follow these rules consistently so that future context migrations do not require test rewrites.

## Toolchain

| Tool | Purpose |
| --- | --- |
| `pytest` | Test runner |
| `pytest-asyncio` | Async test support (`asyncio_mode = "auto"`) |
| `pytest-cov` | Coverage reporting |
| `pytest-dotenv` | Load `.dev.env` for integration tests that need real infra |

Install:

```bash
uv sync --group dev
```

Run:

```bash
uv run pytest                        # all tests
uv run pytest tests/luxtj/contexts  # single tree
uv run pytest -k "campaign"         # keyword filter
```

---

## Project Layout

```
tests/
  conftest.py                        # shared: CapturingEventPublisher, event_publisher, pytest_configure
  luxtj/
    bootstrap/
      conftest.py                    # client fixture (TestClient)
      test_api.py
    contexts/
      marketing/
        conftest.py                  # marketing_repo, marketing_service, make_campaign_command
        test_marketing_campaigns.py
```

Mirror the `src/luxtj/` tree under `tests/luxtj/`. Each bounded context gets its own `conftest.py`.

---

## Async Tests

`asyncio_mode = "auto"` is set in `pyproject.toml`. Every `async def test_*` function is automatically treated as an asyncio test. No decorator is needed.

```python
# correct
async def test_creates_campaign(marketing_service, make_campaign_command) -> None:
    campaign = await marketing_service.create_campaign(make_campaign_command())
    assert campaign.status == CampaignStatusEnum.DRAFT

# wrong — never use asyncio.run() in tests
def test_creates_campaign() -> None:
    asyncio.run(...)
```

Fixtures may also be `async def`:

```python
@pytest.fixture
async def seeded_repo(marketing_service, make_campaign_command):
    await marketing_service.create_campaign(make_campaign_command(name="Seed"))
    return marketing_service
```

---

## Fixture Scopes

| Scope | When to use |
| --- | --- |
| `function` (default) | Any fixture that holds mutable state (repositories, event publishers) |
| `module` | Read-only shared objects: `TestClient`, database engine |
| `session` | Truly global constants: config snapshots, large read models |

Never share a stateful fake (in-memory repository, capturing publisher) across tests. Use `function` scope for all fakes.

---

## The conftest Hierarchy

### `tests/conftest.py` — shared across all contexts

```python
class CapturingEventPublisher:
    """Fake DomainEventPublisher. Stores events for assertion."""
    events: list[BaseDomainEvent]

    async def publish(self, event) -> None: ...
    def of_type(self, event_type: str) -> list[BaseDomainEvent]: ...
    def clear(self) -> None: ...

@pytest.fixture
def event_publisher() -> CapturingEventPublisher: ...
```

`pytest_configure` sets `LTJBE_DATABASE_URL` to an in-memory SQLite URL as a safe default, so importing `luxtj.bootstrap.config` in tests never raises `KeyError`.

### Per-context `conftest.py`

Each context exposes three fixture categories:

1. **Repository** — a fresh in-memory implementation per test
2. **Service** — the application use-case class wired with the fake repository and `event_publisher`
3. **Factory** — a callable that returns a command with sensible defaults, accepting keyword overrides

```python
# tests/luxtj/contexts/marketing/conftest.py

@pytest.fixture
def marketing_repo() -> InMemoryMarketingRepository: ...

@pytest.fixture
def marketing_service(marketing_repo, event_publisher) -> MarketingService: ...

@pytest.fixture
def make_campaign_command():
    def _factory(*, name="Test", ...) -> CreateCampaignCommand: ...
    return _factory
```

Calling `make_campaign_command()` returns a valid command. Override only the fields relevant to the test case.

---

## Test Layers

### Domain tests

Location: `tests/luxtj/contexts/<context>/domain/`

Rules:
- No pytest fixtures that touch I/O, databases, or FastAPI
- Import only from `luxtj.contexts.<context>.domain` and `luxtj.shared_kernel.domain`
- Test invariants, state transitions, and event recording

```python
def test_campaign_create_records_created_event() -> None:
    campaign = MarketingCampaign.create(
        name="Alpha", channel=CampaignChannelEnum.EMAIL, ...
    )
    events = campaign.pull_events()

    assert len(events) == 1
    assert events[0].type == "com.luxtj.marketing.campaign.created.v1"

def test_pull_events_clears_the_event_list() -> None:
    campaign = MarketingCampaign.create(...)
    campaign.pull_events()
    assert campaign.pull_events() == []
```

### Application tests

Location: `tests/luxtj/contexts/<context>/`

Rules:
- Use `marketing_service`, `marketing_repo`, `event_publisher` fixtures
- No SQLAlchemy, no real HTTP
- Assert on return values and captured events

```python
async def test_create_campaign_publishes_created_event(
    marketing_service, event_publisher, make_campaign_command
) -> None:
    campaign = await marketing_service.create_campaign(make_campaign_command())

    events = event_publisher.of_type("com.luxtj.marketing.campaign.created.v1")
    assert len(events) == 1
    assert events[0].subject == str(campaign.id)
```

### Infrastructure tests

Location: `tests/luxtj/contexts/<context>/infrastructure/`

Rules:
- Test ORM row mapping (`from_domain` / `to_domain` round trips)
- Test in-memory repository contract (CRUD, ordering guarantees)
- No FastAPI, no application use cases

```python
async def test_campaign_row_round_trip_preserves_all_fields(
    marketing_service, make_campaign_command
) -> None:
    original = await marketing_service.create_campaign(make_campaign_command())
    row = MarketingCampaignRow.from_domain(original)
    restored = row.to_domain()

    assert restored.id == original.id
    assert restored.channel == original.channel
```

### Presentation tests

Location: `tests/luxtj/bootstrap/` or `tests/luxtj/contexts/<context>/presentation/`

Rules:
- Use `TestClient` from `fastapi.testclient`
- Override `Depends` via `app.dependency_overrides` to inject fakes
- Test request/response contract (status codes, JSON shape, camelCase aliases)
- Do not test business logic here

```python
def test_ping(client: TestClient) -> None:
    resp = client.post("/ping")
    assert resp.status_code == 200
    assert resp.json() == "pong"
```

For endpoint tests that need dependency overrides:

```python
@pytest.fixture
def client_with_fake_service(marketing_service):
    app = server_factory()
    app.dependency_overrides[build_marketing_service] = lambda: marketing_service
    with TestClient(app) as c:
        yield c
```

---

## Parametrize

Use `pytest.mark.parametrize` for:
- Boundary conditions (empty list, single item, many items)
- Enum variants
- Invalid inputs that should raise

```python
@pytest.mark.parametrize(
    "audience_ids,expected_count",
    [
        (["user-1"], 1),
        (["user-1", "user-2"], 2),
        (["user-1", "user-1"], 1),   # deduplication
    ],
    ids=["single", "multiple", "deduplication"],
)
async def test_audience_deduplication(
    marketing_service, make_campaign_command, audience_ids, expected_count
) -> None:
    campaign = await marketing_service.create_campaign(
        make_campaign_command(audience_user_ids=audience_ids)
    )
    assert len(campaign.audience) == expected_count
```

Always supply `ids=` so test output is readable without inspecting the parameter values.

To parametrize over all values of an enum:

```python
@pytest.mark.parametrize(
    "channel",
    list(CampaignChannelEnum),
    ids=[c.value for c in CampaignChannelEnum],
)
async def test_row_round_trip_for_all_channels(..., channel): ...
```

---

## Event Assertions

Use `CapturingEventPublisher.of_type()` to filter by type before asserting, rather than asserting on `events[0]` by index. This makes tests resilient to multiple events from a single operation.

```python
# preferred
events = event_publisher.of_type("com.luxtj.marketing.campaign.created.v1")
assert len(events) == 1

# fragile
assert event_publisher.events[0].type == "..."
```

Assert the CloudEvent contract (type, subject, data fields) for events that are integration contracts:

```python
event = events[0]
assert event.type == "com.luxtj.marketing.campaign.created.v1"
assert event.source == "/luxtj/marketing/campaigns"
assert event.subject == str(campaign.id)
assert event.data["id"] == str(campaign.id)
```

---

## Fakes Over Mocks

Prefer hand-written fakes over `unittest.mock.patch` or `MagicMock`.

| Approach | When to use |
| --- | --- |
| `InMemoryMarketingRepository` | All application and infrastructure tests |
| `CapturingEventPublisher` | All tests that assert on domain events |
| `MockMarketingAudienceResolver` | Tests of `_resolve_audience` that need segment lookup |
| `unittest.mock.patch` | Only for stdlib or third-party functions with no seam (e.g., `datetime.now`) |

Mocks couple tests to implementation details. Fakes let you test behaviour.

---

## Naming

```
test_<unit>_<condition>_<expected_outcome>
```

Examples:

```
test_create_campaign_persists_and_returns_draft
test_create_campaign_publishes_created_event
test_campaign_row_round_trip_preserves_all_fields
test_audience_deduplication  (with parametrize ids for the conditions)
```

Do not include `should`, `verify`, or `check` — the word `test` already signals intent.

---

## What Not To Test

- Python built-in behaviour (dict deduplication, list ordering)
- Third-party library internals (SQLAlchemy session behaviour)
- Configuration constants (`VERSION`, `ENVIRONMENT`)
- Private helper functions — test through the public interface

---

## Coverage Expectations

| Layer | Target |
| --- | --- |
| Domain | 100% line + branch coverage |
| Application use cases | 100% line coverage |
| Infrastructure (ORM mapping) | 100% of `from_domain` / `to_domain` paths |
| Presentation (HTTP) | Critical paths: success, validation error, not-found |

Coverage is reported automatically via `pytest-cov`. Run `uv run pytest --cov-report=html` for an HTML report.
