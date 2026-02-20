#!/usr/bin/env bash
set -euo pipefail

if [[ $EUID -ne 0 ]]; then
  echo "[ERROR] This script must be run as root (sudo)."
  exit 1
fi

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BOT_DIR="$REPO_ROOT/bot"
DEPLOY_DIR="$REPO_ROOT/deploy"
VENV_DIR="$BOT_DIR/.venv"
SERVICE_NAME="vpn-bot"
ENV_FILE="$BOT_DIR/.env"

ask_required() {
  local prompt="$1"
  local value=""
  while [[ -z "$value" ]]; do
    read -r -p "$prompt: " value
  done
  echo "$value"
}

ask_default() {
  local prompt="$1"
  local def="$2"
  local value=""
  read -r -p "$prompt [$def]: " value
  echo "${value:-$def}"
}

echo "=== VPN Bot Webhook Installer ==="

echo "\n--- Telegram / Bot settings ---"
BOT_TOKEN="$(ask_required 'Bot token')"
ADMIN_ID="$(ask_required 'Admin Telegram ID')"
CHANNEL_ID="$(ask_required 'Channel ID or username (without @)')"
CHANNEL_USERNAME="$(ask_default 'Channel username (without @)' "$CHANNEL_ID")"
CARD_NUMBER="$(ask_default 'Card number for payment text' '1234-5678-9012-3456')"
CARD_HOLDER="$(ask_default 'Card holder name' 'نام صاحب کارت')"

echo "\n--- Domain / Webhook settings ---"
DOMAIN="$(ask_required 'Domain for webhook (example: bot.example.com)')"
WEBHOOK_PATH="$(ask_default 'Webhook path' '/telegram/webhook')"
WEBHOOK_PORT="$(ask_default 'Internal webhook port' '8080')"
WEBHOOK_SECRET_TOKEN="$(openssl rand -hex 24)"
SSL_EMAIL="$(ask_required "Email for Let's Encrypt certificate")"

echo "\n--- PostgreSQL settings ---"
DB_NAME="$(ask_default 'Database name' 'myvpn')"
DB_USER="$(ask_default 'Database user' 'myvpn_user')"
DB_PASS="$(ask_required 'Database password')"
DB_HOST="$(ask_default 'Database host' '127.0.0.1')"
DB_PORT="$(ask_default 'Database port' '5432')"
DEFAULT_DATABASE_URL="postgresql://${DB_USER}:${DB_PASS}@${DB_HOST}:${DB_PORT}/${DB_NAME}"
DATABASE_URL="$(ask_default 'Database URL (leave default if unsure)' "$DEFAULT_DATABASE_URL")"

echo "\n[1/8] Installing system packages..."
export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y \
  python3 python3-venv python3-pip \
  postgresql postgresql-contrib \
  nginx certbot python3-certbot-nginx

echo "[2/8] Configuring PostgreSQL..."
sudo -u postgres psql <<SQL
DO
\$\$
BEGIN
   IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = '${DB_USER}') THEN
      CREATE ROLE ${DB_USER} LOGIN PASSWORD '${DB_PASS}';
   ELSE
      ALTER ROLE ${DB_USER} WITH PASSWORD '${DB_PASS}';
   END IF;
END
\$\$;
SQL
sudo -u postgres psql -tc "SELECT 1 FROM pg_database WHERE datname = '${DB_NAME}'" | grep -q 1 || \
  sudo -u postgres createdb -O "$DB_USER" "$DB_NAME"

echo "[3/8] Switching project to webhook runtime..."
if [[ -f "$BOT_DIR/main.py" && ! -f "$BOT_DIR/main.polling.py" ]]; then
  cp "$BOT_DIR/main.py" "$BOT_DIR/main.polling.py"
fi
cp "$DEPLOY_DIR/webhook_main.py" "$BOT_DIR/main.py"

echo "[4/8] Creating Python virtualenv and installing requirements..."
python3 -m venv "$VENV_DIR"
PIP="$VENV_DIR/bin/pip"
PYTHON_BIN="$VENV_DIR/bin/python"

# Keep installer deterministic to reduce version conflicts on servers
"$PIP" install --upgrade "pip==24.3.1" "setuptools==75.6.0" "wheel==0.45.1"

# Prefer prebuilt wheels first (faster + fewer build incompatibilities)
if ! "$PIP" install --prefer-binary --only-binary=:all: -r "$BOT_DIR/requirements.txt"; then
  echo "[WARN] Wheel-only install failed, retrying with source fallback..."
  "$PIP" install --prefer-binary -r "$BOT_DIR/requirements.txt"
fi

# Webhook runtime dependency (kept out of base local requirements intentionally)
"$PIP" install --prefer-binary "aiohttp==3.9.3"

# Validate dependency graph and keep a lock snapshot for troubleshooting/repro
"$PIP" check
"$PIP" freeze > "$BOT_DIR/requirements.lock.txt"

echo "[5/8] Writing .env file..."
cat > "$ENV_FILE" <<ENVVARS
BOT_TOKEN=${BOT_TOKEN}
WEBHOOK_HOST=0.0.0.0
WEBHOOK_PORT=${WEBHOOK_PORT}
WEBHOOK_PATH=${WEBHOOK_PATH}
WEBHOOK_BASE_URL=https://${DOMAIN}
WEBHOOK_SECRET_TOKEN=${WEBHOOK_SECRET_TOKEN}
WEBHOOK_DROP_PENDING_UPDATES=true

CHANNEL_ID=${CHANNEL_ID}
CHANNEL_USERNAME=${CHANNEL_USERNAME}
ADMIN_ID=${ADMIN_ID}
CARD_NUMBER=${CARD_NUMBER}
CARD_HOLDER=${CARD_HOLDER}
DATABASE_URL=${DATABASE_URL}
ENVVARS
chmod 600 "$ENV_FILE"

echo "[6/8] Creating systemd service..."
cat > "/etc/systemd/system/${SERVICE_NAME}.service" <<SERVICE
[Unit]
Description=VPN Telegram Bot (Webhook)
After=network.target postgresql.service

[Service]
Type=simple
User=root
WorkingDirectory=${BOT_DIR}
ExecStart=${VENV_DIR}/bin/python main.py
Restart=always
RestartSec=5
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
SERVICE

echo "[7/8] Configuring Nginx and SSL..."
cat > "/etc/nginx/sites-available/${SERVICE_NAME}" <<NGINX
server {
    listen 80;
    server_name ${DOMAIN};

    location ${WEBHOOK_PATH} {
        proxy_pass http://127.0.0.1:${WEBHOOK_PORT};
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    location / {
        return 404;
    }
}
NGINX
ln -sf "/etc/nginx/sites-available/${SERVICE_NAME}" "/etc/nginx/sites-enabled/${SERVICE_NAME}"
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl reload nginx
certbot --nginx --non-interactive --agree-tos --redirect -m "$SSL_EMAIL" -d "$DOMAIN"

echo "[8/8] Starting services..."
systemctl daemon-reload
systemctl enable "$SERVICE_NAME"
systemctl restart "$SERVICE_NAME"
sleep 2
systemctl --no-pager --full status "$SERVICE_NAME" || true

echo "✅ Done. Webhook URL: https://${DOMAIN}${WEBHOOK_PATH}"
echo "Logs: journalctl -u ${SERVICE_NAME} -f"
