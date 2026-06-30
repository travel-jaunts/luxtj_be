## 1. Context Skeleton and Contracts

- [x] 1.1 Create account context package structure for domain, application, infrastructure, and presentation layers.
- [x] 1.2 Define domain entities/value objects for Account and OtpChallenge with invariants for expiry, attempts, and one-time consumption.
- [x] 1.3 Define application ports for account repository, otp challenge repository, sms sender, token issuer, and clock.
- [x] 1.4 Define command/query DTOs and use case interfaces for signup/login request-otp and verify-otp flows.

## 2. PostgreSQL Persistence and Migration

- [x] 2.1 Add SQLAlchemy models for account and otp challenge tables with PostgreSQL-friendly column types and indexes.
- [x] 2.2 Add unique constraint/index for dial_code plus phone_number identity.
- [x] 2.3 Add Alembic migration to create account and otp challenge tables with required constraints.
- [x] 2.4 Implement async SQLAlchemy repository adapters for account lookup/create/update and otp challenge create/find/consume/attempt updates.

## 3. Auth Use Cases and Security Rules

- [x] 3.1 Implement request-otp use cases for signup and login.
- [x] 3.2 Implement OTP generation, salting/hashing, TTL evaluation, and attempt budget enforcement.
- [x] 3.3 Implement verify-otp use case to validate challenge state, consume successful challenge, and reject invalid or expired OTP.
- [x] 3.4 Implement login verify auto-create behavior for unknown phone identities and duplicate-safe existing-account handling.
- [x] 3.5 Implement email backfill behavior to update email only when existing email is empty and request email is present.

## 4. External Adapters and Configuration

- [x] 4.1 Add Twilio SDK dependency and implement Twilio SMS adapter for OTP delivery behind sms sender port.
- [x] 4.2 Implement token issuer adapter that returns access and refresh tokens only, with configurable expiries and signing secrets.
- [x] 4.3 Add auth and Twilio environment configuration entries and startup wiring safeguards.
- [x] 4.4 Add bootstrap dependency providers to wire repositories, adapters, and use cases.

## 5. HTTP Endpoints and API Wiring

- [x] 5.1 Add public auth router endpoints for signup request-otp, login request-otp, and verify-otp.
- [x] 5.2 Implement request and response serializers ensuring verify response includes token pair and excludes account profile payload.
- [x] 5.3 Register the new auth router under public v1 API surface.
- [x] 5.4 Ensure no account CRUD routes are introduced in this change.

## 6. Testing and Readiness

- [x] 6.1 Add unit tests for OTP security rules (hashing workflow, expiry, attempts, and one-time consume semantics).
- [x] 6.2 Add use case tests for login auto-create and email backfill logic.
- [x] 6.3 Add API integration tests for request-otp and verify-otp happy and failure paths with mocked SMS sender.
- [x] 6.4 Add migration and repository tests validating PostgreSQL constraints and duplicate identity handling.
- [x] 6.5 Run test suite and lint checks for touched modules.
