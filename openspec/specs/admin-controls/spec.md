# admin-controls

## Purpose
Defines admin-page capabilities for operating and inspecting the running application, restricted to authenticated admins: starting/stopping/restarting services, running direct database queries, configuring the chat backend, and rate-limiting repeated failed authentication attempts.

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
Every admin-password-gated endpoint (auth verification, database queries, PDF upload, remote service control, entity merge review, and chat backend configuration) SHALL reject requests from a client that has recently exceeded a fixed number of failed admin-password attempts, without evaluating the provided password.

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

#### Scenario: Distinct clients reaching the app through the required reverse proxy are rate-limited independently
- **WHEN** two different real clients each submit repeated wrong admin passwords through the app's mandatory reverse-proxy front end (see `deployment`'s network-exposure requirement), where every request's raw connection source is the proxy itself rather than the original client
- **THEN** each client's lockout state is tracked using the client address the proxy forwards, not the proxy's own address, so one client's lockout does not also lock out the other

### Requirement: Chat Backend Configuration
An authenticated admin SHALL be able to view the currently configured chat backend (Ollama or hosted API), whether a hosted API key is currently set, and whether a GPU is detected on the host, and SHALL be able to submit a new chat backend choice (and, for the hosted option, a model name and/or API key) that is written to the application config file.

#### Scenario: Viewing current chat backend configuration
- **WHEN** an authenticated admin opens the chat backend section of the admin page
- **THEN** the page shows the currently active chat backend, whether a hosted API key is set (never the key itself), and whether a GPU was detected on the host

#### Scenario: Saving a new chat backend choice
- **WHEN** an authenticated admin submits a new chat backend selection from the admin page
- **THEN** the selection (and any submitted hosted-API model or API key) is written to the application config file, and the response indicates a restart is required for it to take effect

#### Scenario: Submitting a hosted backend selection without a new API key
- **WHEN** an authenticated admin submits a hosted-API backend selection with the API key field left blank, and a key was already configured
- **THEN** the previously configured API key is preserved unchanged rather than cleared

#### Scenario: Selecting local Ollama chat generation with no GPU detected
- **WHEN** an authenticated admin selects the local Ollama chat backend while no GPU is detected on the host
- **THEN** the admin page shows a warning about this being the slow/fragile CPU-only path, without preventing the selection from being saved

#### Scenario: Saved configuration does not take effect until restart
- **WHEN** an authenticated admin saves a new chat backend choice but does not restart the backend service
- **THEN** the running backend process continues using the chat backend it was already using, and the admin page distinguishes the currently-active backend from the saved-on-disk value

#### Scenario: Chat backend configuration is unavailable without authentication
- **WHEN** an unauthenticated request attempts to view or update the chat backend configuration
- **THEN** the request is rejected and no configuration is read or changed
