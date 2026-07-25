# Deploying Malifaux Document Explorer

This directory has everything needed to run Malifaux Document Explorer on a single VM:
a setup script, systemd unit files, an Nginx reverse-proxy config, a sudoers rule, and
the local service-control daemon the admin page talks to. Two cloud targets are
supported, sharing everything except the setup script and a few platform-specific
notes below: **AWS EC2** (`setup_ec2.sh`) and **Azure VM** (`setup_azure_vm.sh`).

**None of this has been run against a real AWS or Azure account** - this development
environment has no cloud credentials configured for either. Review each script/config
before applying it to a real server.

## Why a single GPU-backed instance, not managed containers

Local testing (see the session logs) traced the chat "thinking" delay to
CPU-bound Ollama prompt evaluation - a realistic RAG prompt took ~27s of
prompt evaluation alone on a CPU-only install. **AWS Fargate cannot attach a
GPU at all** - that's a hard platform limitation, not a configuration choice
(GPU support on ECS requires the EC2 launch type, not Fargate); Azure's
equivalent managed-container products (Container Instances, Container Apps)
have the same practical gap for GPU workloads, requiring AKS instead - real
cluster-management overhead for a single-service app. Since container
orchestration doesn't change the underlying compute, and the only real lever
for faster inference is GPU acceleration, a single GPU-backed instance
directly addresses the actual bottleneck; managed containers would not, and
would add real complexity (registry, task/pod definitions, service
networking) for no benefit here. This is why both targets provision a plain
VM with systemd + Nginx rather than a container platform.

## Recommended instance/VM size

| Profile | AWS instance type | Azure VM size |
|---|---|---|
| `gpu-inhouse` (local chat + embeddings) | `g4dn.xlarge` (NVIDIA T4, 4 vCPU, 16 GB RAM) | `Standard_NC4as_T4_v3` (NVIDIA T4, 4 vCPU, 28 GB RAM) |
| `cpu-hosted-api` (embeddings only, chat via hosted API) | `t3.small` | `Standard_B2s` |

Both are the smallest/cheapest size in their family comfortably sufficient for
`llama3.2` + `nomic-embed-text` (`gpu-inhouse`) or embeddings alone
(`cpu-hosted-api`) at this app's scale. Use an Ubuntu 22.04 image; on AWS,
ideally a "Deep Learning AMI" variant that already has NVIDIA drivers
installed (saves a step and a reboot) - Azure's Data Science VM images offer
the same shortcut, though a plain Ubuntu 22.04 marketplace image works fine
either way (`setup_ec2.sh`/`setup_azure_vm.sh` install the driver themselves
if it's missing).

## Network topology

```
Internet --> Nginx (443, TLS) --> /api/*, /wiki*  --> backend  (127.0.0.1:8000)
                               --> everything else --> frontend (127.0.0.1:7860)

Frontend admin page --> controller (127.0.0.1:8100, never exposed publicly)
```

Only ports 80 (redirects to 443), 443, and SSH (22, restricted to your own
IP) should be open to the instance. The backend, frontend, Ollama (11434),
and the controller (8100) all bind to `127.0.0.1` and are never directly
reachable from outside the instance - this holds regardless of which cloud
enforces it (an AWS security group or an Azure NSG).

Because both the wiki and chat sit behind the same public domain in this
topology (path-routed by Nginx), set `frontend.public_url` in `config.yaml`
to that same domain (e.g. `https://your-domain.example.com`) - the
cross-origin concern that exists in local dev (wiki on :8000, chat on :7860)
doesn't arise in production.

## Firewall rules

### AWS security group

| Port | Source | Purpose |
|---|---|---|
| 443 | 0.0.0.0/0 | HTTPS (public) |
| 80 | 0.0.0.0/0 | HTTP -> HTTPS redirect only |
| 22 | your IP only | SSH for initial setup / troubleshooting |

### Azure network security group (NSG)

Same three rules, as inbound NSG rules on the VM's network interface (or
subnet):

| Priority | Port | Source | Purpose |
|---|---|---|---|
| 100 | 443 | Any | HTTPS (public) |
| 110 | 80 | Any | HTTP -> HTTPS redirect only |
| 120 | 22 | your IP only (CIDR) | SSH for initial setup / troubleshooting |

Nothing else should be open, on either cloud. Do not open 8000, 7860, 8100, or 11434.

## Setup

### AWS (EC2)

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

For the cost-optimized, non-GPU profile, launch a `t3.small` instead and add
`DEPLOY_PROFILE=cpu-hosted-api` to the command in step 3.

### Azure (VM)

1. Create a resource group, then the VM (adjust names/region/image as
   needed):
   ```bash
   az group create --name buddharauer-rg --location eastus
   az vm create \
     --resource-group buddharauer-rg \
     --name buddharauer-vm \
     --image Ubuntu2204 \
     --size Standard_NC4as_T4_v3 \
     --admin-username azureuser \
     --generate-ssh-keys
   ```
2. Open the inbound NSG rules from the table above (the default NSG `az vm
   create` generates already allows your SSH source; add 80/443):
   ```bash
   az vm open-port --resource-group buddharauer-rg --name buddharauer-vm --port 80 --priority 110
   az vm open-port --resource-group buddharauer-rg --name buddharauer-vm --port 443 --priority 100
   ```
3. Point a domain's DNS at the VM's public IP (`az vm show -d -g buddharauer-rg -n buddharauer-vm --query publicIps -o tsv`).
4. SSH in and run:
   ```bash
   sudo BUDDHARAUER_REPO_URL=https://github.com/you/rauer-rebuild.git ./setup_azure_vm.sh
   ```
   (Copy `setup_azure_vm.sh` to the VM first, or clone the repo manually and
   run it from `deploy/`.)
5. Follow the script's final printed instructions: edit `config.yaml`, set
   the Nginx `server_name`, get a TLS cert via `certbot --nginx`, then start
   the services.

For the cost-optimized, non-GPU profile, use `--size Standard_B2s` in step 1
and add `DEPLOY_PROFILE=cpu-hosted-api` to the command in step 4.

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

## Backups

`buddharauer-backup.timer` runs `backup.sh` once a day, producing:
- `backups/buddharauer-<timestamp>.db` - a consistent snapshot of the application database, taken via SQLite's own online-backup mechanism (`sqlite3 ... ".backup"`), safe to run against the live, in-use database.
- `backups/vector_db-<timestamp>.tar.gz` - a tarball of the vector store.

Backups older than 7 days are pruned automatically (`BUDDHARAUER_BACKUP_RETENTION_DAYS` to change). This exists specifically because the admin page's database browser runs arbitrary, unrestricted SQL - a backup is the recovery path for a bad query, not just general disk-failure insurance.

**This is local-disk-only** - it does not protect against losing the instance itself (accidental termination, disk failure). If that risk matters to you, the natural next step is periodically syncing `backups/` to cloud object storage - `aws s3 sync` on AWS, `az storage blob upload-batch` on Azure - but that requires real cloud credentials/a storage account to set up and hasn't been configured here.

**To restore from a backup:**
```bash
systemctl stop buddharauer-backend buddharauer-frontend
cp /opt/buddharauer/backups/buddharauer-<timestamp>.db /opt/buddharauer/data_storage/buddharauer.db
rm -rf /opt/buddharauer/vector_db
tar -xzf /opt/buddharauer/backups/vector_db-<timestamp>.tar.gz -C /opt/buddharauer
systemctl start buddharauer-backend buddharauer-frontend
```

**To back up on demand** (e.g. right before a risky admin query): `sudo systemctl start buddharauer-backup.service`.

## Admin endpoint rate limiting

`/api/auth/verify`, `/api/admin/query`, `/api/documents/upload`, and the controller's `/control/*` routes all lock out a client IP for 15 minutes after 5 wrong admin-password attempts (`src/utils/rate_limiter.py`), checked before the password is even compared. This is in-process, per-service state - correct for this single-instance, single-worker-per-service deployment, but would need a shared store (Redis, a DB table) if the topology ever changed to multiple workers or hosts.

## Files in this directory

- `setup_ec2.sh` - one-time AWS EC2 instance setup (installs everything, doesn't start services).
- `setup_azure_vm.sh` - the same, for an Azure VM.
- `buddharauer-backend.service`, `buddharauer-frontend.service`, `buddharauer-controller.service` - systemd units.
- `buddharauer-backup.service`, `buddharauer-backup.timer` - daily backup of the database and vector store.
- `backup.sh` - the backup script the timer runs (see "Backups" above).
- `sudoers-buddharauer-controller` - the controller's narrowly-scoped sudo rule.
- `nginx-buddharauer.conf` - reverse proxy config (path-routes to backend/frontend, TLS via certbot).
- `controller.py` - the local-only service-control daemon the admin page's Service Control section calls.
