# deployment

## Purpose
Defines how the application is deployed and exposed on its hosting infrastructure (currently a single GPU-backed EC2 instance): service lifecycle, network exposure, and data backup/restore.

## Requirements

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

### Requirement: Automated Data Backup
The deployed instance SHALL automatically create a daily backup of the application database and vector store, retaining at least the last 7 days of backups on local disk.

#### Scenario: Daily backup runs automatically
- **WHEN** the daily backup timer fires
- **THEN** a consistent snapshot of the application database and the vector store is written to the backup location, without corrupting or interrupting the running services

#### Scenario: Old backups are pruned
- **WHEN** a new backup completes and more than 7 days of backups exist
- **THEN** backups older than 7 days are removed, keeping local disk usage bounded

#### Scenario: Restoring from a backup
- **WHEN** an operator follows the documented restore procedure with a specific backup snapshot
- **THEN** the application database and vector store are restored to that snapshot's state

### Requirement: Setup Succeeds on a Vanilla Target Instance
`setup_ec2.sh` SHALL complete without error on a fresh, vanilla instance of its documented target OS (Ubuntu 22.04), without requiring any package or repository not available in that OS's default archives.

#### Scenario: Installing system dependencies on a fresh instance
- **WHEN** `setup_ec2.sh` runs `apt-get install` for its required packages
- **THEN** every package it requests is resolvable from Ubuntu 22.04's default archives, without needing a third-party PPA

### Requirement: Reverse Proxy Config Is Valid Before TLS Is Configured
The shipped Nginx configuration SHALL pass `nginx -t` and be capable of serving the application over plain HTTP before a TLS certificate has been obtained, so the reverse proxy can be brought up and the application tested prior to running Certbot.

#### Scenario: Testing the Nginx config immediately after installation
- **WHEN** `nginx -t` is run against the shipped configuration, before Certbot has run
- **THEN** the configuration is valid (no server block declares TLS without an accompanying certificate)

#### Scenario: Serving the application before TLS is configured
- **WHEN** Nginx is started with the shipped configuration, before Certbot has run
- **THEN** requests to the application's routes are correctly proxied to the backend or frontend over plain HTTP
