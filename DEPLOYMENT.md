# SPARING Deployment Guide

Panduan lengkap untuk deploy SPARING ke VPS.

## Prerequisites

- VPS dengan Ubuntu 22.04+ (min 2GB RAM)
- Domain name yang sudah di-pointing ke VPS IP
- SSH access ke VPS

## Quick Start

```bash
# 1. SSH ke VPS
ssh root@your-vps-ip

# 2. Install dependencies
apt update && apt upgrade -y
apt install -y docker.io docker-compose nginx certbot python3-certbot-nginx git

# 3. Clone repository
git clone https://github.com/yourusername/sparing.git /var/www/sparing
cd /var/www/sparing

# 4. Setup environment
cp sparing_api/.env.production sparing_api/.env
nano sparing_api/.env  # Edit with your settings

# 5. Create .env for docker-compose
cat > .env << EOF
MYSQL_ROOT_PASSWORD=$(openssl rand -base64 32)
MYSQL_PASSWORD=$(openssl rand -base64 32)
EOF

# 6. Start services
docker-compose -f docker-compose.prod.yml up -d

# 7. Run database migrations & seed
docker-compose -f docker-compose.prod.yml exec api alembic upgrade head
docker-compose -f docker-compose.prod.yml exec api python seed.py

# 8. Build frontend
cd sparing_front
npm install
npm run build
cp -r dist /var/www/sparing/frontend/

# 9. Setup Nginx
cp nginx.conf /etc/nginx/sites-available/sparing
ln -s /etc/nginx/sites-available/sparing /etc/nginx/sites-enabled/
nginx -t && systemctl reload nginx

# 10. Get SSL certificate
certbot --nginx -d yourdomain.com -d www.yourdomain.com
```

## Environment Variables (.env.production)

```env
APP_ENV=production
JWT_SECRET=<generate-with-openssl-rand-base64-64>
DB_URL=mysql+aiomysql://sparing:password@mysql:3306/sparing_prod
CORS_ORIGINS=https://yourdomain.com
```

## Security Checklist

- [ ] Change default JWT_SECRET
- [ ] Use strong MySQL passwords
- [ ] Enable UFW firewall (`ufw allow 80,443/tcp`)
- [ ] Setup automatic backups
- [ ] Configure log rotation

## Useful Commands

```bash
# View logs
docker-compose -f docker-compose.prod.yml logs -f api

# Restart services  
docker-compose -f docker-compose.prod.yml restart

# Database backup
docker-compose -f docker-compose.prod.yml exec mysql mysqldump -u sparing -p sparing_prod > backup.sql
```
