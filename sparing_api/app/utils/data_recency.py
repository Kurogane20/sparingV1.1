from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.utils.time import as_utc

# Readings dated further ahead than this are a wrong device clock, not data
FUTURE_TOLERANCE = timedelta(hours=1)


async def has_newer_data(db: AsyncSession, site_id: int, ts: datetime) -> bool:
    """True when the site already holds a reading newer than `ts`, i.e. `ts`
    belongs to a late (backfilled) burst — a logger resending its backlog.

    Alert state must follow the newest data only, so callers skip alert
    changes for such bursts. Rows dated beyond now + FUTURE_TOLERANCE are
    ignored so one bad device clock can't mark every later burst as late."""
    from app.models.models import SensorData
    ceiling = datetime.now(timezone.utc) + FUTURE_TOLERANCE
    newer = await db.scalar(
        select(SensorData.id).where(
            SensorData.site_id == site_id,
            # DB stores naive UTC — bind naive
            SensorData.ts > as_utc(ts).replace(tzinfo=None),
            SensorData.ts <= ceiling.replace(tzinfo=None),
        ).limit(1)
    )
    return newer is not None
