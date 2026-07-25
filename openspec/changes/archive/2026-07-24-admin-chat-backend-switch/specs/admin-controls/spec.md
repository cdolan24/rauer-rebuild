## ADDED Requirements

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
