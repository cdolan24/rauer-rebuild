## ADDED Requirements

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
