#!/usr/bin/env bash
# deploy.sh — Deploy SPARING tanpa Docker
# Jalankan sebagai root atau user dengan sudo
# Usage: sudo bash deploy.sh
#
# Asumsi server sudah punya:
#   - Python 3.11+, Node.js 18+, Nginx, MySQL 8.0
#   - SSL cert di /etc/letsencrypt/live/... (via Certbot)
#   - nginx.conf sudah dikopi ke /etc/nginx/sites-available/sparing

set -euo pipefail

# ─── Konfigurasi ─────────────────────────────────────────────────────────────
API_DIR="/opt/sparing/api"
FRONT_DIST="/var/www/sparing/frontend"
VENV_DIR="$API_DIR/.venv"
SERVICE_FILE="/etc/systemd/system/sparing-api.service"
NGINX_CONF="/etc/nginx/sites-available/sparing"
REPO_DIR="$(cd "$(dirname "$0")" && pwd)"

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
info()  { echo -e "${GREEN}[INFO]${NC}  $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
die()   { echo -e "${RED}[ERROR]${NC} $*"; exit 1; }

# ─── Cek dependensi OS ────────────────────────────────────────────────────────
check_deps() {
  info "Memeriksa dependensi sistem..."
  for cmd in python3 pip3 nginx mysql node npm rsync certbot; do
    command -v "$cmd" &>/dev/null || die "'$cmd' tidak ditemukan. Install dulu sebelum deploy."
  done
  python3 -c 'import sys; assert sys.version_info >= (3,11), "Python 3.11+ dibutuhkan"' \
    || die "Python 3.11+ dibutuhkan."
  info "Semua dependensi tersedia."
}

# ─── Salin file API ke /opt/sparing/api ──────────────────────────────────────
copy_api() {
  info "Menyalin kode API ke $API_DIR..."
  mkdir -p "$API_DIR"
  rsync -a --delete \
    --exclude='.venv' --exclude='__pycache__' --exclude='*.pyc' \
    --exclude='.env' --exclude='*.egg-info' \
    "$REPO_DIR/sparing_api/" "$API_DIR/"
  # Atur kepemilikan
  chown -R www-data:www-data "$API_DIR"
}

# ─── Setup Python virtualenv & install deps ───────────────────────────────────
setup_python() {
  info "Membuat virtual environment Python..."
  python3 -m venv "$VENV_DIR"
  "$VENV_DIR/bin/pip" install --upgrade pip setuptools wheel
  "$VENV_DIR/bin/pip" install -r "$API_DIR/requirements.txt"
  chown -R www-data:www-data "$VENV_DIR"
  info "Dependensi Python terinstall."
}

# ─── Cek & validasi .env ─────────────────────────────────────────────────────
setup_env() {
  if [[ ! -f "$API_DIR/.env" ]]; then
    warn ".env tidak ditemukan di $API_DIR/"
    cp "$REPO_DIR/sparing_api/.env.production" "$API_DIR/.env"
    chown www-data:www-data "$API_DIR/.env"
    chmod 600 "$API_DIR/.env"
    die "Harap edit $API_DIR/.env (DB_URL, JWT_SECRET, CORS_ORIGINS) lalu jalankan ulang deploy.sh"
  fi
  grep -q 'DB_URL' "$API_DIR/.env"   || die "DB_URL tidak ada di .env"
  grep -q 'JWT_SECRET' "$API_DIR/.env" || die "JWT_SECRET tidak ada di .env"
  # Pastikan DB_URL pakai localhost, bukan nama container Docker
  if grep -q '@mysql:' "$API_DIR/.env"; then
    warn "DB_URL masih mengarah ke hostname 'mysql' (Docker). Ganti ke '127.0.0.1' atau hostname MySQL lokal."
  fi
  info ".env valid."
}

# ─── Jalankan migrasi Alembic ─────────────────────────────────────────────────
run_migrations() {
  info "Menjalankan migrasi database Alembic..."
  cd "$API_DIR"
  sudo -u www-data "$VENV_DIR/bin/alembic" upgrade head
  info "Migrasi selesai."
}

# ─── Build & deploy frontend ──────────────────────────────────────────────────
build_frontend() {
  info "Build frontend Vue.js..."
  local tmp_build
  tmp_build=$(mktemp -d)
  rsync -a --exclude='node_modules' --exclude='dist' \
    "$REPO_DIR/sparing_front/" "$tmp_build/"
  cd "$tmp_build"
  npm ci --omit=dev
  npm run build
  mkdir -p "$FRONT_DIST"
  rsync -a --delete "$tmp_build/dist/" "$FRONT_DIST/"
  chown -R www-data:www-data "$FRONT_DIST"
  rm -rf "$tmp_build"
  info "Frontend tersalin ke $FRONT_DIST"
}

# ─── Install & aktifkan systemd service ──────────────────────────────────────
install_service() {
  info "Menginstall systemd service..."
  sed -e "s|__API_DIR__|$API_DIR|g" \
      -e "s|__VENV_DIR__|$VENV_DIR|g" \
      "$REPO_DIR/sparing-api.service" > "$SERVICE_FILE"
  systemctl daemon-reload
  systemctl enable sparing-api
  systemctl restart sparing-api
  sleep 2
  systemctl is-active --quiet sparing-api || die "Service sparing-api gagal start. Cek: journalctl -u sparing-api -n 50"
  info "Service sparing-api aktif."
}

# ─── Konfigurasi Nginx ────────────────────────────────────────────────────────
install_nginx() {
  info "Mengaktifkan konfigurasi Nginx..."
  cp "$REPO_DIR/nginx.conf" "$NGINX_CONF"
  ln -sf "$NGINX_CONF" /etc/nginx/sites-enabled/sparing
  rm -f /etc/nginx/sites-enabled/default
  nginx -t || die "Konfigurasi Nginx tidak valid. Cek: nginx -t"
  systemctl reload nginx
  info "Nginx dikonfigurasi."
}

# ─── Main ─────────────────────────────────────────────────────────────────────
main() {
  [[ $EUID -eq 0 ]] || die "Jalankan script ini sebagai root: sudo bash deploy.sh"
  check_deps
  copy_api
  setup_env
  setup_python
  run_migrations
  build_frontend
  install_service
  install_nginx
  echo ""
  info "=== Deploy selesai! ==="
  info "API  : https://sparingapi.mitramutiara.co.id"
  info "App  : https://sparingapp.mitramutiara.co.id"
  info "Cek log API: journalctl -u sparing-api -f"
}

main "$@"
