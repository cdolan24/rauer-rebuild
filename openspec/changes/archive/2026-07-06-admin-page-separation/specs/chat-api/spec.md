## ADDED Requirements

### Requirement: Admin Password Verification Endpoint
The system SHALL expose an endpoint to verify an admin password without performing any other action, using the same check as the upload endpoint.

#### Scenario: Verifying a correct admin password
- **WHEN** a client sends `POST /api/auth/verify` with the correct admin password
- **THEN** the system returns a success response

#### Scenario: Verifying an incorrect or missing admin password
- **WHEN** a client sends `POST /api/auth/verify` with a missing or incorrect admin password, or no admin password is configured
- **THEN** the system returns a 401 response
