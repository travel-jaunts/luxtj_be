# customer-bucket-list Specification

## Purpose
TBD - created by archiving change add-customer-bucket-list. Update Purpose after archive.
## Requirements
### Requirement: Per-customer bucket list ownership
The system SHALL maintain exactly one bucket list per customer account identity, and each bucket list SHALL own multiple bucket list items.

#### Scenario: First item creates bucket list ownership
- **WHEN** a customer without an existing bucket list adds the first bucket list item
- **THEN** the system creates a bucket list linked to that customer account identity
- **AND** the item is persisted under that bucket list

#### Scenario: Existing ownership is reused
- **WHEN** a customer with an existing bucket list adds another item
- **THEN** the system reuses the same bucket list ownership record
- **AND** the new item is persisted in that same bucket list

### Requirement: Destination suggestion for add-item flow
The system SHALL provide destination suggestions with ideal stay day recommendations for country and city/place input flows.

#### Scenario: Country selection returns recommended cities or places
- **WHEN** the user selects a country while adding a bucket list item
- **THEN** the system returns a set of recommended cities/places within that country
- **AND** each recommendation includes an ideal number of days to stay

#### Scenario: City or place selection returns selected destination and alternatives
- **WHEN** the user selects a city or place while adding a bucket list item
- **THEN** the system returns the selected city/place with an ideal number of days to stay
- **AND** the system returns additional alternative cities/places for substitution

### Requirement: Bucket list item lifecycle operations
The system SHALL support adding, updating, deleting, and viewing bucket list items for the owning customer account.

#### Scenario: Add item persists selected destination
- **WHEN** a customer submits a selected destination and ideal stay days
- **THEN** the system persists a new bucket list item in the customer bucket list
- **AND** the persisted item is returned in the response

#### Scenario: Update item persists changed fields
- **WHEN** a customer updates an existing bucket list item
- **THEN** the system persists the updated item fields
- **AND** the updated item is returned in the response

#### Scenario: Delete item removes item from active view
- **WHEN** a customer deletes an existing bucket list item
- **THEN** the item is marked as deleted or removed from active bucket list results
- **AND** subsequent active list views do not include the deleted item

#### Scenario: View bucket list returns all active items
- **WHEN** a customer requests to view the bucket list page data
- **THEN** the system returns the list of all active bucket list items for that customer

### Requirement: Bucket list item event emission
The system SHALL emit identifying domain events when a bucket list item is created, updated, or deleted.

#### Scenario: Created event is emitted with identifiers
- **WHEN** a bucket list item is created
- **THEN** the system emits a bucket list item created domain event
- **AND** the event includes account identifier, bucket list identifier, and bucket list item identifier

#### Scenario: Updated event is emitted with identifiers
- **WHEN** a bucket list item is updated
- **THEN** the system emits a bucket list item updated domain event
- **AND** the event includes account identifier, bucket list identifier, and bucket list item identifier

#### Scenario: Deleted event is emitted with identifiers
- **WHEN** a bucket list item is deleted
- **THEN** the system emits a bucket list item deleted domain event
- **AND** the event includes account identifier, bucket list identifier, and bucket list item identifier

