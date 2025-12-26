# Production Deployment Guide

This guide covers deploying SPARING API to production environments.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Environment Configuration](#environment-configuration)
3. [Database Setup](#database-setup)
4. [Deployment Options](#deployment-options)
5. [Security Checklist](#security-checklist)
6. [Monitoring & Maintenance](#monitoring--maintenance)
7. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### System Requirements

- **Python**: 3.10 or higher
- **Database**: MySQL 8.0 or higher
- **RAM**: Minimum 2GB (4GB+ recommended)
- **CPU**: 2+ cores recommended
- **Disk**: 20GB+ (depends on data volume)

### Software Requirements

- Docker & Docker Compose (if using containerized deployment)
- Nginx or similar reverse proxy (recommended)
- SSL/TLS certificates (Let's Encrypt recommended)

---

## Environment Configuration

### 1. Copy Production Environment Template

```bash
cp .env.production .env
```

### 2. Configure Critical Settings

Edit `.env` and update the following **REQUIRED** settings:

```bash
# Database - Use production MySQL credentials
DB_URL=mysql+aiomysql://prod_user:STRONG_PASSWORD@mysql-host:3306/sparing_prod

# JWT Secret - Generate a strong random secret
JWT_SECRET=<generate-random-32-char-string>

# CORS Origins - Add your frontend URLs
CORS_ORIGINS=https://yourdomain.com,https://app.yourdomain.com
```

### Generate Strong JWT Secret

```bash
# Linux/Mac
openssl rand -hex 32

# Python
python -c "import secrets; print(secrets.token_hex(32))"
```

### 3. Optional Settings

```bash
# Workers (adjust based on CPU cores)
GUNICORN_WORKERS=4  # Formula: (2 x CPU cores) + 1

# Rate Limiting
RATE_LIMIT_PER_MIN=120  # Adjust based on expected traffic

# Logging
LOG_LEVEL=warning  # Options: debug, info, warning, error

# Sentry (for error tracking)
SENTRY_DSN=https://your-sentry-dsn@sentry.io/project-id
```

---

## Database Setup

### 1. Create Production Database

```sql
CREATE DATABASE sparing_prod CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'prod_user'@'%' IDENTIFIED BY 'STRONG_PASSWORD_HERE';
GRANT ALL PRIVILEGES ON sparing_prod.* TO 'prod_user'@'%';
FLUSH PRIVILEGES;
```

### 2. Run Migrations

```bash
# Using Docker
docker compose exec api alembic upgrade head

# Without Docker
alembic upgrade head
```

### 3. Seed Initial Data (Optional)

```bash
# Create admin user and sample data
docker compose exec api python seed.py
```

**⚠️ Warning**: Change default passwords immediately after seeding!

---

## Deployment Options

### Option 1: Docker Compose (Recommended for Small-Medium Scale)

#### 1.1 Production Docker Compose

Create `docker-compose.prod.yml`:

```yaml
version: '3.8'

services:
  api:
    build: .
    container_name: sparing_api
    restart: unless-stopped
    env_file: .env
    ports:
      - "8000:8000"
    depends_on:
      - mysql
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/healthz"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    networks:
      - sparing_network

  mysql:
    image: mysql:8.0
    container_name: sparing_mysql
    restart: unless-stopped
    environment:
      MYSQL_ROOT_PASSWORD: ${MYSQL_ROOT_PASSWORD}
      MYSQL_DATABASE: sparing_prod
      MYSQL_USER: prod_user
      MYSQL_PASSWORD: ${MYSQL_PASSWORD}
    volumes:
      - mysql_data:/var/lib/mysql
      - ./mysql-conf:/etc/mysql/conf.d
    ports:
      - "3306:3306"
    networks:
      - sparing_network

  nginx:
    image: nginx:alpine
    container_name: sparing_nginx
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
    depends_on:
      - api
    networks:
      - sparing_network

volumes:
  mysql_data:

networks:
  sparing_network:
```

#### 1.2 Deploy

```bash
docker compose -f docker-compose.prod.yml up -d
```

#### 1.3 View Logs

```bash
docker compose -f docker-compose.prod.yml logs -f api
```

---

### Option 2: Kubernetes

#### 2.1 Create Deployment

`k8s/deployment.yaml`:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: sparing-api
  labels:
    app: sparing-api
spec:
  replicas: 3
  selector:
    matchLabels:
      app: sparing-api
  template:
    metadata:
      labels:
        app: sparing-api
    spec:
      containers:
      - name: api
        image: your-registry/sparing-api:latest
        ports:
        - containerPort: 8000
        envFrom:
        - configMapRef:
            name: sparing-config
        - secretRef:
            name: sparing-secrets
        livenessProbe:
          httpGet:
            path: /healthz
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /readyz
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 5
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
```

#### 2.2 Create Service

`k8s/service.yaml`:

```yaml
apiVersion: v1
kind: Service
metadata:
  name: sparing-api
spec:
  selector:
    app: sparing-api
  ports:
  - protocol: TCP
    port: 80
    targetPort: 8000
  type: LoadBalancer
```

#### 2.3 Deploy to Kubernetes

```bash
kubectl apply -f k8s/
```

---

### Option 3: Systemd Service (VPS/Bare Metal)

#### 3.1 Create Virtual Environment

```bash
cd /opt/sparing_api
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

#### 3.2 Create Systemd Service

`/etc/systemd/system/sparing-api.service`:

```ini
[Unit]
Description=SPARING API Service
After=network.target mysql.service

[Service]
Type=notify
User=www-data
Group=www-data
WorkingDirectory=/opt/sparing_api
Environment="PATH=/opt/sparing_api/venv/bin"
EnvironmentFile=/opt/sparing_api/.env
ExecStart=/opt/sparing_api/venv/bin/gunicorn app.main:app \
    --workers 4 \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind 0.0.0.0:8000 \
    --access-logfile /var/log/sparing/access.log \
    --error-logfile /var/log/sparing/error.log
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

#### 3.3 Enable and Start Service

```bash
sudo systemctl daemon-reload
sudo systemctl enable sparing-api
sudo systemctl start sparing-api
sudo systemctl status sparing-api
```

---

## Reverse Proxy Setup (Nginx)

### Nginx Configuration

`/etc/nginx/sites-available/sparing-api`:

```nginx
upstream sparing_api {
    server localhost:8000;
    keepalive 64;
}

# HTTP to HTTPS redirect
server {
    listen 80;
    server_name api.yourdomain.com;
    return 301 https://$server_name$request_uri;
}

# HTTPS server
server {
    listen 443 ssl http2;
    server_name api.yourdomain.com;

    # SSL Configuration
    ssl_certificate /etc/letsencrypt/live/api.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.yourdomain.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    # Security Headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

    # Logging
    access_log /var/log/nginx/sparing-api-access.log;
    error_log /var/log/nginx/sparing-api-error.log;

    # Proxy settings
    location / {
        proxy_pass http://sparing_api;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # Health check endpoint (no auth required)
    location /healthz {
        proxy_pass http://sparing_api;
        access_log off;
    }

    # Rate limiting for sensitive endpoints
    location /ingest {
        limit_req zone=ingest_limit burst=20 nodelay;
        proxy_pass http://sparing_api;
    }
}

# Rate limit zone definition
limit_req_zone $binary_remote_addr zone=ingest_limit:10m rate=10r/s;
```

### Enable Site

```bash
sudo ln -s /etc/nginx/sites-available/sparing-api /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### SSL Certificate (Let's Encrypt)

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d api.yourdomain.com
```

---

## Security Checklist

### Before Deployment

- [ ] Change default JWT_SECRET to a strong random value
- [ ] Update database credentials (no default passwords)
- [ ] Configure CORS_ORIGINS to only allow your frontend domains
- [ ] Enable HTTPS/SSL certificates
- [ ] Set APP_ENV=production
- [ ] Change default user passwords from seed.py
- [ ] Review and restrict database user permissions
- [ ] Enable firewall (allow only ports 80, 443, 22)
- [ ] Set up fail2ban or similar intrusion prevention
- [ ] Configure rate limiting
- [ ] Enable database backups
- [ ] Set up monitoring and alerting

### Database Security

```sql
-- Restrict remote access
UPDATE mysql.user SET host='localhost' WHERE user='prod_user';
FLUSH PRIVILEGES;

-- Enable SSL for database connections
-- Add to my.cnf:
[mysqld]
require_secure_transport=ON
```

### Application Security

```bash
# Restrict file permissions
chmod 600 .env
chmod 700 /opt/sparing_api

# Run as non-root user
chown -R www-data:www-data /opt/sparing_api
```

---

## Monitoring & Maintenance

### 1. Prometheus Metrics

The API exposes Prometheus metrics at `/metrics`. Configure Prometheus to scrape:

```yaml
scrape_configs:
  - job_name: 'sparing-api'
    static_configs:
      - targets: ['localhost:8000']
```

### 2. Log Aggregation

Forward logs to a centralized logging system:

```bash
# Example: Forward to ELK Stack
filebeat.inputs:
- type: log
  paths:
    - /var/log/sparing/*.log
  json.keys_under_root: true
```

### 3. Database Backups

```bash
# Daily backup script
#!/bin/bash
BACKUP_DIR="/backups/mysql"
DATE=$(date +%Y%m%d_%H%M%S)

mysqldump -u prod_user -p'PASSWORD' sparing_prod | gzip > $BACKUP_DIR/sparing_$DATE.sql.gz

# Keep only last 7 days
find $BACKUP_DIR -name "sparing_*.sql.gz" -mtime +7 -delete
```

Add to crontab:
```bash
0 2 * * * /opt/scripts/backup-db.sh
```

### 4. Health Monitoring

```bash
# Simple health check script
#!/bin/bash
HEALTH_URL="https://api.yourdomain.com/healthz"

if ! curl -sf $HEALTH_URL | grep -q '"ok":true'; then
    echo "API health check failed!" | mail -s "SPARING API Alert" admin@yourdomain.com
fi
```

### 5. Performance Monitoring

Monitor these key metrics:
- Response time (p50, p95, p99)
- Request rate
- Error rate
- Database connection pool utilization
- Memory usage
- CPU usage

---

## Troubleshooting

### API Won't Start

```bash
# Check logs
docker compose logs -f api

# Or systemd
sudo journalctl -u sparing-api -f

# Common issues:
# 1. Database connection failed - check DB_URL
# 2. Port already in use - check with: lsof -i :8000
# 3. Missing migrations - run: alembic upgrade head
```

### Database Connection Issues

```bash
# Test database connection
docker compose exec api python -c "
from app.core.db import engine
from sqlalchemy import text
with engine.connect() as conn:
    result = conn.execute(text('SELECT 1'))
    print('Database connected!')
"
```

### High Memory Usage

```bash
# Reduce workers
GUNICORN_WORKERS=2

# Or limit per-worker memory
gunicorn --max-requests 1000 --max-requests-jitter 100 ...
```

### Slow Queries

```bash
# Enable MySQL slow query log
# Add to my.cnf:
[mysqld]
slow_query_log = 1
slow_query_log_file = /var/log/mysql/slow-query.log
long_query_time = 1

# Analyze slow queries
mysqldumpslow /var/log/mysql/slow-query.log
```

### Rate Limit Issues

Adjust in `.env`:
```bash
RATE_LIMIT_PER_MIN=240  # Increase limit
```

Or implement Redis-based distributed rate limiting for multi-instance deployments.

---

## Scaling Considerations

### Horizontal Scaling

1. **Load Balancer**: Use Nginx, HAProxy, or cloud load balancer
2. **Stateless Design**: API is stateless, can scale horizontally
3. **Distributed Rate Limiting**: Replace in-memory limiter with Redis
4. **Database**: Consider read replicas for read-heavy workloads

### Vertical Scaling

1. Increase `GUNICORN_WORKERS`
2. Allocate more RAM/CPU to containers
3. Optimize database with indexes and query optimization

### Caching

Consider adding Redis for:
- Session storage
- Distributed rate limiting
- Query result caching
- Real-time metrics

---

## Updating the Application

### Zero-Downtime Deployment

```bash
# 1. Pull latest code
git pull origin main

# 2. Build new image
docker compose -f docker-compose.prod.yml build

# 3. Rolling update
docker compose -f docker-compose.prod.yml up -d --no-deps --build api

# 4. Run migrations if needed
docker compose exec api alembic upgrade head
```

### Rollback

```bash
# Rollback to previous image
docker tag sparing-api:current sparing-api:rollback
docker compose -f docker-compose.prod.yml up -d api

# Or rollback migrations
docker compose exec api alembic downgrade -1
```

---

## Support & Maintenance

### Regular Maintenance Tasks

- **Daily**: Check logs for errors
- **Weekly**: Review monitoring metrics, check disk space
- **Monthly**: Update dependencies, security patches
- **Quarterly**: Review and optimize database indexes
- **Yearly**: Review and update SSL certificates

### Getting Help

- Check logs: `docker compose logs -f`
- Review documentation: `/docs` folder
- Open issue on repository

---

## Production Checklist

Before going live:

- [ ] All environment variables configured
- [ ] Database migrations run
- [ ] SSL/HTTPS enabled
- [ ] Firewall configured
- [ ] Backups scheduled
- [ ] Monitoring configured
- [ ] Logs centralized
- [ ] Health checks passing
- [ ] Load testing completed
- [ ] Security audit performed
- [ ] Documentation reviewed
- [ ] Team trained on deployment process

---

**Last Updated**: 2024-01-01
**Version**: 1.0.0
