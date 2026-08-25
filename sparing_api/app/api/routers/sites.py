from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from datetime import datetime, timezone
from app.core.db import get_db
from app.api.deps import get_current_user, require_roles, get_viewer_site_uids
from app.models.models import AlertRule, OperationalRule, Site, SensorHealth, SiteMonitoringConfig
from app.schemas.site import SiteCreate, SiteUpdate, SiteOut, SiteDeviceKeyOut
from app.schemas.sensor_health import SensorHealthOut
from app.schemas.monitoring import MonitoringConfigOut, MonitoringConfigUpdate, MonitoringThresholdOut, OperationalRuleOut
from app.utils.alert_engine import seed_default_rules
from app.utils.device_secret import generate_device_secret
from app.utils.monitoring_config import ensure_site_monitoring_defaults

router = APIRouter()

@router.post("")
async def create_site(
    data: SiteCreate,
    db: AsyncSession = Depends(get_db),
    user=Depends(require_roles("admin", "operator")),
):
    exists = await db.execute(select(Site).where(Site.uid==data.uid))
    if exists.scalar_one_or_none():
        raise HTTPException(409, "uid exists")
    s = Site(**data.model_dump(), device_secret=generate_device_secret())
    db.add(s)
    await db.flush()
    await seed_default_rules(s.id, db, updated_by_user_id=user.id)
    await ensure_site_monitoring_defaults(db, s.id, updated_by_user_id=user.id)
    await db.commit()
    return {"ok": True, "id": s.id}


def _monitoring_config_out(
    site: Site,
    config: SiteMonitoringConfig,
    rules: list[OperationalRule],
    thresholds: list[AlertRule],
) -> MonitoringConfigOut:
    return MonitoringConfigOut(
        site_uid=site.uid,
        cadence_seconds=config.cadence_seconds,
        stale_after_seconds=config.stale_after_seconds,
        max_chart_points=config.max_chart_points,
        max_range_days=config.max_range_days,
        updated_by_user_id=config.updated_by_user_id,
        rules=[
            OperationalRuleOut(
                id=rule.id,
                field=rule.field,
                secondary_field=rule.secondary_field,
                rule_type=rule.rule_type,
                is_active=rule.is_active,
                window_seconds=rule.window_seconds,
                min_points=rule.min_points,
                hold_seconds=rule.hold_seconds,
                cooldown_seconds=rule.cooldown_seconds,
                abs_delta=rule.abs_delta,
                percent_delta=rule.percent_delta,
                minimum_baseline=rule.minimum_baseline,
                trigger_mode=rule.trigger_mode,
                no_flow_threshold=rule.no_flow_threshold,
                low_flow_threshold=rule.low_flow_threshold,
                recovery_threshold=rule.recovery_threshold,
                updated_by_user_id=rule.updated_by_user_id,
            )
            for rule in rules
        ],
        thresholds=[
            MonitoringThresholdOut(
                field=rule.field,
                warning_min=rule.warning_min,
                warning_max=rule.warning_max,
                danger_min=rule.danger_min,
                danger_max=rule.danger_max,
                reference_label=rule.reference_label,
                regulation=rule.regulation,
            )
            for rule in thresholds
        ],
    )


async def _load_monitoring_config(
    uid: str, db: AsyncSession
) -> tuple[Site, SiteMonitoringConfig, list[OperationalRule], list[AlertRule]]:
    site = (await db.execute(select(Site).where(Site.uid == uid))).scalar_one_or_none()
    if not site:
        raise HTTPException(404, "Not found")
    config = (
        await db.execute(
            select(SiteMonitoringConfig).where(SiteMonitoringConfig.site_id == site.id)
        )
    ).scalar_one_or_none()
    if not config:
        raise HTTPException(404, "Monitoring config not found")
    rules = (
        await db.execute(
            select(OperationalRule)
            .where(OperationalRule.site_id == site.id)
            .order_by(OperationalRule.field, OperationalRule.rule_type)
        )
    ).scalars().all()
    thresholds = (
        await db.execute(
            select(AlertRule)
            .where(AlertRule.site_id == site.id, AlertRule.is_active == True)
            .order_by(AlertRule.field)
        )
    ).scalars().all()
    return site, config, rules, thresholds


@router.get("/{uid}/monitoring-config", response_model=MonitoringConfigOut)
async def get_monitoring_config(
    uid: str,
    db: AsyncSession = Depends(get_db),
    viewer_uids: list[str] = Depends(get_viewer_site_uids),
    user=Depends(get_current_user),
):
    site, config, rules, thresholds = await _load_monitoring_config(uid, db)
    if user._role == "viewer" and site.uid not in viewer_uids:
        raise HTTPException(403, "Forbidden")
    return _monitoring_config_out(site, config, rules, thresholds)


@router.put("/{uid}/monitoring-config", response_model=MonitoringConfigOut)
async def update_monitoring_config(
    uid: str,
    data: MonitoringConfigUpdate,
    db: AsyncSession = Depends(get_db),
    user=Depends(require_roles("admin", "operator")),
):
    site = (await db.execute(select(Site).where(Site.uid == uid))).scalar_one_or_none()
    if not site:
        raise HTTPException(404, "Not found")
    config = (
        await db.execute(
            select(SiteMonitoringConfig).where(SiteMonitoringConfig.site_id == site.id)
        )
    ).scalar_one_or_none()
    if not config:
        config = await ensure_site_monitoring_defaults(db, site.id, user.id)

    config.cadence_seconds = data.cadence_seconds
    config.stale_after_seconds = data.stale_after_seconds
    config.max_chart_points = data.max_chart_points
    config.max_range_days = data.max_range_days
    config.updated_by_user_id = user.id

    await db.execute(delete(OperationalRule).where(OperationalRule.site_id == site.id))
    for rule in data.rules:
        db.add(
            OperationalRule(
                site_id=site.id,
                updated_by_user_id=user.id,
                **rule.model_dump(),
            )
        )
    await db.commit()
    site, config, rules, thresholds = await _load_monitoring_config(uid, db)
    return _monitoring_config_out(site, config, rules, thresholds)

@router.get("", response_model=list[SiteOut])
async def list_sites(db: AsyncSession = Depends(get_db), viewer_uids: list[str] = Depends(get_viewer_site_uids)):
    stmt = select(Site)
    if viewer_uids:
        stmt = stmt.where(Site.uid.in_(viewer_uids))
    res = await db.execute(stmt.order_by(Site.id.desc()))
    return [SiteOut(**{
        "id": s.id, "uid": s.uid, "name": s.name, "company_name": s.company_name,
        "lat": s.lat, "lon": s.lon, "is_active": s.is_active, "timezone": s.timezone or 'Asia/Jakarta'
    }) for s in res.scalars().all()]

@router.get("/{uid}", response_model=SiteOut)
async def get_site(uid: str, db: AsyncSession = Depends(get_db), viewer_uids: list[str] = Depends(get_viewer_site_uids)):
    res = await db.execute(select(Site).where(Site.uid==uid))
    s = res.scalar_one_or_none()
    if not s:
        raise HTTPException(404, "Not found")
    if viewer_uids and s.uid not in viewer_uids:
        raise HTTPException(403, "Forbidden")
    return SiteOut(id=s.id, uid=s.uid, name=s.name, company_name=s.company_name,
                   lat=s.lat, lon=s.lon, is_active=s.is_active, timezone=s.timezone or 'Asia/Jakarta')

@router.get("/{uid}/sensor-health", response_model=list[SensorHealthOut])
async def get_sensor_health(uid: str, db: AsyncSession = Depends(get_db),
                            viewer_uids: list[str] = Depends(get_viewer_site_uids)):
    res = await db.execute(select(Site).where(Site.uid == uid))
    s = res.scalar_one_or_none()
    if not s:
        raise HTTPException(404, "Not found")
    if viewer_uids and s.uid not in viewer_uids:
        raise HTTPException(403, "Forbidden")
    rows = (await db.execute(
        select(SensorHealth).where(SensorHealth.site_id == s.id)
    )).scalars().all()
    return [SensorHealthOut(
        field=h.field, status=h.status, anomaly_type=h.anomaly_type,
        reason=h.reason, last_value=h.last_value, updated_at=h.updated_at,
    ) for h in rows]

@router.patch("/{uid}", dependencies=[Depends(require_roles("admin","operator"))])
async def update_site(uid: str, data: SiteUpdate, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(Site).where(Site.uid==uid))
    s = res.scalar_one_or_none()
    if not s:
        raise HTTPException(404, "Not found")
    payload = data.model_dump(exclude_unset=True)
    for k, v in payload.items():
        setattr(s, k, v)
    await db.commit()
    return {"ok": True}

@router.delete("/{uid}", dependencies=[Depends(require_roles("admin"))])
async def delete_site(uid: str, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(Site).where(Site.uid==uid))
    s = res.scalar_one_or_none()
    if not s:
        raise HTTPException(404, "Not found")
    await db.delete(s); await db.commit()
    return {"ok": True}


@router.get("/{uid}/device-key", response_model=SiteDeviceKeyOut,
            dependencies=[Depends(require_roles("admin"))])
async def get_site_device_key(uid: str, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(Site).where(Site.uid == uid))
    s = res.scalar_one_or_none()
    if not s:
        raise HTTPException(404, "Site not found")
    if not s.device_secret:
        s.device_secret = generate_device_secret()
        await db.commit()
        await db.refresh(s)
    return SiteDeviceKeyOut(
        uid=s.uid,
        name=s.name,
        device_secret=s.device_secret,
        last_ingest_at=s.last_ingest_at,
    )


@router.post("/{uid}/rotate-secret", response_model=SiteDeviceKeyOut,
             dependencies=[Depends(require_roles("admin"))])
async def rotate_site_secret(uid: str, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(Site).where(Site.uid == uid))
    s = res.scalar_one_or_none()
    if not s:
        raise HTTPException(404, "Site not found")
    s.device_secret = generate_device_secret()
    await db.commit()
    await db.refresh(s)
    return SiteDeviceKeyOut(
        uid=s.uid,
        name=s.name,
        device_secret=s.device_secret,
        last_ingest_at=s.last_ingest_at,
    )
