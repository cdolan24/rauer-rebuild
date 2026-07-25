## ADDED Requirements

### Requirement: Configured Hosted API Key Is Never Exposed After Being Set
Once a hosted API key has been written to configuration, the system SHALL NOT return its value through any read path (API response, admin page, logs) - only whether a key is currently configured.

#### Scenario: Reading backend configuration after a key was set
- **WHEN** the chat backend configuration is read after a hosted API key has previously been configured
- **THEN** the response indicates a key is configured without including its value

### Requirement: Configuration Changes to the Chat Backend Require a Restart to Take Effect
Since the chat backend is constructed once at process startup, writing a new `chat_backend`/`hosted_llm` configuration value SHALL NOT change which backend the running process uses until the process is restarted.

#### Scenario: Configuration is updated while the process is running
- **WHEN** the chat backend configuration is changed on disk while the application is already running
- **THEN** the running process continues using the chat backend it started with, until it is restarted
