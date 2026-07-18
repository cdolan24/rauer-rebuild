## MODIFIED Requirements

### Requirement: Admin Endpoint Rate Limiting
Every admin-password-gated endpoint (auth verification, database queries, PDF upload, remote service control, and entity merge review) SHALL reject requests from a client that has recently exceeded a fixed number of failed admin-password attempts, without evaluating the provided password.

#### Scenario: Repeated wrong passwords lock out further attempts
- **WHEN** a client submits more than the allowed number of incorrect admin passwords to an admin-gated endpoint within the lockout window
- **THEN** further attempts from that client are rejected for the remainder of the window, without comparing the submitted password

#### Scenario: A locked-out client is rejected even with the correct password
- **WHEN** a client that has just been locked out submits the correct admin password
- **THEN** the request is still rejected, since the lockout applies before password comparison
