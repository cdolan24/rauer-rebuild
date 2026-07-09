# admin-controls

## Purpose
TBD - defines admin-page capabilities for operating and inspecting the running application, restricted to authenticated admins.

## Requirements

### Requirement: Remote Service Control
An authenticated admin SHALL be able to start, stop, and restart the backend and frontend services from the admin page, without shell access to the host.

#### Scenario: Restarting the backend from the admin page
- **WHEN** an authenticated admin triggers a restart of the backend service
- **THEN** the backend service is restarted and the admin page reflects its updated status

#### Scenario: Service control is unavailable without authentication
- **WHEN** an unauthenticated request attempts to control a service
- **THEN** the request is rejected and no service state changes

### Requirement: Direct Database Access
An authenticated admin SHALL be able to run arbitrary SQL against the application database from the admin page and see the results.

#### Scenario: Running a query from the admin page
- **WHEN** an authenticated admin submits a SQL statement from the database browser
- **THEN** the statement is executed against the application database and its results (or row-count effect, for a non-SELECT statement) are displayed

#### Scenario: Database access is unavailable without authentication
- **WHEN** an unauthenticated request attempts to run a query
- **THEN** the request is rejected and no query is executed

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
