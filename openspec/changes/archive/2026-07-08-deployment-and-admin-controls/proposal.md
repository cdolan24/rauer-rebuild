## Why

The app has only ever run locally. Making it a real public service needs three things that don't exist yet: a documented way to actually deploy it on AWS, a way for an admin to remotely start/stop/restart the running services without SSHing in and hand-running commands each time, and a way to inspect/edit the database directly without a separate DB client and manual SQLite file access.

## What Changes

- **Deployment**: a single EC2 instance (not ECS/Fargate - see design.md for why container orchestration wouldn't address this app's actual speed bottleneck, and AWS Fargate specifically cannot attach a GPU at all), GPU-backed so Ollama inference isn't CPU-bound the way it is locally. Backend and frontend run as systemd services behind an Nginx reverse proxy terminating TLS; Ollama and the app's own ports are bound to localhost only, never exposed directly to the internet.
- **Service control admin panel**: extends the existing password-gated admin page with start/stop/restart controls for the backend and frontend services, backed by a small, tightly-scoped local control process (not the backend or frontend calling `systemctl` on themselves, which is architecturally awkward - a live process can't cleanly restart itself mid-request).
- **Database browser**: extends the same admin page with a raw-SQL query tool against the SQLite database, via a new admin-gated backend endpoint - direct database access without a separate SQL client.

## Capabilities

### New Capabilities
- `deployment`: how the app is deployed and run on AWS (systemd services, reverse proxy, network exposure).
- `admin-controls`: remote service control and direct database access from the admin page.

### Modified Capabilities
(none - the admin page's existing password-gate mechanism is reused as-is; the new behavior is fully described by the new `admin-controls` capability)

## Impact

- New: EC2 setup script, systemd unit files, Nginx config, security group documentation (all under a new `deploy/` directory).
- New: a minimal local-only "controller" process with narrowly-scoped `sudo` permissions for `systemctl start/stop/restart` on exactly the app's two service units.
- `src/api/routes/admin.py` (new): admin-gated raw-SQL query endpoint.
- `src/frontend/app.py`: admin page gets service-control and database-browser UI sections.
- `config.yaml` / `config.example.yaml`: controller URL/port.
