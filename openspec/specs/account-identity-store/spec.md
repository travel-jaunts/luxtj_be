# account-identity-store

## Purpose

Defines the persistent storage layer for account identity records and OTP challenge lifecycle management in PostgreSQL, with SQLAlchemy async adapters.

## Requirements

### Requirement: Persist account identity in PostgreSQL
The system SHALL persist account identity using PostgreSQL-backed repositories with SQLAlchemy async adapters, storing account id, dial code, phone number, and optional email.

#### Scenario: Create account record
- **WHEN** account creation is triggered by a valid verify flow
- **THEN** the repository stores a new account row with unique phone identity and generated UUID

#### Scenario: Prevent duplicate phone identities
- **WHEN** account creation is attempted for an existing dial code and phone number
- **THEN** the repository enforces uniqueness and returns existing account semantics to application logic

### Requirement: Persist OTP challenge lifecycle securely
The system SHALL store OTP challenge records in PostgreSQL with hashed OTP values, expiration timestamp, attempt tracking, and one-time consumption state.

#### Scenario: Store challenge
- **WHEN** request-otp is processed
- **THEN** the repository stores an OTP challenge record with hash, expiry, and initial attempt budget

#### Scenario: Consume challenge once
- **WHEN** OTP verification succeeds
- **THEN** the repository marks the challenge as consumed and prevents re-use

### Requirement: Backfill email only when existing email is empty
The system SHALL update account email during verify only when a non-empty email is provided and the existing account email is empty.

#### Scenario: Email backfill on existing account
- **WHEN** verify succeeds for an existing account with empty email and request contains email
- **THEN** the repository updates the account email with the provided value

#### Scenario: Preserve non-empty email
- **WHEN** verify succeeds for an existing account with non-empty email and request contains a different email
- **THEN** the repository keeps the existing email unchanged
