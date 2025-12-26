# SPARING API (FastAPI + MySQL)

Production-grade API for wastewater and environmental monitoring with comprehensive sensor data management.

## Features

- JWT authentication with role-based access control (admin, operator, viewer)
- RESTful API for sites, devices, and sensor data management
- Real-time data ingestion with validation and idempotency
- Prometheus metrics and health checks
- Structured JSON logging with request IDs
- Rate limiting and security best practices
- Production-ready with Docker support

## Supported Sensors

The API supports monitoring for:
- Water quality: pH, TSS, Debit, NH3N, COD
- Environmental: Temperature, Humidity, Wind Speed, Wind Direction, Noise
- Air quality: CO, SO2, NO2, O3, PM2.5, PM10, TVOC
- Electrical: **Voltage**, **Current**

## Quickstart (Docker)

```bash
# Copy environment configuration
cp .env.example .env

# Start services
docker compose up --build

# API will be available at http://localhost:8000
```

Run seed data (creates default users):
```bash
docker compose exec api bash -lc "python seed.py"
```

**Interactive API docs:** http://localhost:8000/docs

**Default users (after seed):**
- `admin@example.com` / `Admin#123` (admin - full access)
- `op@example.com` / `Op#12345` (operator - can manage sites/devices)
- `viewer@example.com` / `Viewer#123` (viewer - read-only, site-scoped)

## Key Endpoints

- `POST /auth/login`
- `GET /me`
- `POST /auth/register` (admin)
- `POST /auth/refresh`
- `POST /auth/logout`

- `POST /sites` (admin/operator)
- `GET /sites`
- `GET /sites/{id}`
- `PATCH /sites/{id}`
- `DELETE /sites/{id}` (admin)

- `POST /devices` (admin/operator)
- `GET /devices?site_uid=...`
- `GET /devices/{id}`
- `PATCH /devices/{id}`
- `DELETE /devices/{id}` (admin)

- `POST /ingest/state` (+ optional `Idempotency-Key` header)
- `POST /ingest/bulk`

- `GET /data?site_uid=...&date_from=...&date_to=...&page=1&per_page=50&order=desc&fields=ph,tss,debit`
- `GET /data/last?site_uid=...`

- `GET /sites/{uid}/stats/last-seen`
- `GET /sites/{uid}/metrics`

## Documentation

- **[API Documentation](docs/API.md)** - Complete API reference with examples
- **[Deployment Guide](docs/DEPLOYMENT.md)** - Production deployment instructions
- **[Monitoring & Logging](docs/MONITORING.md)** - Observability best practices

## Production Deployment

For production deployment:

1. **Configure environment:**
   ```bash
   cp .env.production .env
   # Edit .env with production values (database, JWT secret, CORS, etc.)
   ```

2. **Generate strong JWT secret:**
   ```bash
   openssl rand -hex 32
   ```

3. **Deploy:**
   - See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) for detailed instructions
   - Supports Docker Compose, Kubernetes, and systemd deployments
   - Includes Nginx reverse proxy configuration
   - SSL/TLS setup with Let's Encrypt

4. **Monitor:**
   - Health checks: `/healthz` (liveness) and `/readyz` (readiness)
   - Prometheus metrics: `/metrics`
   - See [docs/MONITORING.md](docs/MONITORING.md) for Grafana dashboards

## Architecture Notes

- **Timezone**: All timestamps stored in UTC; API accepts any timezone offset
- **Authentication**: JWT-based with access and refresh tokens
- **Authorization**: Role-based (admin/operator/viewer) with site-scoped permissions
- **Rate Limiting**: In-memory limiter for `/ingest/*` (Redis recommended for multi-instance)
- **Database**: MySQL 8.0+ with Alembic migrations
- **Logging**: Structured JSON with request ID correlation
- **Validation**: Input validation with range checks for all sensor readings
- **Idempotency**: Optional `Idempotency-Key` header for critical operations

## Sensor Data Validation

The API validates all sensor readings:
- **pH**: 0-14
- **Temperature**: -40°C to 80°C
- **Humidity**: 0-100%
- **Voltage**: 0-1000V
- **Current**: 0-1000A
- **Wind Speed, Debit, TSS, Noise**: >= 0

## Security Features

- Argon2 password hashing
- JWT token blacklist on logout
- CORS configuration
- Rate limiting on ingestion endpoints
- SQL injection protection (SQLAlchemy ORM)
- Environment-based configuration
- Role-based access control (RBAC)

## Development

### Project Structure

```
sparing_api/
├── app/
│   ├── api/routers/       # API endpoints
│   ├── core/              # Configuration, database, security
│   ├── middlewares/       # Rate limiting, request ID
│   ├── models/            # SQLAlchemy models
│   ├── schemas/           # Pydantic schemas
│   └── main.py            # FastAPI application
├── alembic/               # Database migrations
├── docs/                  # Documentation
│   ├── API.md
│   ├── DEPLOYMENT.md
│   └── MONITORING.md
├── .env.example           # Development config
├── .env.production        # Production config template
└── requirements.txt       # Python dependencies
```

### Running Tests

```bash
# Install dev dependencies
pip install pytest pytest-asyncio httpx

# Run tests
pytest
```

### Database Migrations

```bash
# Create new migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1
```

## Scaling Considerations

- **Horizontal**: Stateless design allows multiple instances behind load balancer
- **Database**: Consider read replicas for read-heavy workloads
- **Caching**: Add Redis for session storage and distributed rate limiting
- **Workers**: Adjust `GUNICORN_WORKERS` based on CPU cores

## Support

For issues or questions, please check the documentation in the `docs/` folder or open an issue.
