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
TARGET_BRANCH="${1:-$(git -C "$REPO_ROOT" rev-parse --abbrev-ref HEAD)}"

if [[ -z "$TARGET_BRANCH" ]]; then
  echo "[ERROR] Could not detect target branch. Pass it as first argument."
  exit 1
fi

if [[ ! -d "$REPO_ROOT/.git" ]]; then
  echo "[ERROR] Git repository not found at: $REPO_ROOT"
  exit 1
fi

if [[ -f "$ENV_FILE" ]]; then
  ENV_BACKUP="$(mktemp)"
  cp "$ENV_FILE" "$ENV_BACKUP"
else
  ENV_BACKUP=""
fi

cleanup() {
  if [[ -n "${ENV_BACKUP:-}" && -f "${ENV_BACKUP:-}" ]]; then
    rm -f "$ENV_BACKUP"
  fi
}
trap cleanup EXIT

echo "[1/6] Fetching latest changes from origin..."
git -C "$REPO_ROOT" fetch --prune origin

if git -C "$REPO_ROOT" show-ref --verify --quiet "refs/remotes/origin/$TARGET_BRANCH"; then
  REMOTE_REF="origin/$TARGET_BRANCH"
else
  echo "[ERROR] Remote branch origin/$TARGET_BRANCH not found."
  exit 1
fi

echo "[2/6] Updating working tree to $REMOTE_REF ..."
git -C "$REPO_ROOT" checkout "$TARGET_BRANCH"
git -C "$REPO_ROOT" reset --hard "$REMOTE_REF"
git -C "$REPO_ROOT" clean -fd

if [[ -n "$ENV_BACKUP" && -f "$ENV_BACKUP" ]]; then
  cp "$ENV_BACKUP" "$ENV_FILE"
  chmod 600 "$ENV_FILE"
fi

echo "[3/6] Enforcing webhook runtime entrypoint..."
cp "$DEPLOY_DIR/webhook_main.py" "$BOT_DIR/main.py"

echo "[4/6] Installing/updating Python dependencies..."
if [[ ! -x "$VENV_DIR/bin/python" ]]; then
  python3 -m venv "$VENV_DIR"
fi
PIP="$VENV_DIR/bin/pip"
"$PIP" install --upgrade "pip==24.3.1" "setuptools==75.6.0" "wheel==0.45.1"
if ! "$PIP" install --prefer-binary --only-binary=:all: -r "$BOT_DIR/requirements.txt"; then
  echo "[WARN] Wheel-only install failed, retrying with source fallback..."
  "$PIP" install --prefer-binary -r "$BOT_DIR/requirements.txt"
fi
"$PIP" install --prefer-binary "aiohttp==3.9.3"
"$PIP" check
"$PIP" freeze > "$BOT_DIR/requirements.lock.txt"

echo "[5/6] Restarting systemd service..."
systemctl daemon-reload
systemctl restart "$SERVICE_NAME"

echo "[6/6] Service status"
systemctl --no-pager --full status "$SERVICE_NAME" || true

echo "✅ Update completed successfully on branch: $TARGET_BRANCH"
