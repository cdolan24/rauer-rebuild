## ADDED Requirements

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
