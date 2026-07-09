#!/bin/bash
# Buddharauer EC2 setup script. Run as root on a fresh Ubuntu 22.04 instance.
# Tested target: a GPU-backed instance (e.g. g4dn.xlarge) - see README.md for
# why GPU matters here. This script has not been run against a real AWS
# instance from this development environment (no AWS access here) - review
# each step before running it against a real server.
#
# Usage: sudo BUDDHARAUER_REPO_URL=https://github.com/you/rauer-rebuild.git ./setup_ec2.sh
set -euo pipefail

APP_DIR=/opt/buddharauer
APP_USER=buddharauer
CONTROLLER_USER=buddharauer-controller
REPO_URL="${BUDDHARAUER_REPO_URL:?Set BUDDHARAUER_REPO_URL to the repo clone URL}"

echo "==> Installing system dependencies"
apt-get update
apt-get install -y python3.11 python3.11-venv nginx certbot python3-certbot-nginx git curl

echo "==> Installing NVIDIA driver (if not already present) + Ollama"
# If you launched from a "Deep Learning AMI" the driver is already installed
# and this block is a no-op.
if ! command -v nvidia-smi &> /dev/null; then
    apt-get install -y ubuntu-drivers-common
    ubuntu-drivers autoinstall
    echo "    NVIDIA driver installed - a reboot may be required before Ollama can use the GPU."
fi
curl -fsSL https://ollama.com/install.sh | sh

echo "==> Creating app + controller system users"
id -u "$APP_USER" &>/dev/null || useradd --system --create-home --shell /bin/bash "$APP_USER"
id -u "$CONTROLLER_USER" &>/dev/null || useradd --system --no-create-home --shell /usr/sbin/nologin "$CONTROLLER_USER"

echo "==> Cloning application to $APP_DIR"
if [ ! -d "$APP_DIR" ]; then
    git clone "$REPO_URL" "$APP_DIR"
fi
chown -R "$APP_USER:$APP_USER" "$APP_DIR"

echo "==> Python virtualenv + dependencies"
sudo -u "$APP_USER" python3.11 -m venv "$APP_DIR/venv"
sudo -u "$APP_USER" "$APP_DIR/venv/bin/pip" install --upgrade pip
sudo -u "$APP_USER" "$APP_DIR/venv/bin/pip" install -r "$APP_DIR/requirements.txt"

echo "==> Pulling required Ollama models"
ollama pull llama3.2:latest
ollama pull nomic-embed-text:latest

echo "==> Config"
if [ ! -f "$APP_DIR/config.yaml" ]; then
    cp "$APP_DIR/config.example.yaml" "$APP_DIR/config.yaml"
    echo "    Created $APP_DIR/config.yaml from the example - edit it (admin_password,"
    echo "    frontend.public_url, etc.) before starting services. See README.md."
fi
chown "$APP_USER:$APP_USER" "$APP_DIR/config.yaml"

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

==> Setup complete. Before going live:
  1. Edit $APP_DIR/config.yaml - set a real admin_password and
     frontend.public_url to match your domain (same domain as the reverse
     proxy - see README.md).
  2. Edit /etc/nginx/sites-available/buddharauer - set server_name to your
     actual domain.
  3. Point your domain's DNS at this instance, then get a TLS cert:
       certbot --nginx -d your-domain.example.com
  4. Start everything:
       systemctl start buddharauer-backend buddharauer-frontend buddharauer-controller nginx
  5. Check status:
       systemctl status buddharauer-backend buddharauer-frontend buddharauer-controller
EOF
