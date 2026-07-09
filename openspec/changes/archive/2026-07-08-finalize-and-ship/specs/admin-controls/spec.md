## ADDED Requirements

### Requirement: Admin Endpoint Rate Limiting
Every admin-password-gated endpoint (auth verification, database queries, PDF upload, and remote service control) SHALL reject requests from a client that has recently exceeded a fixed number of failed admin-password attempts, without evaluating the provided password.

#### Scenario: Repeated wrong passwords lock out further attempts
- **WHEN** a client submits more than the allowed number of incorrect admin passwords to an admin-gated endpoint within the lockout window
- **THEN** further attempts from that client are rejected for the remainder of the window, without comparing the submitted password

#### Scenario: A locked-out client is rejected even with the correct password
- **WHEN** a client that has just been locked out submits the correct admin password
- **THEN** the request is still rejected, since the lockout applies before password comparison

#### Scenario: Lockout expires after the window elapses
- **WHEN** a locked-out client waits until the lockout window has elapsed and then submits the correct admin password
- **THEN** the request succeeds normally

#### Scenario: Successful authentication does not count toward lockout
- **WHEN** a client submits the correct admin password on a fresh (non-locked-out) attempt
- **THEN** that attempt does not count toward the failed-attempt threshold
