"""Sensor data-quality / anomaly detection.

Pure detection functions (stdlib only) + DB orchestration that mirrors
app/utils/alert_engine.py. Never raises into the ingest path.
"""
import statistics
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.logging import logger
from app.utils.time import as_utc as _as_utc


@dataclass
class AnomalyResult:
    anomaly_type: str   # "implausible" | "flatline" | "spike" | "drift"
    severity: str       # "warning" | "danger"
    reason: str         # human-readable (Indonesian)


# ── Config (tunable) ────────────────────────────────────────────────
IN_SCOPE_FIELDS = ["ph", "tss", "cod", "nh3n", "temp", "debit"]

PLAUSIBLE_RANGES = {
    "ph":    (2.0, 12.0),
    "tss":   (0.0, 2000.0),
    "cod":   (0.0, 3000.0),
    "nh3n":  (0.0, 200.0),
    "temp":  (0.0, 50.0),
    "debit": (0.0, 1000.0),
}

SEVERITY_BY_TYPE = {
    "implausible": "danger",
    "flatline":    "danger",
    "spike":       "warning",
    "drift":       "warning",
}

FLATLINE_MIN_MINUTES = 15

SPIKE_WINDOW_MINUTES = 120
SPIKE_K = 5.0
SPIKE_MIN_POINTS = 10
SPIKE_MIN_ABS_DELTA = {
    "ph": 1.0, "tss": 50.0, "cod": 100.0, "nh3n": 3.0, "temp": 5.0, "debit": 50.0,
}

DRIFT_RECENT_HOURS = 24
DRIFT_BASELINE_DAYS = 7
DRIFT_PCT = 0.25
DRIFT_MIN_BASELINE = {
    "ph": 1.0, "tss": 10.0, "cod": 10.0, "nh3n": 1.0, "temp": 5.0, "debit": 5.0,
}


def check_implausible(field: str, value) -> AnomalyResult | None:
    """Flag a value outside its physically plausible range."""
    rng = PLAUSIBLE_RANGES.get(field)
    if rng is None or value is None:
        return None
    lo, hi = rng
    if value < lo or value > hi:
        return AnomalyResult(
            "implausible",
            SEVERITY_BY_TYPE["implausible"],
            f"{field} {value} di luar rentang wajar {lo}–{hi}",
        )
    return None


def check_flatline(samples: list, field: str) -> AnomalyResult | None:
    """samples: list of (ts, value) sorted ascending. Flag if all values are
    identical AND span at least FLATLINE_MIN_MINUTES (sensor stuck)."""
    pts = [(ts, v) for ts, v in samples if v is not None]
    if len(pts) < 2:
        return None
    span_min = (pts[-1][0] - pts[0][0]).total_seconds() / 60.0
    if span_min < FLATLINE_MIN_MINUTES:
        return None
    vals = [v for _, v in pts]
    if max(vals) == min(vals):
        return AnomalyResult(
            "flatline",
            SEVERITY_BY_TYPE["flatline"],
            f"Sensor {field} nyangkut di nilai {vals[0]} selama {int(span_min)} menit",
        )
    return None


def _mad(values: list) -> float:
    """Median Absolute Deviation — robust spread measure."""
    med = statistics.median(values)
    return statistics.median([abs(v - med) for v in values])


def check_spike(value, history: list, field: str) -> AnomalyResult | None:
    """Flag a reading that deviates far from the recent median (robust via MAD)."""
    if value is None or len(history) < SPIKE_MIN_POINTS:
        return None
    med = statistics.median(history)
    mad = _mad(history)
    delta = abs(value - med)
    min_delta = SPIKE_MIN_ABS_DELTA.get(field, 0.0)
    if delta <= min_delta:
        return None
    if mad == 0 or delta > SPIKE_K * mad:
        return AnomalyResult(
            "spike",
            SEVERITY_BY_TYPE["spike"],
            f"Lonjakan {field}: {value} (median {med:.2f})",
        )
    return None


def check_drift(recent: list, baseline: list, field: str) -> AnomalyResult | None:
    """Flag a sustained relative shift of the recent mean vs the baseline mean."""
    if not recent or not baseline:
        return None
    rmean = statistics.fmean(recent)
    bmean = statistics.fmean(baseline)
    floor = DRIFT_MIN_BASELINE.get(field, 1.0)
    rel = abs(rmean - bmean) / max(abs(bmean), floor)
    if rel > DRIFT_PCT:
        return AnomalyResult(
            "drift",
            SEVERITY_BY_TYPE["drift"],
            f"Drift {field}: rata-rata {rmean:.2f} vs baseline {bmean:.2f} ({rel * 100:.0f}%)",
        )
    return None


def scan_batch(samples: list, new_since: "datetime", field: str) -> list:
    """Evaluate each newly-ingested reading of a burst.

    Devices deliver hourly bursts (~30 readings, ~2 min apart), so detection
    windows are anchored to DATA timestamps, not server time. `samples` is the
    full window as (ts, value) sorted ascending — prior history plus the new
    burst. Readings with ts >= new_since are checked implausible-first, then
    spike against the values strictly before them.

    Returns [(ts, value, AnomalyResult)] for flagged readings.
    """
    hits = []
    prior = []
    for ts, value in samples:
        if ts >= new_since:
            result = check_implausible(field, value) or check_spike(value, prior, field)
            if result is not None:
                hits.append((ts, value, result))
        prior.append(value)
    return hits


def _status_for(result: "AnomalyResult | None") -> str:
    if result is None:
        return "ok"
    return "bad" if result.severity == "danger" else "warning"


async def _upsert_health(db: AsyncSession, site_id: int, field: str, value: float, result: "AnomalyResult | None", now: datetime) -> None:
    from app.models.models import SensorHealth
    status = _status_for(result)
    atype = result.anomaly_type if result else None
    reason = result.reason if result else None
    existing = (await db.execute(
        select(SensorHealth).where(
            SensorHealth.site_id == site_id,
            SensorHealth.field == field,
        )
    )).scalar_one_or_none()
    if existing is None:
        db.add(SensorHealth(
            site_id=site_id, field=field, status=status,
            anomaly_type=atype, reason=reason, last_value=value, updated_at=now,
        ))
    else:
        existing.status = status
        existing.anomaly_type = atype
        existing.reason = reason
        existing.last_value = value
        existing.updated_at = now


async def _maybe_create_alert(db: AsyncSession, site_id: int, device_uid: "str | None", field: str, value: float, result: AnomalyResult, now: datetime) -> None:
    """Insert a data_quality alert unless one of the same kind is already active.

    Dedup is NOT time-bounded: while an alert for the same (site, field,
    anomaly_type) stays active, repeated detections add nothing for the
    operator. Once it is acknowledged/resolved, a persisting condition may
    alert again. `.first()` (not scalar_one_or_none) keeps this robust if
    historical duplicates exist."""
    from app.models.models import Alert
    existing = await db.execute(
        select(Alert).where(
            Alert.site_id == site_id,
            Alert.field == field,
            Alert.category == "data_quality",
            Alert.anomaly_type == result.anomaly_type,
            Alert.status == "active",
        ).limit(1)
    )
    if existing.scalars().first() is not None:
        return
    db.add(Alert(
        site_id=site_id, device_uid=device_uid, field=field, value=value,
        threshold_type=result.severity, status="active", triggered_at=now,
        category="data_quality", anomaly_type=result.anomaly_type, detail=result.reason,
    ))


async def detect_realtime(site_id: int, site_uid: str, device_uid, readings: list) -> None:
    """Run implausible/flatline/spike over a freshly-ingested batch of readings.

    Devices deliver hourly bursts (~30 readings, ~2 min apart), so every window
    is anchored to the newest DATA timestamp — anchoring to server time would
    miss the data entirely. Own session; never raises."""
    from app.core.db import SessionLocal
    from app.models.models import SensorData
    try:
        batch_ts = [_as_utc(r["ts"]) for r in readings if r.get("ts") is not None]
        if not batch_ts:
            return
        anchor = max(batch_ts)       # newest reading in the burst
        new_since = min(batch_ts)    # start of the burst — readings from here are "new"
        now = datetime.now(timezone.utc)
        async with SessionLocal() as db:
            for field in IN_SCOPE_FIELDS:
                batch_vals = sorted(
                    ((_as_utc(r["ts"]), float(r[field])) for r in readings
                     if r.get(field) is not None and r.get("ts") is not None),
                    key=lambda s: s[0],
                )
                if not batch_vals:
                    continue
                newest_ts, newest_val = batch_vals[-1]

                # Full detection window anchored at the newest data timestamp;
                # includes the just-committed burst plus the previous one.
                col = getattr(SensorData, field)
                rows = (await db.execute(
                    select(SensorData.ts, col).where(
                        SensorData.site_id == site_id,
                        col.isnot(None),
                        SensorData.ts >= anchor - timedelta(minutes=SPIKE_WINDOW_MINUTES),
                    ).order_by(SensorData.ts.asc())
                )).all()
                samples = [(_as_utc(ts), v) for ts, v in rows]

                # Implausible/spike: every new reading in the burst is evaluated
                hits = scan_batch(samples, new_since, field)
                for ts, value, result in hits:
                    await _maybe_create_alert(db, site_id, device_uid, field, value, result, now)

                # Flatline: tail window relative to the data anchor
                flat_samples = [
                    s for s in samples
                    if s[0] >= anchor - timedelta(minutes=FLATLINE_MIN_MINUTES)
                ]
                flat_result = check_flatline(flat_samples, field)
                if flat_result is not None:
                    await _maybe_create_alert(db, site_id, device_uid, field, newest_val, flat_result, now)

                # Health badge reflects the newest reading: implausible > flatline > spike
                newest_hit = next((r for ts, _, r in hits if ts == newest_ts), None)
                if newest_hit is not None and newest_hit.anomaly_type == "implausible":
                    health_result = newest_hit
                else:
                    health_result = flat_result or newest_hit
                await _upsert_health(db, site_id, field, newest_val, health_result, now)
            await db.commit()
    except Exception:
        logger.exception(f"Anomaly realtime detection failed for site {site_uid}")


async def detect_drift_all_sites(db: AsyncSession) -> None:
    """Scheduled drift check across active sites x in-scope fields. Never raises.

    Windows are anchored to each site's newest data timestamp (devices ingest
    in hourly bursts). Sites with no data within DRIFT_RECENT_HOURS are skipped
    — the offline-device alert already covers those."""
    from app.models.models import Site, SensorData
    try:
        now = datetime.now(timezone.utc)
        sites = (await db.execute(select(Site).where(Site.is_active == True))).scalars().all()
        for site in sites:
            last_ts = (await db.execute(
                select(func.max(SensorData.ts)).where(SensorData.site_id == site.id)
            )).scalar()
            if last_ts is None:
                continue
            anchor = _as_utc(last_ts)
            if anchor < now - timedelta(hours=DRIFT_RECENT_HOURS):
                continue  # stale site — no fresh data to judge drift on
            recent_cutoff = anchor - timedelta(hours=DRIFT_RECENT_HOURS)
            baseline_start = anchor - timedelta(days=DRIFT_BASELINE_DAYS) - timedelta(hours=DRIFT_RECENT_HOURS)
            for field in IN_SCOPE_FIELDS:
                col = getattr(SensorData, field)
                rows = (await db.execute(
                    select(SensorData.ts, col).where(
                        SensorData.site_id == site.id,
                        col.isnot(None),
                        SensorData.ts >= baseline_start,
                    ).order_by(SensorData.ts.asc())
                )).all()
                recent = [v for ts, v in rows if _as_utc(ts) >= recent_cutoff]
                baseline = [v for ts, v in rows if _as_utc(ts) < recent_cutoff]
                if not recent or not baseline:
                    continue
                result = check_drift(recent, baseline, field)
                # Drift surfaces as an alert only; sensor_health is written
                # solely by detect_realtime to avoid two writers racing on the
                # same (site, field) row (the ~2-min realtime path would clobber
                # an hourly drift status within minutes).
                if result is not None:
                    await _maybe_create_alert(db, site.id, None, field, recent[-1], result, now)
        await db.commit()
    except Exception:
        logger.exception("Anomaly drift detection failed")
