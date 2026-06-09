from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from app.core.config import settings
from app.core.exceptions import APIError
from app.api.routers import auth, sites, devices, ingest, data, metrics, admin, getdata, alerts, alert_rules, reports
from app.middlewares.request_id import RequestIDMiddleware
from app.middlewares.rate_limit import RateLimitMiddleware
from app.core.db import init_models
from app.core.logging import logger

scheduler = AsyncIOScheduler()

async def _cleanup_expired_tokens():
    """Delete blacklisted tokens that have already expired — runs hourly."""
    from app.core.db import get_db
    from app.models.models import AuthTokenBlacklist
    from sqlalchemy import delete
    from datetime import datetime, timezone
    try:
        async for db in get_db():
            await db.execute(
                delete(AuthTokenBlacklist).where(
                    AuthTokenBlacklist.expires_at < datetime.now(timezone.utc)
                )
            )
            await db.commit()
            break
        logger.info("Expired token blacklist entries cleaned up")
    except Exception:
        logger.exception("Token cleanup failed")


# Create FastAPI app
app = FastAPI(
    title="SPARING API",
    version="1.0.0",
    description="Environmental Monitoring System API",
    default_response_class=JSONResponse
)

# ========================================
# Exception Handlers
# ========================================

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.warning(f"Validation error on {request.method} {request.url}: {exc.errors()}")
    return JSONResponse(status_code=422, content={"detail": exc.errors()})

@app.exception_handler(APIError)
async def api_error_handler(request: Request, exc: APIError):
    """Handle custom API errors with consistent format."""
    logger.warning(f"API Error: {exc.code} - {exc.message}")
    return JSONResponse(
        status_code=exc.status_code,
        content=exc.to_dict()
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected errors."""
    logger.exception(f"Unhandled exception: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={
            "ok": False,
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "Terjadi kesalahan server"
            }
        }
    )

# ========================================
# Middleware Stack
# ========================================

# GZip compression for responses > 500 bytes
app.add_middleware(GZipMiddleware, minimum_size=500)

# Request ID for tracing
app.add_middleware(RequestIDMiddleware)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rate limiting for ingest endpoints
app.add_middleware(
    RateLimitMiddleware,
    routes_prefix=["/ingest"],
    rate_per_min=settings.rate_limit_per_min
)

# ========================================
# API Routers
# ========================================

app.include_router(auth.router, prefix="/auth", tags=["Auth"])
app.include_router(sites.router, prefix="/sites", tags=["Sites"])
app.include_router(devices.router, prefix="/devices", tags=["Devices"])
app.include_router(ingest.router, prefix="/ingest", tags=["Ingest"])
app.include_router(data.router, prefix="/data", tags=["Data"])
app.include_router(metrics.router, tags=["Metrics"])
app.include_router(admin.router, prefix="/admin", tags=["Admin"])
app.include_router(getdata.router, tags=["GetData"])
app.include_router(alerts.router, prefix="/alerts", tags=["Alerts"])
app.include_router(alert_rules.router, prefix="/alert-rules", tags=["AlertRules"])
app.include_router(reports.router, prefix="/reports", tags=["Reports"])

# ========================================
# Health Check Endpoints
# ========================================

@app.get("/healthz", tags=["Health"])
async def healthz():
    """Liveness probe - checks if service is running."""
    try:
        await init_models()
        return {"ok": True, "status": "healthy", "service": "sparing-api"}
    except Exception as e:
        logger.exception("Health check failed")
        return JSONResponse(
            {"ok": False, "status": "unhealthy", "error": str(e)},
            status_code=503
        )

@app.get("/readyz", tags=["Health"])
async def readyz():
    """Readiness probe - checks if service is ready to accept traffic."""
    from app.core.db import get_db
    try:
        async for db in get_db():
            from sqlalchemy import text
            await db.execute(text("SELECT 1"))
            await db.close()
        return {"ok": True, "status": "ready", "database": "connected"}
    except Exception as e:
        logger.exception("Readiness check failed")
        return JSONResponse(
            {"ok": False, "status": "not_ready", "error": str(e)},
            status_code=503
        )

async def _check_offline_devices():
    """Check for offline devices and trigger alerts — runs every 5 minutes."""
    from app.core.db import get_db
    from app.utils.alert_engine import check_offline_devices
    try:
        async for db in get_db():
            await check_offline_devices(db)
            break
    except Exception:
        logger.exception("Offline device scheduler failed")


@app.on_event("startup")
async def startup_event():
    scheduler.add_job(_cleanup_expired_tokens, "interval", hours=1, id="token_cleanup")
    scheduler.add_job(_check_offline_devices, "interval", minutes=5, id="offline_device_check")
    scheduler.start()
    logger.info("APScheduler started")


@app.on_event("shutdown")
async def shutdown_event():
    scheduler.shutdown(wait=False)


@app.get("/", tags=["Root"])
async def root():
    """API root endpoint."""
    return {
        "service": "SPARING API",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs"
    }
