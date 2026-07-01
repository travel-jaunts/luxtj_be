# account-otp-auth

## Purpose

Defines the OTP-based authentication API endpoints and flows for phone-based signup and login with automatic account creation on first login.

## Requirements

### Requirement: Request OTP for phone-based auth flows
The system SHALL provide POST endpoints to request OTP for signup and login experiences using dial code and phone number as required inputs, with email optional only for signup-related paths.

#### Scenario: Request signup OTP
- **WHEN** a client submits dial code and phone number to signup request-otp with optional email
- **THEN** the system creates an OTP challenge for signup and sends OTP through the configured SMS provider

#### Scenario: Request login OTP
- **WHEN** a client submits dial code and phone number to login request-otp
- **THEN** the system creates an OTP challenge for login and sends OTP through the configured SMS provider

### Requirement: Verify OTP and issue token pair only
The system SHALL verify OTP challenges and return only authentication token data, including access token and refresh token, without account profile data.

#### Scenario: Successful verify response shape
- **WHEN** a valid OTP is submitted with dial code and phone number to verify endpoint
- **THEN** the response includes access token and refresh token fields and excludes account profile payload

#### Scenario: Invalid OTP
- **WHEN** an incorrect OTP is submitted for an active challenge
- **THEN** the system rejects verification and decrements remaining attempts for that challenge

#### Scenario: Expired OTP
- **WHEN** an OTP challenge is past its expiration time
- **THEN** the system rejects verification and does not issue tokens

### Requirement: Auto-create account during login verify when phone is absent
The system SHALL create an account automatically during login OTP verification when no account exists for the provided phone identity, and SHALL continue by issuing tokens in the same flow.

#### Scenario: Login verify with unknown phone
- **WHEN** a valid login OTP is verified for a dial code and phone number that has no account record
- **THEN** the system creates a new account and returns access and refresh tokens

#### Scenario: Login verify with existing phone
- **WHEN** a valid login OTP is verified for a dial code and phone number that already exists
- **THEN** the system does not create a duplicate account and returns access and refresh tokens

### Requirement: Exclude account CRUD endpoints from this change
The system SHALL NOT expose create, read, update, or delete account management APIs as part of this change.

#### Scenario: Auth route surface remains limited
- **WHEN** API routes for this capability are registered
- **THEN** only request-otp and verify-otp auth endpoints are added for account flows
