# customer-personal-calendar Specification

## Purpose
TBD - synced from change add-customer-personal-calendar. Update Purpose as needed.

## Requirements
### Requirement: Per-customer personal calendar ownership
The system SHALL maintain exactly one personal calendar per customer account identity, and each personal calendar SHALL own event items and vacation/holiday period items.

#### Scenario: First calendar item creates ownership
- **WHEN** a customer without an existing personal calendar creates the first event or period item
- **THEN** the system creates a personal calendar linked to that customer account identity
- **AND** the created item is persisted under that calendar

#### Scenario: Existing ownership is reused
- **WHEN** a customer with an existing personal calendar creates another event or period item
- **THEN** the system reuses the same personal calendar ownership record
- **AND** the new item is persisted under that same calendar

### Requirement: Personal calendar supports birthday event creation
The system SHALL allow customers to create birthday events with constrained relationship type, person name, event date, and holiday preference types.

#### Scenario: Birthday event is created with valid inputs
- **WHEN** a customer submits a birthday event with `birthday_for`, `person_name`, `event_date`, and valid holiday types
- **THEN** the system persists a birthday event item for that customer personal calendar
- **AND** the response returns the created event item

#### Scenario: Birthday relation is constrained
- **WHEN** a customer submits a birthday event with `birthday_for` outside the allowed set
- **THEN** the system rejects the request with an error response
- **AND** no event item is persisted

### Requirement: Personal calendar supports anniversary event creation
The system SHALL allow customers to create anniversary events with constrained relationship type, person names, event date, and holiday preference types.

#### Scenario: Anniversary event is created with valid inputs
- **WHEN** a customer submits an anniversary event with `anniversary_for`, `person1_name`, `person2_name`, `event_date`, and valid holiday types
- **THEN** the system persists an anniversary event item for that customer personal calendar
- **AND** the response returns the created event item

#### Scenario: Missing required anniversary names is rejected
- **WHEN** a customer submits an anniversary event without either `person1_name` or `person2_name`
- **THEN** the system rejects the request with an error response
- **AND** no event item is persisted

### Requirement: Personal calendar supports special-occasion event creation
The system SHALL allow customers to create other special occasion events with event name, event date, and holiday preference types.

#### Scenario: Special occasion is created with valid inputs
- **WHEN** a customer submits an event with type `special_occasion`, `event_name`, `event_date`, and valid holiday types
- **THEN** the system persists a special occasion event item for that customer personal calendar
- **AND** the response returns the created event item

### Requirement: Personal calendar supports vacation period creation
The system SHALL allow customers to create vacation/holiday periods with period name, start date, end date, date flexibility, and holiday preference types.

#### Scenario: Vacation period is created with valid range
- **WHEN** a customer submits a period with `period_name`, `period_start`, `period_end`, `is_date_flexible`, and valid holiday types
- **THEN** the system persists a vacation period item for that customer personal calendar
- **AND** the response returns the created period item

#### Scenario: Invalid period range is rejected
- **WHEN** a customer submits a period where `period_end` is before `period_start`
- **THEN** the system rejects the request with an error response
- **AND** no period item is persisted

### Requirement: Personal calendar supports consolidated account view
The system SHALL provide a consolidated account-level view that combines personal calendar events and vacation periods.

#### Scenario: Consolidated view returns events and periods
- **WHEN** a client calls the personal calendar view endpoint for an account with saved events and periods
- **THEN** the system returns a single response containing both event and period items
- **AND** each item includes enough type metadata to distinguish event vs period

#### Scenario: Consolidated view returns empty list for account without items
- **WHEN** a client calls the personal calendar view endpoint for an account with no calendar items
- **THEN** the system returns success with an empty items list

### Requirement: Holiday preference types are constrained and bounded
The system SHALL accept holiday preference types only from the backend-controlled `HOLIDAY_TYPE_LIST`, and each created item SHALL include at most three holiday types.

#### Scenario: Holiday type list is fetchable from API
- **WHEN** a client calls the holiday-type list endpoint for personal calendar
- **THEN** the system returns the backend-defined `HOLIDAY_TYPE_LIST`
- **AND** the response can be used by clients as the allowed input set for calendar operations

#### Scenario: Valid holiday preference types are persisted
- **WHEN** a customer submits holiday types all present in the backend-provided `HOLIDAY_TYPE_LIST` with up to three selections
- **THEN** the system accepts the request
- **AND** persists the selected holiday types on the created item

#### Scenario: Invalid or excessive holiday type selections are rejected
- **WHEN** a customer submits any holiday type outside `HOLIDAY_TYPE_LIST` or more than three selections
- **THEN** the system rejects the request with an error response
- **AND** no calendar item is persisted

### Requirement: Holiday type validation is applied only where needed
The system SHALL validate holiday types on operations that consume holiday type inputs and SHALL NOT require this validation on operations that do not accept holiday types.

#### Scenario: Create event validates holiday types
- **WHEN** a client submits `POST /v1/personal-calendar/{account_id}/events/add` with invalid holiday types
- **THEN** the system rejects the request with an error response
- **AND** no event item is persisted

#### Scenario: Create period validates holiday types
- **WHEN** a client submits `POST /v1/personal-calendar/{account_id}/periods/add` with invalid holiday types
- **THEN** the system rejects the request with an error response
- **AND** no period item is persisted

#### Scenario: Fetch holiday types does not require holiday-type input validation
- **WHEN** a client calls the holiday-type list endpoint
- **THEN** the system returns the configured holiday types
- **AND** the operation succeeds without requiring holiday-type input from the caller

### Requirement: Create endpoints follow customer bucket-list API style
The system SHALL expose POST create endpoints in customer context, aligned with bucket-list routing and response conventions.

#### Scenario: Event create endpoint contract
- **WHEN** a client calls `POST /v1/personal-calendar/{account_id}/events/add` with a valid event payload
- **THEN** the system returns a success response containing the created event item
- **AND** the response uses the standard API success wrapper contract

#### Scenario: Period create endpoint contract
- **WHEN** a client calls `POST /v1/personal-calendar/{account_id}/periods/add` with a valid period payload
- **THEN** the system returns a success response containing the created period item
- **AND** the response uses the standard API success wrapper contract

#### Scenario: Holiday-type list endpoint contract
- **WHEN** a client calls `POST /v1/personal-calendar/holiday-types/view`
- **THEN** the system returns a success response containing the `HOLIDAY_TYPE_LIST`
- **AND** the response uses the standard API success wrapper contract

#### Scenario: Consolidated view endpoint contract
- **WHEN** a client calls `POST /v1/personal-calendar/{account_id}/view`
- **THEN** the system returns a success response containing consolidated event and period items
- **AND** the response uses the standard API success wrapper contract
