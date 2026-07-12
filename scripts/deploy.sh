#!/usr/bin/env bash
#
# Deploy SPARING to production.
#
#   sudo bash /opt/sparing/repo/scripts/deploy.sh            # backend + frontend
#   sudo bash /opt/sparing/repo/scripts/deploy.sh backend    # backend only
#   sudo bash /opt/sparing/repo/scripts/deploy.sh frontend   # frontend only
#
# Automates the manual steps so a deploy can't silently skip the migration or
# the file sync (both have caused prod bugs before). Must run as root; it uses
# `sudo -u` for the www-data / build-user sub-steps.
#
# Two-directory layout (see docs): git repo at /opt/sparing/repo, the running
# gunicorn deployment at /opt/sparing/api — pulling the repo alone changes
# nothing until the code is synced across.

set -euo pipefail

REPO=/opt/sparing/repo
API=/opt/sparing/api
FRONTEND_SRC="$REPO/sparing_front"
WEB_ROOT=/var/www/sparing/frontend
SERVICE=sparing-api.service
HEALTH_URL=https://sparingapi.mitramutiara.co.id/healthz
BUILD_USER=mitramutiara         # owns the repo; runs the npm build
API_USER=www-data               # owns /opt/sparing/api and the .env
VENV="$API/.venv/bin/python"

TARGET="${1:-all}"

say() { printf '\n\033[1;34m==>\033[0m %s\n' "$*"; }

if [[ $EUID -ne 0 ]]; then
  echo "Run as root:  sudo bash $0 ${1:-}"
  exit 1
fi

# ── 1. Update the repo (root: .git internals are root-owned) ──────────
say "Pulling latest main into $REPO"
git -C "$REPO" pull origin main

deploy_backend() {
  # No --delete: only add/update files, never remove prod-only state.
  # .env / .venv / alembic.ini are excluded so they are never overwritten.
  say "Syncing backend code -> $API"
  rsync -rlptD \
    --exclude='.venv' --exclude='__pycache__' --exclude='*.pyc' \
    --exclude='.env' --exclude='alembic.ini' \
    --chown="$API_USER:$API_USER" \
    "$REPO/sparing_api/" "$API/"

  # Pre-flight: fail BEFORE restarting if the code doesn't import, so a broken
  # deploy never takes the live service down.
  say "Verifying the app imports (pre-flight)"
  ( cd "$API" && sudo -u "$API_USER" "$VENV" -c \
      "from app.main import app; print('  import ok, routes:', len(app.routes))" )

  say "Applying database migrations (alembic upgrade head)"
  ( cd "$API" && sudo -u "$API_USER" "$VENV" -m alembic upgrade head )

  say "Restarting $SERVICE"
  systemctl restart "$SERVICE"
}

deploy_frontend() {
  # rm as root first: past root-run builds left a root-owned dist/assets that
  # the build user then can't clear, breaking `npm run build` at emptyDir.
  say "Building frontend (as $BUILD_USER)"
  rm -rf "$FRONTEND_SRC/dist"
  sudo -u "$BUILD_USER" bash -lc "cd '$FRONTEND_SRC' && npm run build"

  # --delete here IS wanted: the web root must mirror dist so old hashed
  # bundles are removed.
  say "Publishing frontend -> $WEB_ROOT"
  rsync -a --delete --chown="$API_USER:$API_USER" "$FRONTEND_SRC/dist/" "$WEB_ROOT/"
  echo "  bundle: $(grep -o 'index-[A-Za-z0-9_-]*\.js' "$WEB_ROOT/index.html" | head -1)"
}

case "$TARGET" in
  all)      deploy_backend; deploy_frontend ;;
  backend)  deploy_backend ;;
  frontend) deploy_frontend ;;
  *) echo "Usage: $0 [all|backend|frontend]"; exit 1 ;;
esac

# ── Health check (backend touched) ────────────────────────────────────
if [[ "$TARGET" == "all" || "$TARGET" == "backend" ]]; then
  say "Health check"
  for i in $(seq 1 10); do
    code=$(curl -s -o /dev/null -w '%{http_code}' "$HEALTH_URL" || true)
    if [[ "$code" == "200" ]]; then
      echo "  healthy ($HEALTH_URL -> 200)"
      break
    fi
    if [[ $i -eq 10 ]]; then
      echo "  WARNING: health check did not return 200 (last: $code)"
      exit 1
    fi
    sleep 1
  done
fi

say "Deploy complete ($TARGET)."
