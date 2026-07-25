# deployment

## Purpose
Defines how the application is deployed and exposed on its hosting infrastructure - a single instance under one of two profiles (GPU-backed for local/in-house Ollama chat generation, or a smaller non-GPU instance routing chat generation to a hosted API): service lifecycle, network exposure, and data backup/restore.

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
Each supported cloud target's setup script (`setup_ec2.sh` for AWS, `setup_azure_vm.sh` for Azure) SHALL complete without error on a fresh, vanilla instance of its documented target OS (Ubuntu 22.04), without requiring any package or repository not available in that OS's default archives, for either supported `DEPLOY_PROFILE`.

#### Scenario: Installing system dependencies on a fresh instance
- **WHEN** a target's setup script runs `apt-get install` for its required packages, under either deployment profile
- **THEN** every package it requests is resolvable from Ubuntu 22.04's default archives, without needing a third-party PPA

#### Scenario: Installing under the cpu-hosted-api profile on a non-GPU instance
- **WHEN** a target's setup script runs with `DEPLOY_PROFILE=cpu-hosted-api` on an instance with no GPU
- **THEN** setup completes without attempting GPU driver installation and without error

#### Scenario: The AWS script targets EC2
- **WHEN** `setup_ec2.sh` runs on a fresh Ubuntu 22.04 EC2 instance
- **THEN** it completes without error, per the scenarios above

#### Scenario: The Azure script targets an Azure VM
- **WHEN** `setup_azure_vm.sh` runs on a fresh Ubuntu 22.04 Azure VM
- **THEN** it completes without error, per the scenarios above

### Requirement: Cost-Optimized Non-GPU Deployment Profile
Each supported cloud target's setup script SHALL support a `cpu-hosted-api` deployment profile that provisions no GPU driver and pulls no local chat model, configuring the application to use the hosted-API chat backend with local Ollama retained for embeddings only.

#### Scenario: Running setup with the cpu-hosted-api profile
- **WHEN** a target's setup script is run with `DEPLOY_PROFILE=cpu-hosted-api`
- **THEN** no GPU driver installation is attempted, only the embeddings model is pulled via Ollama, and the generated `config.yaml` sets `chat_backend` to the hosted API

#### Scenario: Running setup with the default profile
- **WHEN** a target's setup script is run without `DEPLOY_PROFILE` set, or with it set to `gpu-inhouse`
- **THEN** behavior is unchanged from before this capability existed - GPU driver installation is attempted, both the chat and embedding models are pulled via Ollama, and the generated `config.yaml` sets `chat_backend` to Ollama

#### Scenario: Azure's cpu-hosted-api profile matches AWS's
- **WHEN** `setup_azure_vm.sh` is run with `DEPLOY_PROFILE=cpu-hosted-api` on an Azure VM with no GPU
- **THEN** it satisfies the same scenarios as `setup_ec2.sh`'s `cpu-hosted-api` profile above

### Requirement: Reverse Proxy Config Is Valid Before TLS Is Configured
The shipped Nginx configuration SHALL pass `nginx -t` and be capable of serving the application over plain HTTP before a TLS certificate has been obtained, so the reverse proxy can be brought up and the application tested prior to running Certbot.

#### Scenario: Testing the Nginx config immediately after installation
- **WHEN** `nginx -t` is run against the shipped configuration, before Certbot has run
- **THEN** the configuration is valid (no server block declares TLS without an accompanying certificate)

#### Scenario: Serving the application before TLS is configured
- **WHEN** Nginx is started with the shipped configuration, before Certbot has run
- **THEN** requests to the application's routes are correctly proxied to the backend or frontend over plain HTTP
