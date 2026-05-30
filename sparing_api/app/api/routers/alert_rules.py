from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone

from app.core.db import get_db
from app.api.deps import require_roles, get_current_user
from app.models.models import AlertRule, Site
from app.schemas.alert import AlertRuleCreate, AlertRuleUpdate, AlertRuleOut
from sqlalchemy import select

router = APIRouter()


async def _get_site_by_uid(uid: str, db: AsyncSession) -> Site:
    result = await db.execute(select(Site).where(Site.uid == uid))
    site = result.scalar_one_or_none()
    if not site:
        raise HTTPException(404, "Site not found")
    return site


@router.get("", response_model=list[AlertRuleOut])
async def list_alert_rules(
    site_uid: str,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    site = await _get_site_by_uid(site_uid, db)
    result = await db.execute(
        select(AlertRule).where(AlertRule.site_id == site.id).order_by(AlertRule.field)
    )
    return [
        AlertRuleOut(
            id=r.id, site_id=r.site_id, field=r.field,
            warning_min=r.warning_min, warning_max=r.warning_max,
            danger_min=r.danger_min, danger_max=r.danger_max,
            is_active=r.is_active,
        )
        for r in result.scalars().all()
    ]


@router.post("", response_model=AlertRuleOut, dependencies=[Depends(require_roles("admin", "operator"))])
async def create_alert_rule(
    site_uid: str,
    data: AlertRuleCreate,
    db: AsyncSession = Depends(get_db),
):
    site = await _get_site_by_uid(site_uid, db)
    now = datetime.now(timezone.utc)
    rule = AlertRule(
        site_id=site.id,
        field=data.field,
        warning_min=data.warning_min,
        warning_max=data.warning_max,
        danger_min=data.danger_min,
        danger_max=data.danger_max,
        is_active=data.is_active,
        created_at=now,
        updated_at=now,
    )
    db.add(rule)
    await db.commit()
    await db.refresh(rule)
    return AlertRuleOut(
        id=rule.id, site_id=rule.site_id, field=rule.field,
        warning_min=rule.warning_min, warning_max=rule.warning_max,
        danger_min=rule.danger_min, danger_max=rule.danger_max,
        is_active=rule.is_active,
    )


@router.patch("/{rule_id}", response_model=AlertRuleOut, dependencies=[Depends(require_roles("admin", "operator"))])
async def update_alert_rule(
    rule_id: int,
    data: AlertRuleUpdate,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(AlertRule).where(AlertRule.id == rule_id))
    rule = result.scalar_one_or_none()
    if not rule:
        raise HTTPException(404, "Rule not found")
    payload = data.model_dump(exclude_unset=True)
    for k, v in payload.items():
        setattr(rule, k, v)
    rule.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(rule)
    return AlertRuleOut(
        id=rule.id, site_id=rule.site_id, field=rule.field,
        warning_min=rule.warning_min, warning_max=rule.warning_max,
        danger_min=rule.danger_min, danger_max=rule.danger_max,
        is_active=rule.is_active,
    )


@router.delete("/{rule_id}", dependencies=[Depends(require_roles("admin"))])
async def delete_alert_rule(rule_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(AlertRule).where(AlertRule.id == rule_id))
    rule = result.scalar_one_or_none()
    if not rule:
        raise HTTPException(404, "Rule not found")
    await db.delete(rule)
    await db.commit()
    return {"ok": True}
