#!/bin/bash
# Buddharauer Azure VM setup script. Run as root on a fresh Ubuntu 22.04 VM.
#
# Two deployment profiles, selected via DEPLOY_PROFILE:
#   gpu-inhouse    (default) - today's behavior: Ollama runs both chat
#                  generation and embeddings locally. Needs a GPU-backed VM
#                  size (e.g. an NC-family, T4-class size such as
#                  Standard_NC4as_T4_v3) - see README.md for why GPU matters
#                  here. Use this for hardware you already own/have quota for.
#   cpu-hosted-api - no GPU needed: chat generation routes to a hosted API
#                  (config.yaml's hosted_llm section), Ollama only runs
#                  embeddings on a small CPU size (e.g. Standard_B2s). Cost-
#                  optimized - see openspec/specs/deployment/.
#
# This script has not been run against a real Azure subscription from this
# development environment (no Azure credentials here) - review each step
# before running it against a real VM. See deploy/README.md for the
# az vm create / NSG prerequisites this script assumes are already done.
#
# Usage: sudo BUDDHARAUER_REPO_URL=https://github.com/you/rauer-rebuild.git ./setup_azure_vm.sh
# Usage (cost-optimized profile): sudo BUDDHARAUER_REPO_URL=... DEPLOY_PROFILE=cpu-hosted-api ./setup_azure_vm.sh
set -euo pipefail

APP_DIR=/opt/buddharauer
APP_USER=buddharauer
CONTROLLER_USER=buddharauer-controller
REPO_URL="${BUDDHARAUER_REPO_URL:?Set BUDDHARAUER_REPO_URL to the repo clone URL}"
DEPLOY_PROFILE="${DEPLOY_PROFILE:-gpu-inhouse}"
case "$DEPLOY_PROFILE" in
    gpu-inhouse|cpu-hosted-api) ;;
    *) echo "Unknown DEPLOY_PROFILE '$DEPLOY_PROFILE' - expected 'gpu-inhouse' or 'cpu-hosted-api'" >&2; exit 1 ;;
esac
echo "==> Deployment profile: $DEPLOY_PROFILE"

echo "==> Installing system dependencies"
apt-get update
# Ubuntu 22.04 ships Python 3.10 by default - python3.11 isn't in the
# standard archives (it needs the deadsnakes PPA) and nothing here actually
# requires 3.11, so use the system python3 rather than a version apt-get
# would fail to find on a vanilla instance.
apt-get install -y python3 python3-venv nginx certbot python3-certbot-nginx git curl sqlite3

if [ "$DEPLOY_PROFILE" = "gpu-inhouse" ]; then
    echo "==> Installing NVIDIA driver (if not already present)"
    # If you launched from an Azure Data Science VM or another GPU-ready
    # marketplace image, the driver may already be installed and this block
    # is a no-op.
    if ! command -v nvidia-smi &> /dev/null; then
        apt-get install -y ubuntu-drivers-common
        ubuntu-drivers autoinstall
        echo "    NVIDIA driver installed - a reboot may be required before Ollama can use the GPU."
    fi
else
    echo "==> Skipping NVIDIA driver install (DEPLOY_PROFILE=cpu-hosted-api needs no GPU)"
fi

echo "==> Installing Ollama"
curl -fsSL https://ollama.com/install.sh | sh

echo "==> Creating app + controller system users"
id -u "$APP_USER" &>/dev/null || useradd --system --create-home --shell /bin/bash "$APP_USER"
id -u "$CONTROLLER_USER" &>/dev/null || useradd --system --no-create-home --shell /usr/sbin/nologin "$CONTROLLER_USER"
# Controller needs read access to config.yaml (to check the admin password
# against incoming /control/* requests) but runs as its own, separate user -
# added as a supplementary member of $APP_USER's group rather than widening
# config.yaml's permissions beyond owner+group. Safe to re-run (idempotent).
usermod -aG "$APP_USER" "$CONTROLLER_USER"

echo "==> Cloning application to $APP_DIR"
if [ ! -d "$APP_DIR" ]; then
    git clone "$REPO_URL" "$APP_DIR"
fi
chown -R "$APP_USER:$APP_USER" "$APP_DIR"

echo "==> Python virtualenv + dependencies"
sudo -u "$APP_USER" python3 -m venv "$APP_DIR/venv"
sudo -u "$APP_USER" "$APP_DIR/venv/bin/pip" install --upgrade pip
sudo -u "$APP_USER" "$APP_DIR/venv/bin/pip" install "$APP_DIR"

echo "==> Pulling required Ollama models"
# Embeddings always run on Ollama regardless of profile.
ollama pull nomic-embed-text:latest
if [ "$DEPLOY_PROFILE" = "gpu-inhouse" ]; then
    ollama pull llama3.2:latest
else
    echo "    Skipping local chat model pull (DEPLOY_PROFILE=cpu-hosted-api routes chat to hosted_llm)"
fi

echo "==> Config"
if [ ! -f "$APP_DIR/config.yaml" ]; then
    cp "$APP_DIR/config.example.yaml" "$APP_DIR/config.yaml"
    if [ "$DEPLOY_PROFILE" = "cpu-hosted-api" ]; then
        sed -i 's/^chat_backend: "ollama"/chat_backend: "hosted_api"/' "$APP_DIR/config.yaml"
        cat >> "$APP_DIR/config.yaml" <<'HOSTED_LLM'

hosted_llm:
  provider: "anthropic"
  model: "claude-haiku-4-5"
  # REQUIRED before starting services under this profile - get a key at
  # https://console.anthropic.com/settings/keys. Never commit a real value.
  api_key: "changeme"
  max_tokens: 1024
HOSTED_LLM
    fi
    echo "    Created $APP_DIR/config.yaml from the example - edit it (admin_password,"
    echo "    frontend.public_url, etc.) before starting services. See README.md."
fi
chown "$APP_USER:$APP_USER" "$APP_DIR/config.yaml"
# config.yaml holds plaintext secrets (admin_password, hosted_llm.api_key) -
# owner+group only (buddharauer-controller reads it as a group member, see
# above), not the world-readable default a plain cp leaves it at.
chmod 640 "$APP_DIR/config.yaml"

echo "==> Installing systemd units"
cp "$APP_DIR/deploy/buddharauer-backend.service" /etc/systemd/system/
cp "$APP_DIR/deploy/buddharauer-frontend.service" /etc/systemd/system/
cp "$APP_DIR/deploy/buddharauer-controller.service" /etc/systemd/system/
cp "$APP_DIR/deploy/buddharauer-backup.service" /etc/systemd/system/
cp "$APP_DIR/deploy/buddharauer-backup.timer" /etc/systemd/system/
chmod +x "$APP_DIR/deploy/backup.sh"
systemctl daemon-reload

echo "==> Installing sudoers rule for the controller"
install -m 0440 "$APP_DIR/deploy/sudoers-buddharauer-controller" /etc/sudoers.d/buddharauer-controller
visudo -c

echo "==> Installing Nginx config"
cp "$APP_DIR/deploy/nginx-buddharauer.conf" /etc/nginx/sites-available/buddharauer
ln -sf /etc/nginx/sites-available/buddharauer /etc/nginx/sites-enabled/buddharauer
rm -f /etc/nginx/sites-enabled/default
nginx -t

echo "==> Enabling services (not starting yet - edit config.yaml and server_name first)"
systemctl enable buddharauer-backend buddharauer-frontend buddharauer-controller nginx
systemctl enable --now buddharauer-backup.timer

cat <<EOF

==> Setup complete (profile: $DEPLOY_PROFILE). Before going live:
  1. Edit $APP_DIR/config.yaml - set a real admin_password and
     frontend.public_url to match your domain (same domain as the reverse
     proxy - see README.md).
EOF
if [ "$DEPLOY_PROFILE" = "cpu-hosted-api" ]; then
cat <<EOF
     Also set hosted_llm.api_key to a real Anthropic key (from
     https://console.anthropic.com/settings/keys) - chat generation will
     fail to start until this is a real value, not the "changeme" placeholder.
EOF
fi
cat <<EOF
  2. Edit /etc/nginx/sites-available/buddharauer - set server_name to your
     actual domain.
  3. Point your domain's DNS at this VM's public IP, then get a TLS cert:
       certbot --nginx -d your-domain.example.com
  4. Start everything:
       systemctl start buddharauer-backend buddharauer-frontend buddharauer-controller nginx
  5. Check status:
       systemctl status buddharauer-backend buddharauer-frontend buddharauer-controller
EOF
