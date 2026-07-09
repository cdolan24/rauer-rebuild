# Deploying Buddharauer to AWS

This directory has everything needed to run Buddharauer on a single AWS EC2
instance: a setup script, systemd unit files, an Nginx reverse-proxy config,
a sudoers rule, and the local service-control daemon the admin page talks to.

**None of this has been run against a real AWS account** - this development
environment has no AWS credentials configured. Review each script/config
before applying it to a real server.

## Why a single GPU-backed EC2 instance, not ECS/Fargate

Local testing (see the session logs) traced the chat "thinking" delay to
CPU-bound Ollama prompt evaluation - a realistic RAG prompt took ~27s of
prompt evaluation alone on a CPU-only install. **AWS Fargate cannot attach a
GPU at all** - that's a hard platform limitation, not a configuration choice
(GPU support on ECS requires the EC2 launch type, not Fargate). Since
container orchestration doesn't change the underlying compute, and the only
real lever for faster inference is GPU acceleration, a single GPU-backed EC2
instance directly addresses the actual bottleneck; ECS/Fargate would not,
and would add real complexity (registry, task definitions, service
networking) for no benefit here.

**Recommended instance type**: `g4dn.xlarge` (NVIDIA T4 GPU, 4 vCPU, 16 GB
RAM) - the smallest/cheapest GPU instance type, comfortably enough for
`llama3.2` + `nomic-embed-text` at this app's scale. Use an Ubuntu 22.04 AMI,
ideally a "Deep Learning AMI" variant that already has NVIDIA drivers
installed (saves a step and a reboot).

## Network topology

```
Internet --> Nginx (443, TLS) --> /api/*, /wiki*  --> backend  (127.0.0.1:8000)
                               --> everything else --> frontend (127.0.0.1:7860)

Frontend admin page --> controller (127.0.0.1:8100, never exposed publicly)
```

Only ports 80 (redirects to 443), 443, and SSH (22, restricted to your own
IP) should be open in the instance's security group. The backend, frontend,
Ollama (11434), and the controller (8100) all bind to `127.0.0.1` and are
never directly reachable from outside the instance.

Because both the wiki and chat sit behind the same public domain in this
topology (path-routed by Nginx), set `frontend.public_url` in `config.yaml`
to that same domain (e.g. `https://your-domain.example.com`) - the
cross-origin concern that exists in local dev (wiki on :8000, chat on :7860)
doesn't arise in production.

## Security group

| Port | Source | Purpose |
|---|---|---|
| 443 | 0.0.0.0/0 | HTTPS (public) |
| 80 | 0.0.0.0/0 | HTTP -> HTTPS redirect only |
| 22 | your IP only | SSH for initial setup / troubleshooting |

Nothing else should be open. Do not open 8000, 7860, 8100, or 11434.

## Setup

1. Launch a `g4dn.xlarge` (or similar GPU instance) with Ubuntu 22.04, in a
   security group matching the table above.
2. Point a domain's DNS at the instance's public IP.
3. SSH in and run:
   ```bash
   sudo BUDDHARAUER_REPO_URL=https://github.com/you/rauer-rebuild.git ./setup_ec2.sh
   ```
   (Copy `setup_ec2.sh` to the instance first, or clone the repo manually and
   run it from `deploy/`.)
4. Follow the script's final printed instructions: edit `config.yaml`, set
   the Nginx `server_name`, get a TLS cert via `certbot --nginx`, then start
   the services.

## Using the admin controls once deployed

Visit `https://your-domain.example.com/admin` and enter the admin password
(the same one in `config.yaml`'s `auth.admin_password`) to unlock:

- **Upload New PDFs** - existing functionality, unchanged.
- **Database Browser** - run arbitrary SQL against the application database
  directly from the browser. This is intentionally unrestricted (no
  read-only mode) - the admin password is the only access control, the same
  trust boundary PDF upload already has.
- **Service Control** - start/stop/restart the backend and frontend, and
  check their current status, without SSHing in. This works through the
  `buddharauer-controller` service, which holds a narrowly-scoped `sudo`
  rule (see `sudoers-buddharauer-controller`) permitting *only*
  `systemctl {start,stop,restart}` on these two specific units - nothing
  else, and it's never reachable from outside the instance.

You can also manage services directly via SSH as a fallback:
```bash
systemctl status buddharauer-backend buddharauer-frontend buddharauer-controller
systemctl restart buddharauer-backend
journalctl -u buddharauer-backend -f   # tail logs
```

## Files in this directory

- `setup_ec2.sh` - one-time instance setup (installs everything, doesn't start services).
- `buddharauer-backend.service`, `buddharauer-frontend.service`, `buddharauer-controller.service` - systemd units.
- `sudoers-buddharauer-controller` - the controller's narrowly-scoped sudo rule.
- `nginx-buddharauer.conf` - reverse proxy config (path-routes to backend/frontend, TLS via certbot).
- `controller.py` - the local-only service-control daemon the admin page's Service Control section calls.
