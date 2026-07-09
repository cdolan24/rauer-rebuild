## 1. Database browser (backend)

- [x] 1.1 Add `POST /api/admin/query` in a new `src/api/routes/admin.py`: admin-password gated (same `verify_admin_password` pattern as upload), executes arbitrary SQL against `data_storage_path` via a plain `sqlite3` connection, returns column names + rows for `SELECT`-like statements or an affected-row count otherwise
- [x] 1.2 Register the new router in `src/api/main.py`
- [x] 1.3 Unit/integration tests: correct password runs a query and returns results; incorrect/missing password is rejected with no query executed; a non-SELECT statement returns an affected-row count

## 2. Database browser (frontend)

- [x] 2.1 Add `ApiClient.run_admin_query(sql, admin_password) -> dict`
- [x] 2.2 Add a "Database Browser" section to the admin page: a SQL textbox, a "Run query" button, and a results table/output area

## 3. Service control (controller process)

- [x] 3.1 Write a minimal standalone controller script (`deploy/controller.py`): a small FastAPI app exposing `POST /control/{service}/{action}` (service in backend/frontend, action in start/stop/restart) and `GET /control/{service}/status`, admin-password gated, calling `systemctl` via `subprocess`
- [x] 3.2 Write the `sudoers.d` rule template restricting the controller's system user to exactly `systemctl {start,stop,restart} buddharauer-backend/buddharauer-frontend` with `NOPASSWD`
- [x] 3.3 Add `ApiClient`-equivalent calls from the frontend admin page to the controller (new config value for the controller's local URL)
- [x] 3.4 Add a "Service Control" section to the admin page: status indicators and start/stop/restart buttons for backend and frontend
- [x] 3.5 Unit tests for the controller's request validation (correct/incorrect password, valid/invalid service+action combinations) using a fake subprocess call

## 4. Deployment artifacts

- [x] 4.1 systemd unit files: `buddharauer-backend.service`, `buddharauer-frontend.service`, `buddharauer-controller.service` (all `Restart=on-failure`, enabled at boot, bound to 127.0.0.1)
- [x] 4.2 Nginx reverse proxy config: path-routes `/api/*` and `/wiki*` to the backend, everything else to the frontend, TLS via Certbot
- [x] 4.3 EC2 setup script (`deploy/setup_ec2.sh`): installs Ollama + pulls required models, installs Python deps, installs the systemd units, configures the sudoers rule, starts services
- [x] 4.4 `deploy/README.md`: instance type recommendation (GPU-backed, e.g. `g4dn.xlarge`) and why, security group configuration (only 80/443/22 exposed, SSH restricted), step-by-step deployment instructions, and how to use the new admin controls once deployed

## 5. Verify & ship

- [x] 5.1 Run full test suite, confirm green
- [x] 5.2 Local verification: run the controller script locally, confirm the admin page's service-control and database-browser sections work end-to-end against local services (systemctl itself can't be exercised on this Windows dev machine - verified via mocked unit tests instead, and confirmed the auth-gating/error-handling path live)
- [ ] 5.3 Archive the OpenSpec change (sync specs first), commit and push to `session-4`
