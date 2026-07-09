## ADDED Requirements

### Requirement: Single-Instance Service Deployment
The backend and frontend SHALL run as independent systemd services on a single host, each restarting automatically on failure and starting automatically on boot.

#### Scenario: A service crashes
- **WHEN** the backend or frontend process exits unexpectedly
- **THEN** systemd restarts it automatically without manual intervention

#### Scenario: The host reboots
- **WHEN** the host machine reboots
- **THEN** both services start automatically without manual intervention

### Requirement: No Direct Internet Exposure of Application Ports
The backend, frontend, and Ollama SHALL be bound to localhost only; the only internet-facing ports SHALL be a reverse proxy on 80/443 and restricted SSH.

#### Scenario: Attempting to reach an application port directly
- **WHEN** a request is made directly to the backend, frontend, or Ollama's port from outside the host
- **THEN** the connection is refused, since those services only listen on localhost

#### Scenario: Reaching the app through the reverse proxy
- **WHEN** a request is made to the public domain over HTTPS
- **THEN** the reverse proxy routes it to the appropriate local service and returns its response
