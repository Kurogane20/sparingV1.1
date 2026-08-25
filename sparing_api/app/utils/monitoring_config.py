from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import SiteMonitoringConfig


DEFAULT_CADENCE_SECONDS = 120
DEFAULT_STALE_AFTER_SECONDS = 90 * 60
DEFAULT_MAX_CHART_POINTS = 720
DEFAULT_MAX_RANGE_DAYS = 31

ALLOWED_FIELDS = ("ph", "tss", "debit")
ALLOWED_RESOLUTIONS_SECONDS = (120, 300, 600, 900, 1800, 3600, 10800, 21600, 86400)
PARAMETER_META = {
    "ph": {"label": "pH", "unit": "", "decimals": 2},
    "tss": {"label": "TSS", "unit": "mg/L", "decimals": 2},
    "debit": {"label": "Debit", "unit": "L/min", "decimals": 2},
}


async def ensure_site_monitoring_defaults(
    db: AsyncSession, site_id: int, updated_by_user_id: int | None = None
) -> SiteMonitoringConfig:
    """Add a site's configuration defaults when absent, without committing.

    The caller owns the transaction so site provisioning can commit the site,
    alert rules, and monitoring configuration atomically.
    """
    existing = await db.scalar(
        select(SiteMonitoringConfig).where(SiteMonitoringConfig.site_id == site_id)
    )
    if existing is not None:
        return existing

    config = SiteMonitoringConfig(
        site_id=site_id,
        cadence_seconds=DEFAULT_CADENCE_SECONDS,
        stale_after_seconds=DEFAULT_STALE_AFTER_SECONDS,
        max_chart_points=DEFAULT_MAX_CHART_POINTS,
        max_range_days=DEFAULT_MAX_RANGE_DAYS,
        updated_by_user_id=updated_by_user_id,
    )
    db.add(config)
    return config
