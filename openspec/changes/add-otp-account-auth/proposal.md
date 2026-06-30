## Why

The public API currently has no account identity flow for phone-based signup and authentication, which blocks a simple user onboarding and return-login experience. A minimal OTP-first module is needed now to ship signup and login flows with secure token issuance while keeping implementation scope small.

## What Changes

- Add a new OTP-based account authentication capability using phone number and dial code as the primary identity.
- Add request-otp endpoints for signup and login.
- Add an OTP verify endpoint that returns only access and refresh tokens (no account profile payload).
- Add automatic account creation during verify when the phone number does not already exist.
- For existing accounts, avoid duplicate account creation and continue login flow.
- Support optional email in signup flow and update account email when stored email is empty and a new email is provided during verify.
- Implement Twilio SMS integration for OTP delivery.
- Implement repository and persistence using PostgreSQL-backed SQLAlchemy adapters.
- Do not add account CRUD APIs in this change.

## Capabilities

### New Capabilities
- account-otp-auth: Phone OTP-based signup, login, OTP verification, and token issuance.
- account-identity-store: Minimal account persistence and OTP challenge persistence on PostgreSQL for auth flows.

### Modified Capabilities
- None.

## Impact

- API: new public auth endpoints under v1 auth surface for request-otp and verify-otp.
- Domain/application: new account/auth use cases, OTP challenge lifecycle, token issuance interfaces.
- Infrastructure: Twilio SMS sender adapter, JWT token issuer, PostgreSQL repository implementations, Alembic migration for account and OTP challenge tables.
- Dependencies/config: add Twilio SDK, new auth and OTP environment variables (token secrets, TTLs, Twilio credentials).
- Security: OTP hashing, expiration, attempt limits, one-time consume semantics, and basic request throttling policy.
