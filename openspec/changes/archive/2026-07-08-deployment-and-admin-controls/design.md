## Context

This session already diagnosed the chat "thinking" delay as CPU-bound Ollama prompt evaluation (measured directly: ~27s of prompt eval on a realistic RAG prompt, on a CPU-only local install). That diagnosis is directly relevant to the deployment model choice: **AWS Fargate cannot attach a GPU at all** (a hard platform limitation, not a configuration option - GPU support on ECS requires the EC2 launch type, not Fargate). Container orchestration itself doesn't change the underlying compute; the only real lever for faster inference is GPU-backed compute. So "should we use ECS/Fargate to go faster" resolves to: no - it can't use the one thing that would actually help, and adds orchestration complexity (registry, task definitions, service networking) that a single-service app running Ollama doesn't get any benefit from.

No AWS CLI/credentials are available in this development environment, so this change produces deployment *artifacts* (scripts, systemd units, Nginx config, documentation) for the user to apply against their own AWS account - it does not itself provision any AWS resources.

## Goals / Non-Goals

**Goals:**
- A single GPU-backed EC2 instance runs Ollama + the FastAPI backend + the Gradio frontend as systemd services, reverse-proxied by Nginx with TLS, with no port other than 80/443 (and SSH, restricted) exposed to the internet.
- An admin can start/stop/restart either service from the existing password-gated admin page, without SSH.
- An admin can run raw SQL against the database from the same admin page.

**Non-Goals:**
- Not containerizing the app (Docker/ECS) - a single EC2 instance running systemd services directly is simpler and sufficient at this scale, and avoids Fargate's GPU limitation entirely.
- Not building a general-purpose infrastructure-as-code stack (Terraform/CloudFormation) - a setup script + documented manual steps is enough for one instance; revisit if there's ever a need to manage a fleet.
- Not restricting which SQL statements the database browser can run - "access the database directly" means direct access; the existing admin password is the access control, same trust boundary as PDF upload already has.

## Decisions

1. **Single EC2 instance, GPU-backed (e.g. `g4dn.xlarge`), not ECS/Fargate.** Directly addresses the project's actual diagnosed bottleneck (CPU-bound inference); Fargate structurally cannot. A single instance also matches how the app already runs locally (all services on one machine), minimizing what changes between local dev and production.

2. **Both services run as systemd units bound to `127.0.0.1`, reverse-proxied by Nginx.** `buddharauer-backend.service` (uvicorn, port 8000) and `buddharauer-frontend.service` (Gradio, port 7860) are never directly reachable from outside the instance - Nginx terminates TLS (via Certbot/Let's Encrypt) on 443 and path-routes: `/api/*` and `/wiki*` to the backend, everything else to the frontend. This also means, in production, both surfaces sit under one public domain - the cross-origin link problem this session fixed via `frontend.public_url` doesn't even arise in this topology (same-origin through the proxy); the config-driven fix still matters for local dev's two-port setup, which is unchanged.

3. **Service control via a separate, narrowly-scoped local controller process - not the services restarting themselves.** A running process cleanly restarting itself mid-HTTP-request is architecturally awkward (the response may not finish sending before the process dies). Instead, a small standalone process (`buddharauer-controller`, its own systemd unit, bound to `127.0.0.1` only) is the only thing with `sudo` rights, restricted via a `sudoers.d` rule to exactly `systemctl {start,stop,restart} buddharauer-backend` and `buddharauer-frontend` - nothing else. The frontend's admin page calls this controller directly (both processes run on the same machine); restarting the frontend itself works cleanly because the *controller*, not the frontend, is the one issuing the restart.

4. **Database browser as a new admin-gated backend endpoint (`POST /api/admin/query`), not direct SQLite access from the frontend process.** Matches the existing pattern where the frontend always talks to the backend via `ApiClient`, keeps file-path/permissions concerns on the backend (which already owns `data_storage_path`), and reuses the existing admin-password check.

## Risks / Trade-offs

- [The controller process has real `sudo` rights] → Scoped as tightly as `sudoers.d` allows (exact commands, exact unit names, `NOPASSWD` only for those), bound to localhost, never reachable from Nginx/the public internet.
- [Unrestricted SQL means an admin can destroy data with one query] → Accepted deliberately - this is what "direct database access" means; same trust boundary as the existing admin password already guards (PDF upload can also already introduce bad data).
- [A single EC2 instance is a single point of failure] → Acceptable for this app's current scale (one deployment, not a highly-available service); revisit if uptime requirements change.
