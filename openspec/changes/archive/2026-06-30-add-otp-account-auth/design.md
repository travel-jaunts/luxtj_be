## Context

The current public API has no account identity or OTP authentication module. The repository follows a modular monolith with DDD and hexagonal layering, where contexts expose application use cases and infrastructure adapters implement ports. The new change must remain minimal in scope while adding secure phone OTP signup/login behavior, Twilio SMS delivery, token issuance, and PostgreSQL-backed persistence.

Constraints:
- Asynchronous Python implementation style.
- Existing API response envelope conventions and POST-only route policy.
- No account CRUD API exposure in this change.
- Verify response must include access and refresh tokens only.
- No strict anti-enumeration behavior is required.

## Goals / Non-Goals

**Goals:**
- Introduce phone OTP flows for signup and login experiences.
- Issue access plus refresh tokens on successful OTP verification.
- Auto-create account when login verify is completed for a phone number not found in storage.
- Persist account and OTP challenge state in PostgreSQL via SQLAlchemy repositories.
- Backfill email when account email is empty and a new email is provided during verification.

**Non-Goals:**
- Implement account CRUD HTTP APIs.
- Implement social login, password login, or MFA chaining.
- Introduce strict anti-enumeration equalized responses/timing.
- Introduce external identity provider integration in this iteration.

## Decisions

### Decision 1: Create a dedicated account auth capability in a new context slice
- Choice: Add an account-focused context with domain entities for Account and OtpChallenge, application use cases for request and verify flows, and HTTP routes under public v1 auth surface.
- Rationale: Aligns with existing modular-monolith context pattern and keeps auth behavior isolated from admin_api mock user services.
- Alternatives considered:
  - Extend admin_api customer users module: rejected because it is admin-oriented and currently mock-backed.
  - Put logic directly in router/service layers: rejected because it bypasses current context architecture.

### Decision 2: Use PostgreSQL-backed SQLAlchemy repositories for account and OTP challenge ports
- Choice: Implement repository adapters with async SQLAlchemy session dependencies and add Alembic migration for account and otp challenge tables.
- Rationale: Matches existing persistence style and keeps domain/application independent of storage concerns.
- Alternatives considered:
  - In-memory only: rejected because auth state and OTP verification require durability.
  - Redis-only OTP storage: deferred to reduce moving parts for initial release.

### Decision 3: OTP verification returns token pair only
- Choice: Verify endpoint returns access_token, refresh_token, token_type, and expiry metadata; no account profile payload.
- Rationale: Meets explicit requirement and keeps response minimal.
- Alternatives considered:
  - Return account profile with tokens: rejected per requirement.

### Decision 4: Account creation and email update policy at verify time
- Choice: For login verify, if phone identity does not exist, create account and continue issuing tokens. If account exists and stored email is empty, update email when provided in verify request.
- Rationale: Meets onboarding continuity requirement while avoiding duplicate records.
- Alternatives considered:
  - Create account only in signup flow: rejected because requirement states login should continue by auto-creating when missing.
  - Never mutate email during verify: rejected because requirement asks to update empty email.

### Decision 5: Twilio as SMS adapter behind application port
- Choice: Add SmsOtpSender port with Twilio implementation and environment-based credential configuration.
- Rationale: Keeps external dependency isolated and testable by port mocking.
- Alternatives considered:
  - Direct Twilio calls from use case: rejected because it couples application to vendor SDK.

### Decision 6: Security baseline with pragmatic constraints
- Choice: Hash OTP at rest, enforce TTL and attempt limits, consume OTP once, and apply basic request throttling; allow explicit account-not-found signaling where flow requires it.
- Rationale: Keeps implementation simple but secure, while honoring no strict anti-enumeration constraint.
- Alternatives considered:
  - Plaintext OTP storage: rejected for security risk.
  - No throttling: rejected due to abuse risk.

## Risks / Trade-offs

- [OTP abuse/spam risk] -> Mitigation: phone/IP throttling and cooldown windows for request-otp endpoints.
- [Twilio delivery latency or failures] -> Mitigation: timeout/retry policy and operational logging with non-sensitive error responses.
- [Token theft risk] -> Mitigation: short-lived access token, signed refresh token, secret rotation plan.
- [Enumeration leakage due to explicit not-found responses] -> Mitigation: accept as intentional trade-off for current phase; revisit if threat posture changes.
- [Race conditions on verify/create] -> Mitigation: unique phone constraint and transactional verify-create flow.

## Migration Plan

1. Add account and otp challenge SQLAlchemy models and Alembic migration with PostgreSQL-friendly indexes and unique constraints.
2. Add application ports/use cases and infrastructure adapters (repositories, Twilio sender, token issuer).
3. Add public auth routes for request-otp and verify-otp.
4. Wire bootstrap dependencies and include router in public v1 API.
5. Add tests with mocked Twilio sender and deterministic clock/token fixtures.
6. Roll out behind environment configuration readiness checks.

Rollback strategy:
- Revert API route registration and application wiring.
- Roll back migration if no dependent data is required; otherwise keep tables and disable endpoints via deployment switch.

## Open Questions

- Refresh token lifetime and rotation policy (single-use vs multi-use) for first release.
- Whether Twilio Verify API should be adopted later instead of custom OTP generation and hashing.
