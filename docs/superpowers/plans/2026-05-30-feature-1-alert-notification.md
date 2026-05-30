# Feature 1: Alert & Notification System — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** When sensor data breaches baku mutu thresholds, create an Alert record in the database, show a badge on the frontend Header bell icon, and send an email to site-assigned users.

**Architecture:** Alert rules (`AlertRule`) are stored per-site in the DB (seeded from defaults on site creation). After each data ingest (both `/api/post-data` and `/ingest/state`), the async alert engine checks incoming values against active rules and creates `Alert` records. The frontend polls `/alerts/count` every 30s and renders an `AlertDropdown` component in the Header. A separate APScheduler job creates offline-device alerts every 5 minutes.

**Tech Stack:** FastAPI + SQLAlchemy async + MySQL + APScheduler (already installed) · aiosmtplib (new) · Vue 3 Composition API

---

## File Map

### Backend — Create
- `sparing_api/app/schemas/alert.py` — Pydantic schemas for AlertRule and Alert
- `sparing_api/app/utils/alert_engine.py` — async alert trigger logic (called after ingest)
- `sparing_api/app/utils/email.py` — async email sender via SMTP
- `sparing_api/app/api/routers/alert_rules.py` — CRUD for AlertRule per site
- `sparing_api/app/api/routers/alerts.py` — list/count/acknowledge Alert records
- `sparing_api/alembic/versions/0002_add_alerts.py` — DB migration
- `sparing_api/app/tests/test_alert_engine.py` — unit tests for alert engine

### Backend — Modify
- `sparing_api/requirements.txt` — add `aiosmtplib==23.0.1`
- `sparing_api/app/models/models.py` — add `AlertRule` and `Alert` models
- `sparing_api/app/core/config.py` — add SMTP settings fields
- `sparing_api/app/main.py` — register new routers + add offline-device scheduler job
- `sparing_api/app/api/routers/getdata.py` — call alert engine after commit
- `sparing_api/app/api/routers/ingest.py` — call alert engine after commit

### Frontend — Create
- `sparing_front/resources/js/Components/AlertDropdown.vue` — bell icon + dropdown panel

### Frontend — Modify
- `sparing_front/resources/js/Composables/useApi.js` — add alert API methods
- `sparing_front/resources/js/Components/Header.vue` — embed AlertDropdown, add `/alerts` to pageTitles
- `sparing_front/resources/js/Pages/Sites/Index.vue` — add Baku Mutu tab to edit modal

---

## Task 1: Add aiosmtplib dependency and SMTP config

**Files:**
- Modify: `sparing_api/requirements.txt`
- Modify: `sparing_api/app/core/config.py`

- [ ] **Step 1: Add aiosmtplib to requirements.txt**

Open `sparing_api/requirements.txt` and add after `apscheduler==3.10.4`:
```
aiosmtplib==23.0.1
```

- [ ] **Step 2: Add SMTP fields to Settings in config.py**

In `sparing_api/app/core/config.py`, add inside the `Settings` class after `log_level`:
```python
    # SMTP email settings (optional — email skipped if smtp_host is empty)
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_pass: str = ""
    smtp_from: str = "noreply@sparing.local"
    smtp_tls: bool = True
```

- [ ] **Step 3: Install the new dependency**

```bash
cd sparing_api
pip install aiosmtplib==23.0.1
```

Expected output: `Successfully installed aiosmtplib-23.0.1`

- [ ] **Step 4: Commit**

```bash
git add sparing_api/requirements.txt sparing_api/app/core/config.py
git commit -m "chore: add aiosmtplib and SMTP config settings"
```

---

## Task 2: Database migration — alert_rules and alerts tables

**Files:**
- Create: `sparing_api/alembic/versions/0002_add_alerts.py`

- [ ] **Step 1: Create migration file**

Create `sparing_api/alembic/versions/0002_add_alerts.py`:
```python
from alembic import op
import sqlalchemy as sa

revision = '0002_add_alerts'
down_revision = '0001_initial'
branch_labels = None
depends_on = None

def upgrade():
    op.create_table('alert_rules',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('site_id', sa.Integer(), sa.ForeignKey('sites.id', ondelete='CASCADE'), nullable=False),
        sa.Column('field', sa.String(32), nullable=False),
        sa.Column('warning_min', sa.Float(), nullable=True),
        sa.Column('warning_max', sa.Float(), nullable=True),
        sa.Column('danger_min', sa.Float(), nullable=True),
        sa.Column('danger_max', sa.Float(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('1')),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint('site_id', 'field', name='uq_alert_rule_site_field'),
    )
    op.create_index('ix_alert_rules_site_id', 'alert_rules', ['site_id'])

    op.create_table('alerts',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('site_id', sa.Integer(), sa.ForeignKey('sites.id', ondelete='CASCADE'), nullable=False),
        sa.Column('device_uid', sa.String(64), nullable=True),
        sa.Column('field', sa.String(32), nullable=False),
        sa.Column('value', sa.Float(), nullable=False),
        sa.Column('threshold_type', sa.String(16), nullable=False),  # warning | danger
        sa.Column('status', sa.String(16), nullable=False, server_default='active'),  # active | acknowledged | resolved
        sa.Column('triggered_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('acknowledged_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('acknowledged_by_user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
    )
    op.create_index('ix_alerts_site_status', 'alerts', ['site_id', 'status', 'triggered_at'])

def downgrade():
    op.drop_index('ix_alerts_site_status', table_name='alerts')
    op.drop_table('alerts')
    op.drop_index('ix_alert_rules_site_id', table_name='alert_rules')
    op.drop_table('alert_rules')
```

- [ ] **Step 2: Run migration**

```bash
cd sparing_api
alembic upgrade head
```

Expected output:
```
INFO  [alembic.runtime.migration] Running upgrade 0001_initial -> 0002_add_alerts, add_alerts
```

- [ ] **Step 3: Commit**

```bash
git add sparing_api/alembic/versions/0002_add_alerts.py
git commit -m "feat: migration for alert_rules and alerts tables"
```

---

## Task 3: SQLAlchemy models — AlertRule and Alert

**Files:**
- Modify: `sparing_api/app/models/models.py`

- [ ] **Step 1: Add AlertRule and Alert models**

At the end of `sparing_api/app/models/models.py`, append:
```python
class AlertRule(Base):
    __tablename__ = "alert_rules"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id", ondelete="CASCADE"), index=True)
    field: Mapped[str] = mapped_column(String(32))
    warning_min: Mapped[float | None] = mapped_column(Float, nullable=True)
    warning_max: Mapped[float | None] = mapped_column(Float, nullable=True)
    danger_min: Mapped[float | None] = mapped_column(Float, nullable=True)
    danger_max: Mapped[float | None] = mapped_column(Float, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    site: Mapped["Site"] = relationship()

    __table_args__ = (UniqueConstraint("site_id", "field", name="uq_alert_rule_site_field"),)


class Alert(Base):
    __tablename__ = "alerts"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id", ondelete="CASCADE"), index=True)
    device_uid: Mapped[str | None] = mapped_column(String(64), nullable=True)
    field: Mapped[str] = mapped_column(String(32))
    value: Mapped[float] = mapped_column(Float)
    threshold_type: Mapped[str] = mapped_column(String(16))  # warning | danger
    status: Mapped[str] = mapped_column(String(16), default="active")  # active | acknowledged | resolved
    triggered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    acknowledged_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    site: Mapped["Site"] = relationship()
```

- [ ] **Step 2: Verify models import without error**

```bash
cd sparing_api
python -c "from app.models.models import AlertRule, Alert; print('OK')"
```

Expected output: `OK`

- [ ] **Step 3: Commit**

```bash
git add sparing_api/app/models/models.py
git commit -m "feat: add AlertRule and Alert SQLAlchemy models"
```

---

## Task 4: Pydantic schemas for alerts

**Files:**
- Create: `sparing_api/app/schemas/alert.py`

- [ ] **Step 1: Create schema file**

Create `sparing_api/app/schemas/alert.py`:
```python
from pydantic import BaseModel
from datetime import datetime

# --- AlertRule schemas ---

class AlertRuleCreate(BaseModel):
    field: str
    warning_min: float | None = None
    warning_max: float | None = None
    danger_min: float | None = None
    danger_max: float | None = None
    is_active: bool = True

class AlertRuleUpdate(BaseModel):
    warning_min: float | None = None
    warning_max: float | None = None
    danger_min: float | None = None
    danger_max: float | None = None
    is_active: bool | None = None

class AlertRuleOut(BaseModel):
    id: int
    site_id: int
    field: str
    warning_min: float | None
    warning_max: float | None
    danger_min: float | None
    danger_max: float | None
    is_active: bool

# --- Alert schemas ---

class AlertOut(BaseModel):
    id: int
    site_id: int
    site_uid: str
    site_name: str
    device_uid: str | None
    field: str
    value: float
    threshold_type: str
    status: str
    triggered_at: datetime
    acknowledged_at: datetime | None
    acknowledged_by_user_id: int | None

class AlertCountOut(BaseModel):
    count: int
```

- [ ] **Step 2: Verify import**

```bash
cd sparing_api
python -c "from app.schemas.alert import AlertRuleOut, AlertOut; print('OK')"
```

Expected output: `OK`

- [ ] **Step 3: Commit**

```bash
git add sparing_api/app/schemas/alert.py
git commit -m "feat: add Pydantic schemas for AlertRule and Alert"
```

---

## Task 5: Alert engine utility

**Files:**
- Create: `sparing_api/app/utils/alert_engine.py`
- Create: `sparing_api/app/tests/test_alert_engine.py`

- [ ] **Step 1: Write failing test**

Create `sparing_api/app/tests/test_alert_engine.py`:
```python
import pytest
from unittest.mock import AsyncMock, MagicMock
from app.utils.alert_engine import _is_violated, _determine_threshold_type

def test_is_violated_upper_limit():
    rule = MagicMock(warning_min=None, warning_max=150.0, danger_min=None, danger_max=200.0)
    assert _is_violated(120.0, rule, "warning") is False
    assert _is_violated(160.0, rule, "warning") is True
    assert _is_violated(210.0, rule, "danger") is True

def test_is_violated_range():
    rule = MagicMock(warning_min=6.5, warning_max=8.5, danger_min=6.0, danger_max=9.0)
    assert _is_violated(7.2, rule, "warning") is False   # within range
    assert _is_violated(6.2, rule, "warning") is True    # below min
    assert _is_violated(9.1, rule, "danger") is True     # above max
    assert _is_violated(6.05, rule, "danger") is False   # within danger range

def test_determine_threshold_type_danger():
    rule = MagicMock(warning_min=None, warning_max=150.0, danger_min=None, danger_max=200.0)
    assert _determine_threshold_type(210.0, rule) == "danger"

def test_determine_threshold_type_warning():
    rule = MagicMock(warning_min=None, warning_max=150.0, danger_min=None, danger_max=200.0)
    assert _determine_threshold_type(160.0, rule) == "warning"

def test_determine_threshold_type_normal():
    rule = MagicMock(warning_min=None, warning_max=150.0, danger_min=None, danger_max=200.0)
    assert _determine_threshold_type(100.0, rule) is None
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
cd sparing_api
python -m pytest app/tests/test_alert_engine.py -v
```

Expected: `ImportError` or `ModuleNotFoundError` (file doesn't exist yet)

- [ ] **Step 3: Create alert_engine.py**

Create `sparing_api/app/utils/alert_engine.py`:
```python
import asyncio
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.models import AlertRule, Alert, Site, User, ViewerSite
from app.core.logging import logger

# Default rules seeded when a site is created
DEFAULT_ALERT_RULES = [
    {"field": "ph",    "warning_min": 6.5, "warning_max": 8.5, "danger_min": 6.0,  "danger_max": 9.0},
    {"field": "tss",   "warning_min": None, "warning_max": 150, "danger_min": None, "danger_max": 200},
    {"field": "cod",   "warning_min": None, "warning_max": 200, "danger_min": None, "danger_max": 300},
    {"field": "nh3n",  "warning_min": None, "warning_max": 7,   "danger_min": None, "danger_max": 10},
    {"field": "temp",  "warning_min": None, "warning_max": 30,  "danger_min": None, "danger_max": 35},
    {"field": "noise", "warning_min": None, "warning_max": 60,  "danger_min": None, "danger_max": 70},
    {"field": "pm25",  "warning_min": None, "warning_max": 35,  "danger_min": None, "danger_max": 65},
    {"field": "pm10",  "warning_min": None, "warning_max": 100, "danger_min": None, "danger_max": 150},
]


def _is_violated(value: float, rule: AlertRule, level: str) -> bool:
    """Return True if value breaches the given threshold level (warning or danger)."""
    mn = getattr(rule, f"{level}_min")
    mx = getattr(rule, f"{level}_max")
    if mn is None and mx is None:
        return False
    if mn is not None and mx is not None:
        return value < mn or value > mx
    if mx is not None:
        return value > mx
    return value < mn  # type: ignore[return-value]


def _determine_threshold_type(value: float, rule: AlertRule) -> str | None:
    """Return 'danger', 'warning', or None based on which threshold is breached."""
    if _is_violated(value, rule, "danger"):
        return "danger"
    if _is_violated(value, rule, "warning"):
        return "warning"
    return None


async def seed_default_rules(site_id: int, db: AsyncSession) -> None:
    """Insert default AlertRule records for a newly created site."""
    now = datetime.now(timezone.utc)
    for rule_def in DEFAULT_ALERT_RULES:
        rule = AlertRule(
            site_id=site_id,
            field=rule_def["field"],
            warning_min=rule_def["warning_min"],
            warning_max=rule_def["warning_max"],
            danger_min=rule_def["danger_min"],
            danger_max=rule_def["danger_max"],
            is_active=True,
            created_at=now,
            updated_at=now,
        )
        db.add(rule)
    await db.commit()


async def trigger_alerts(
    site_id: int,
    site_uid: str,
    device_uid: str | None,
    data: dict,
) -> None:
    """Check data against active AlertRules and create Alert records for violations.
    Creates its own DB session so it is safe to call via asyncio.create_task()
    after the request session has been committed and closed.
    """
    from app.core.db import SessionLocal
    try:
        async with SessionLocal() as db:
            rules_result = await db.execute(
                select(AlertRule).where(
                    AlertRule.site_id == site_id,
                    AlertRule.is_active == True,
                )
            )
            rules = rules_result.scalars().all()

            now = datetime.now(timezone.utc)
            dedup_cutoff = now - timedelta(minutes=30)
            new_alerts = []

            for rule in rules:
                value = data.get(rule.field)
                if value is None:
                    continue

                threshold_type = _determine_threshold_type(float(value), rule)
                if threshold_type is None:
                    continue

                # Deduplication: skip if same site+field already has an active alert in last 30 min
                existing = await db.execute(
                    select(Alert).where(
                        Alert.site_id == site_id,
                        Alert.field == rule.field,
                        Alert.status == "active",
                        Alert.triggered_at >= dedup_cutoff,
                    )
                )
                if existing.scalar_one_or_none():
                    continue

                alert = Alert(
                    site_id=site_id,
                    device_uid=device_uid,
                    field=rule.field,
                    value=float(value),
                    threshold_type=threshold_type,
                    status="active",
                    triggered_at=now,
                )
                db.add(alert)
                new_alerts.append(rule.field)

            if new_alerts:
                await db.commit()
                # Fire-and-forget email (import here to avoid circular imports)
                from app.utils.email import send_alert_emails
                asyncio.create_task(send_alert_emails(site_id, site_uid, data))

    except Exception:
        logger.exception(f"Alert engine failed for site {site_uid}")


async def check_offline_devices(db: AsyncSession) -> None:
    """Create offline-device alerts for sites that have not sent data in >60 minutes."""
    try:
        from sqlalchemy import text
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=60)
        dedup_cutoff = datetime.now(timezone.utc) - timedelta(minutes=60)

        # Find sites with last data older than cutoff
        result = await db.execute(
            text("""
                SELECT s.id, s.uid
                FROM sites s
                WHERE s.is_active = 1
                  AND (
                    SELECT MAX(sd.ts) FROM sensor_data sd WHERE sd.site_id = s.id
                  ) < :cutoff
                  AND NOT EXISTS (
                    SELECT 1 FROM alerts a
                    WHERE a.site_id = s.id
                      AND a.field = 'device_offline'
                      AND a.status = 'active'
                      AND a.triggered_at >= :dedup_cutoff
                  )
            """),
            {"cutoff": cutoff, "dedup_cutoff": dedup_cutoff},
        )
        rows = result.fetchall()

        now = datetime.now(timezone.utc)
        for row in rows:
            alert = Alert(
                site_id=row.id,
                device_uid=None,
                field="device_offline",
                value=0.0,
                threshold_type="danger",
                status="active",
                triggered_at=now,
            )
            db.add(alert)

        if rows:
            await db.commit()
            logger.warning(f"Offline device alerts created for {len(rows)} sites")

    except Exception:
        logger.exception("Offline device check failed")
```

- [ ] **Step 4: Run tests — should pass now**

```bash
cd sparing_api
python -m pytest app/tests/test_alert_engine.py -v
```

Expected output:
```
PASSED app/tests/test_alert_engine.py::test_is_violated_upper_limit
PASSED app/tests/test_alert_engine.py::test_is_violated_range
PASSED app/tests/test_alert_engine.py::test_determine_threshold_type_danger
PASSED app/tests/test_alert_engine.py::test_determine_threshold_type_warning
PASSED app/tests/test_alert_engine.py::test_determine_threshold_type_normal
5 passed
```

- [ ] **Step 5: Commit**

```bash
git add sparing_api/app/utils/alert_engine.py sparing_api/app/tests/test_alert_engine.py
git commit -m "feat: add alert engine with threshold checking and offline device detection"
```

---

## Task 6: Email utility

**Files:**
- Create: `sparing_api/app/utils/email.py`

- [ ] **Step 1: Create email.py**

Create `sparing_api/app/utils/email.py`:
```python
import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.config import settings
from app.core.logging import logger
from app.models.models import User, ViewerSite, Site

FIELD_LABELS = {
    "ph": "pH", "tss": "TSS (mg/L)", "cod": "COD (mg/L)",
    "nh3n": "NH3-N (mg/L)", "temp": "Temperatur (°C)",
    "noise": "Kebisingan (dB)", "pm25": "PM2.5 (µg/m³)",
    "pm10": "PM10 (µg/m³)", "device_offline": "Perangkat Offline",
}


async def _get_recipient_emails(site_id: int, db: AsyncSession) -> list[str]:
    """Return emails of all admin users + viewers assigned to this site."""
    # Admins
    admin_result = await db.execute(
        select(User.email).where(User.role == "admin", User.is_active == True)
    )
    emails = list(admin_result.scalars().all())

    # Viewers assigned to site
    viewer_result = await db.execute(
        select(User.email)
        .join(ViewerSite, ViewerSite.user_id == User.id)
        .where(ViewerSite.site_id == site_id, User.is_active == True)
    )
    emails += list(viewer_result.scalars().all())
    return list(set(emails))


async def send_alert_emails(
    site_id: int,
    site_uid: str,
    data: dict,
) -> None:
    """Send email notifications for newly triggered alerts. Silently skips if SMTP not configured.
    Creates its own DB session — safe to call via asyncio.create_task().
    """
    if not settings.smtp_host:
        return

    from app.core.db import SessionLocal
    try:
        async with SessionLocal() as db:
            site_result = await db.execute(select(Site).where(Site.id == site_id))
            site = site_result.scalar_one_or_none()
            if not site:
                return

            recipients = await _get_recipient_emails(site_id, db)
        if not recipients:
            return

        # Build a summary of violated fields from the data dict
        violated_fields = []
        for field, label in FIELD_LABELS.items():
            if field == "device_offline":
                continue
            value = data.get(field)
            if value is not None:
                violated_fields.append(f"{label}: {value}")

        if not violated_fields:
            return

        body = f"""
Peringatan Baku Mutu — {site.name} ({site.company_name})

Parameter berikut melebihi batas baku mutu:
{chr(10).join(f'  • {v}' for v in violated_fields)}

Lokasi  : {site.name}
UID     : {site_uid}
Waktu   : {data.get('ts', 'N/A')}

Silakan buka dashboard SPARING untuk detail lebih lanjut.
"""

        msg = MIMEMultipart()
        msg["Subject"] = f"[SPARING] Peringatan Baku Mutu — {site.name}"
        msg["From"] = settings.smtp_from
        msg["To"] = ", ".join(recipients)
        msg.attach(MIMEText(body, "plain", "utf-8"))

            await aiosmtplib.send(
                msg,
                hostname=settings.smtp_host,
                port=settings.smtp_port,
                username=settings.smtp_user or None,
                password=settings.smtp_pass or None,
                use_tls=False,
                start_tls=settings.smtp_tls,
            )
            logger.info(f"Alert email sent for site {site_uid} to {len(recipients)} recipients")

    except Exception:
        logger.exception(f"Failed to send alert email for site {site_uid}")
```

- [ ] **Step 2: Verify import**

```bash
cd sparing_api
python -c "from app.utils.email import send_alert_emails; print('OK')"
```

Expected output: `OK`

- [ ] **Step 3: Commit**

```bash
git add sparing_api/app/utils/email.py
git commit -m "feat: add async email utility for alert notifications"
```

---

## Task 7: Alert rules router

**Files:**
- Create: `sparing_api/app/api/routers/alert_rules.py`

- [ ] **Step 1: Create alert_rules.py**

Create `sparing_api/app/api/routers/alert_rules.py`:
```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from datetime import datetime, timezone

from app.core.db import get_db
from app.api.deps import require_roles, get_current_user
from app.models.models import AlertRule, Site
from app.schemas.alert import AlertRuleCreate, AlertRuleUpdate, AlertRuleOut

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
```

- [ ] **Step 2: Verify import**

```bash
cd sparing_api
python -c "from app.api.routers.alert_rules import router; print('OK')"
```

Expected output: `OK`

- [ ] **Step 3: Commit**

```bash
git add sparing_api/app/api/routers/alert_rules.py
git commit -m "feat: add alert_rules CRUD router"
```

---

## Task 8: Alerts router

**Files:**
- Create: `sparing_api/app/api/routers/alerts.py`

- [ ] **Step 1: Create alerts.py**

Create `sparing_api/app/api/routers/alerts.py`:
```python
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime, timezone

from app.core.db import get_db
from app.api.deps import get_current_user, get_viewer_site_uids
from app.models.models import Alert, Site, User
from app.schemas.alert import AlertOut, AlertCountOut

router = APIRouter()


async def _build_alert_out(alert: Alert, db: AsyncSession) -> AlertOut:
    site_result = await db.execute(select(Site).where(Site.id == alert.site_id))
    site = site_result.scalar_one_or_none()
    return AlertOut(
        id=alert.id,
        site_id=alert.site_id,
        site_uid=site.uid if site else "",
        site_name=site.name if site else "",
        device_uid=alert.device_uid,
        field=alert.field,
        value=alert.value,
        threshold_type=alert.threshold_type,
        status=alert.status,
        triggered_at=alert.triggered_at,
        acknowledged_at=alert.acknowledged_at,
        acknowledged_by_user_id=alert.acknowledged_by_user_id,
    )


@router.get("/count", response_model=AlertCountOut)
async def get_alert_count(
    status: str = Query(default="active"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    viewer_uids: list[str] = Depends(get_viewer_site_uids),
):
    stmt = select(func.count(Alert.id)).where(Alert.status == status)
    if viewer_uids:
        site_ids_result = await db.execute(
            select(Site.id).where(Site.uid.in_(viewer_uids))
        )
        site_ids = list(site_ids_result.scalars().all())
        stmt = stmt.where(Alert.site_id.in_(site_ids))
    result = await db.execute(stmt)
    return AlertCountOut(count=result.scalar_one() or 0)


@router.get("", response_model=list[AlertOut])
async def list_alerts(
    status: str = Query(default="active"),
    site_uid: str | None = Query(default=None),
    limit: int = Query(default=20, le=100),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    viewer_uids: list[str] = Depends(get_viewer_site_uids),
):
    stmt = select(Alert).where(Alert.status == status)

    if site_uid:
        site_result = await db.execute(select(Site).where(Site.uid == site_uid))
        site = site_result.scalar_one_or_none()
        if site:
            stmt = stmt.where(Alert.site_id == site.id)
    elif viewer_uids:
        site_ids_result = await db.execute(
            select(Site.id).where(Site.uid.in_(viewer_uids))
        )
        site_ids = list(site_ids_result.scalars().all())
        stmt = stmt.where(Alert.site_id.in_(site_ids))

    stmt = stmt.order_by(Alert.triggered_at.desc()).limit(limit)
    result = await db.execute(stmt)
    alerts = result.scalars().all()

    return [await _build_alert_out(a, db) for a in alerts]


@router.patch("/{alert_id}/acknowledge")
async def acknowledge_alert(
    alert_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(select(Alert).where(Alert.id == alert_id))
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(404, "Alert not found")
    alert.status = "acknowledged"
    alert.acknowledged_at = datetime.now(timezone.utc)
    alert.acknowledged_by_user_id = user.id
    await db.commit()
    return {"ok": True}


@router.patch("/{alert_id}/resolve")
async def resolve_alert(
    alert_id: int,
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
):
    result = await db.execute(select(Alert).where(Alert.id == alert_id))
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(404, "Alert not found")
    alert.status = "resolved"
    await db.commit()
    return {"ok": True}
```

- [ ] **Step 2: Verify import**

```bash
cd sparing_api
python -c "from app.api.routers.alerts import router; print('OK')"
```

Expected output: `OK`

- [ ] **Step 3: Commit**

```bash
git add sparing_api/app/api/routers/alerts.py
git commit -m "feat: add alerts router with count, list, acknowledge, resolve"
```

---

## Task 9: Register routers and add offline device scheduler

**Files:**
- Modify: `sparing_api/app/main.py`

- [ ] **Step 1: Update imports in main.py**

In `sparing_api/app/main.py`, change line 8 from:
```python
from app.api.routers import auth, sites, devices, ingest, data, metrics, admin, getdata
```
to:
```python
from app.api.routers import auth, sites, devices, ingest, data, metrics, admin, getdata, alerts, alert_rules
```

- [ ] **Step 2: Register new routers**

After line `app.include_router(getdata.router, tags=["GetData"])`, add:
```python
app.include_router(alerts.router, prefix="/alerts", tags=["Alerts"])
app.include_router(alert_rules.router, prefix="/alert-rules", tags=["AlertRules"])
```

- [ ] **Step 3: Add offline device scheduler job**

In the `startup_event` function, after the `scheduler.add_job` for token cleanup, add:
```python
    async def _check_offline_devices():
        from app.core.db import get_db
        from app.utils.alert_engine import check_offline_devices
        try:
            async for db in get_db():
                await check_offline_devices(db)
                break
        except Exception:
            logger.exception("Offline device scheduler failed")

    scheduler.add_job(_check_offline_devices, "interval", minutes=5, id="offline_device_check")
```

- [ ] **Step 4: Verify server starts without error**

```bash
cd sparing_api
uvicorn app.main:app --reload --port 8000
```

Expected: server starts, visit `http://localhost:8000/docs` — should see `/alerts` and `/alert-rules` endpoints listed.

Stop server with Ctrl+C.

- [ ] **Step 5: Commit**

```bash
git add sparing_api/app/main.py
git commit -m "feat: register alerts/alert-rules routers and add offline device scheduler"
```

---

## Task 10: Integrate alert engine into ingest endpoints

**Files:**
- Modify: `sparing_api/app/api/routers/ingest.py`
- Modify: `sparing_api/app/api/routers/getdata.py`
- Modify: `sparing_api/app/api/routers/sites.py`

- [ ] **Step 1: Update ingest.py to call alert engine**

In `sparing_api/app/api/routers/ingest.py`, add import at top:
```python
import asyncio
from app.utils.alert_engine import trigger_alerts
```

In the `ingest_state` function, replace the line `check_thresholds(body.site_uid, body)` with:
```python
        asyncio.create_task(trigger_alerts(
            site_id=site.id,
            site_uid=body.site_uid,
            device_uid=str(body.device_id) if body.device_id else None,
            data=body.model_dump(),
        ))
```

- [ ] **Step 2: Update getdata.py to call alert engine**

In `sparing_api/app/api/routers/getdata.py`, add import at top:
```python
import asyncio
from app.utils.alert_engine import trigger_alerts
```

After the line `await db.commit()` that follows `await db.execute(insert(SensorData), rows)`, add:
```python
    # Trigger alerts for each row (use last row's data as representative sample)
    if rows:
        last_row = rows[-1]
        asyncio.create_task(trigger_alerts(
            site_id=site.id,
            site_uid=uid,
            device_uid=device_id_str,
            data=last_row,
        ))
```

- [ ] **Step 3: Seed default AlertRules on site creation**

In `sparing_api/app/api/routers/sites.py`, add import at top:
```python
from app.utils.alert_engine import seed_default_rules
```

In the `create_site` function, after `await db.refresh(s)`, add:
```python
    await seed_default_rules(s.id, db)
```

- [ ] **Step 4: Verify no import errors**

```bash
cd sparing_api
python -c "from app.api.routers.ingest import router; from app.api.routers.getdata import router; from app.api.routers.sites import router; print('OK')"
```

Expected output: `OK`

- [ ] **Step 5: Commit**

```bash
git add sparing_api/app/api/routers/ingest.py sparing_api/app/api/routers/getdata.py sparing_api/app/api/routers/sites.py
git commit -m "feat: trigger alerts after data ingest and seed rules on site creation"
```

---

## Task 11: Frontend — add alert API methods to useApi.js

**Files:**
- Modify: `sparing_front/resources/js/Composables/useApi.js`

- [ ] **Step 1: Add alert API methods**

In `sparing_front/resources/js/Composables/useApi.js`, add inside the `useApi()` function body (after the `updateUserSites` function, before the `return` statement):

```javascript
  // Alert rules endpoints
  const getAlertRules = (siteUid) => request('GET', '/alert-rules', null, { params: { site_uid: siteUid } });
  const createAlertRule = (siteUid, data) => request('POST', '/alert-rules', data, { params: { site_uid: siteUid } });
  const updateAlertRule = (ruleId, data) => request('PATCH', `/alert-rules/${ruleId}`, data);
  const deleteAlertRule = (ruleId) => request('DELETE', `/alert-rules/${ruleId}`);

  // Alerts endpoints
  const getAlerts = (params = {}) => request('GET', '/alerts', null, { params });
  const getAlertCount = (status = 'active') => request('GET', '/alerts/count', null, { params: { status } });
  const acknowledgeAlert = (alertId) => request('PATCH', `/alerts/${alertId}/acknowledge`);
  const resolveAlert = (alertId) => request('PATCH', `/alerts/${alertId}/resolve`);
```

Also add these to the `return` object at the bottom of `useApi()`:
```javascript
    // Alert Rules
    getAlertRules,
    createAlertRule,
    updateAlertRule,
    deleteAlertRule,
    // Alerts
    getAlerts,
    getAlertCount,
    acknowledgeAlert,
    resolveAlert,
```

- [ ] **Step 2: Commit**

```bash
git add sparing_front/resources/js/Composables/useApi.js
git commit -m "feat: add alert and alert-rules API methods to useApi composable"
```

---

## Task 12: Frontend — AlertDropdown component

**Files:**
- Create: `sparing_front/resources/js/Components/AlertDropdown.vue`

- [ ] **Step 1: Create AlertDropdown.vue**

Create `sparing_front/resources/js/Components/AlertDropdown.vue`:
```vue
<template>
  <div class="relative" ref="dropdownRef">
    <!-- Bell button -->
    <button
      @click="toggleDropdown"
      class="relative w-9 h-9 rounded-lg hover:bg-slate-100 flex items-center justify-center transition-colors"
      aria-label="Notifikasi"
    >
      <i class="fas fa-bell text-slate-500 text-sm"></i>
      <span
        v-if="activeCount > 0"
        class="absolute -top-0.5 -right-0.5 min-w-[18px] h-[18px] bg-red-500 text-white text-[10px] font-bold rounded-full flex items-center justify-center px-1 leading-none"
      >
        {{ activeCount > 99 ? '99+' : activeCount }}
      </span>
    </button>

    <!-- Dropdown panel -->
    <Transition name="dropdown">
      <div
        v-if="open"
        class="absolute right-0 top-full mt-2 w-80 bg-white rounded-xl shadow-lg border border-slate-100 z-50 overflow-hidden"
      >
        <!-- Header -->
        <div class="flex items-center justify-between px-4 py-3 border-b border-slate-100">
          <span class="text-sm font-bold text-slate-800">Notifikasi</span>
          <span v-if="activeCount > 0" class="text-xs font-mono text-red-500">{{ activeCount }} aktif</span>
        </div>

        <!-- Loading -->
        <div v-if="loading" class="px-4 py-6 text-center text-sm text-slate-400">
          <i class="fas fa-spinner fa-spin mr-2"></i>Memuat...
        </div>

        <!-- Empty -->
        <div v-else-if="!alerts.length" class="px-4 py-6 text-center text-sm text-slate-400">
          <i class="fas fa-check-circle text-emerald-400 text-2xl mb-2 block"></i>
          Tidak ada alert aktif
        </div>

        <!-- Alert list -->
        <div v-else class="divide-y divide-slate-50 max-h-80 overflow-y-auto">
          <div
            v-for="alert in alerts"
            :key="alert.id"
            class="px-4 py-3 hover:bg-slate-50 transition-colors"
            :class="alert.threshold_type === 'danger' ? 'border-l-2 border-red-500' : 'border-l-2 border-amber-400'"
          >
            <div class="flex items-start justify-between gap-2">
              <div class="flex-1 min-w-0">
                <div class="text-xs font-bold text-slate-700 truncate">{{ alert.site_name }}</div>
                <div class="text-sm font-semibold mt-0.5" :class="alert.threshold_type === 'danger' ? 'text-red-600' : 'text-amber-600'">
                  {{ getFieldLabel(alert.field) }}:
                  <span class="font-mono">{{ alert.field === 'device_offline' ? 'Offline' : formatAlertValue(alert) }}</span>
                </div>
                <div class="text-xs text-slate-400 mt-0.5 font-mono">{{ getRelativeTime(alert.triggered_at) }}</div>
              </div>
              <button
                @click.stop="handleAcknowledge(alert.id)"
                class="shrink-0 text-[10px] font-bold px-2 py-1 rounded border border-slate-200 text-slate-500 hover:bg-slate-100 transition-colors mt-0.5"
              >
                ACK
              </button>
            </div>
          </div>
        </div>

        <!-- Footer -->
        <div v-if="alerts.length" class="px-4 py-2.5 border-t border-slate-100 text-center">
          <span class="text-xs text-slate-400">Klik ACK untuk konfirmasi tiap alert</span>
        </div>
      </div>
    </Transition>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue';
import { useApi } from '@/Composables/useApi';
import { getRelativeTime, getSensorUnit } from '@/Utils/helpers';

const { getAlertCount, getAlerts, acknowledgeAlert } = useApi();

const open = ref(false);
const loading = ref(false);
const activeCount = ref(0);
const alerts = ref([]);
const dropdownRef = ref(null);

const FIELD_LABELS = {
  ph: 'pH', tss: 'TSS', cod: 'COD', nh3n: 'NH3-N', temp: 'Temperatur',
  noise: 'Kebisingan', pm25: 'PM2.5', pm10: 'PM10',
  device_offline: 'Perangkat Offline',
};

const getFieldLabel = (field) => FIELD_LABELS[field] || field.toUpperCase();

const formatAlertValue = (alert) => {
  const unit = getSensorUnit(alert.field);
  return `${Number(alert.value).toFixed(2)}${unit ? ' ' + unit : ''}`;
};

const fetchCount = async () => {
  try {
    const res = await getAlertCount('active');
    activeCount.value = res?.count ?? 0;
  } catch {
    // silent
  }
};

const fetchAlerts = async () => {
  loading.value = true;
  try {
    const res = await getAlerts({ status: 'active', limit: 20 });
    alerts.value = Array.isArray(res) ? res : [];
    activeCount.value = alerts.value.length;
  } catch {
    alerts.value = [];
  } finally {
    loading.value = false;
  }
};

const toggleDropdown = () => {
  open.value = !open.value;
  if (open.value) fetchAlerts();
};

const handleAcknowledge = async (alertId) => {
  try {
    await acknowledgeAlert(alertId);
    alerts.value = alerts.value.filter(a => a.id !== alertId);
    activeCount.value = Math.max(0, activeCount.value - 1);
  } catch {
    // silent
  }
};

const handleOutsideClick = (e) => {
  if (dropdownRef.value && !dropdownRef.value.contains(e.target)) {
    open.value = false;
  }
};

let pollInterval;

onMounted(() => {
  fetchCount();
  pollInterval = setInterval(fetchCount, 30000);
  document.addEventListener('click', handleOutsideClick);
});

onUnmounted(() => {
  clearInterval(pollInterval);
  document.removeEventListener('click', handleOutsideClick);
});
</script>

<style scoped>
.dropdown-enter-active { transition: all 0.15s ease-out; }
.dropdown-leave-active { transition: all 0.1s ease-in; }
.dropdown-enter-from   { opacity: 0; transform: translateY(-6px) scale(0.97); }
.dropdown-leave-to     { opacity: 0; transform: translateY(-4px) scale(0.97); }
</style>
```

- [ ] **Step 2: Commit**

```bash
git add sparing_front/resources/js/Components/AlertDropdown.vue
git commit -m "feat: add AlertDropdown component with bell icon, badge, and acknowledge"
```

---

## Task 13: Frontend — Update Header.vue

**Files:**
- Modify: `sparing_front/resources/js/Components/Header.vue`

- [ ] **Step 1: Import AlertDropdown in Header.vue**

In `sparing_front/resources/js/Components/Header.vue`, add to the script setup imports (after the existing imports):
```javascript
import AlertDropdown from '@/Components/AlertDropdown.vue';
```

- [ ] **Step 2: Add AlertDropdown to template**

In the template, find the `<!-- Right: Date + User avatar -->` section. Add `<AlertDropdown />` between the date div and the divider before the avatar, so it reads:

```html
      <!-- Right: Date + Alert Bell + User avatar -->
      <div class="flex items-center gap-3">

        <div class="hidden md:block text-right">
          <div class="text-xs text-slate-400">{{ currentDate }}</div>
        </div>

        <div class="h-5 w-px bg-slate-200 hidden md:block"></div>

        <!-- Alert Bell -->
        <AlertDropdown />

        <div class="h-5 w-px bg-slate-200"></div>

        <!-- Avatar + Dropdown -->
        <div class="relative" ref="dropdownRef">
```

- [ ] **Step 3: Add /alerts to pageTitles**

In the `pageTitles` object in `Header.vue`, add:
```javascript
  '/alerts': 'Notifikasi & Alert',
```

- [ ] **Step 4: Commit**

```bash
git add sparing_front/resources/js/Components/Header.vue
git commit -m "feat: add AlertDropdown bell icon to Header"
```

---

## Task 14: Frontend — Baku Mutu tab in Sites modal

**Files:**
- Modify: `sparing_front/resources/js/Pages/Sites/Index.vue`

- [ ] **Step 1: Add alert rule state and API methods**

In the `<script setup>` section of `Sites/Index.vue`, add after the existing destructuring:
```javascript
const { getSites, createSite, updateSite, deleteSite, getAlertRules, updateAlertRule, createAlertRule } = useApi();
```

Add new state variables (after `const editingSite = ref(null)`):
```javascript
const modalTab = ref('info'); // 'info' | 'baku-mutu'
const alertRules = ref([]);
const loadingRules = ref(false);
const newRule = ref({ field: '', warning_min: null, warning_max: null, danger_min: null, danger_max: null });
const showAddRule = ref(false);

const AVAILABLE_FIELDS = [
  { key: 'ph', label: 'pH' }, { key: 'tss', label: 'TSS' },
  { key: 'cod', label: 'COD' }, { key: 'nh3n', label: 'NH3-N' },
  { key: 'temp', label: 'Temperatur' }, { key: 'noise', label: 'Kebisingan' },
  { key: 'pm25', label: 'PM2.5' }, { key: 'pm10', label: 'PM10' },
];
```

Add a function to load alert rules (after `loadSites`):
```javascript
const loadAlertRules = async (siteUid) => {
  loadingRules.value = true;
  try {
    const res = await getAlertRules(siteUid);
    alertRules.value = Array.isArray(res) ? res : [];
  } catch {
    alertRules.value = [];
  } finally {
    loadingRules.value = false;
  }
};

const saveRule = async (rule) => {
  try {
    await updateAlertRule(rule.id, {
      warning_min: rule.warning_min,
      warning_max: rule.warning_max,
      danger_min: rule.danger_min,
      danger_max: rule.danger_max,
      is_active: rule.is_active,
    });
    toast.success('Aturan berhasil disimpan');
  } catch {
    toast.error('Gagal menyimpan aturan');
  }
};

const addRule = async () => {
  if (!editingSite.value || !newRule.value.field) return;
  try {
    await createAlertRule(editingSite.value.uid, newRule.value);
    await loadAlertRules(editingSite.value.uid);
    newRule.value = { field: '', warning_min: null, warning_max: null, danger_min: null, danger_max: null };
    showAddRule.value = false;
    toast.success('Aturan berhasil ditambahkan');
  } catch {
    toast.error('Gagal menambah aturan');
  }
};
```

Update `editSite` to also reset the tab and load rules:
```javascript
const editSite = (site) => {
  editingSite.value = site;
  siteForm.value = { ...site };
  modalTab.value = 'info';
  loadAlertRules(site.uid);
};
```

Update `closeModal` to reset tab:
```javascript
const closeModal = () => {
  showAddModal.value = false;
  editingSite.value = null;
  modalTab.value = 'info';
  showAddRule.value = false;
  siteForm.value = { uid: '', name: '', company_name: '', lat: 0, lon: 0, is_active: true };
};
```

- [ ] **Step 2: Update modal template to add tabs**

In the modal template, replace the modal header `<h3>` line:
```html
              <h3 class="font-bold text-slate-800">{{ editingSite ? 'Edit Lokasi' : 'Tambah Lokasi' }}</h3>
```
with:
```html
              <h3 class="font-bold text-slate-800">{{ editingSite ? 'Edit Lokasi' : 'Tambah Lokasi' }}</h3>
            </div>
            <button @click="closeModal" class="w-8 h-8 rounded-lg hover:bg-slate-100 flex items-center justify-center transition-colors">
              <i class="fas fa-times text-slate-400 text-sm"></i>
            </button>
          </div>

          <!-- Tabs (only shown when editing) -->
          <div v-if="editingSite" class="flex border-b border-slate-100 px-6">
            <button
              @click="modalTab = 'info'"
              class="px-4 py-2.5 text-sm font-semibold border-b-2 transition-colors"
              :class="modalTab === 'info' ? 'border-primary text-primary' : 'border-transparent text-slate-500 hover:text-slate-700'"
            >
              Info
            </button>
            <button
              v-if="isOperator"
              @click="modalTab = 'baku-mutu'"
              class="px-4 py-2.5 text-sm font-semibold border-b-2 transition-colors"
              :class="modalTab === 'baku-mutu' ? 'border-primary text-primary' : 'border-transparent text-slate-500 hover:text-slate-700'"
            >
              Baku Mutu
            </button>
          </div>

```

> **Note on modal structure:** The existing modal header is one `<div>` containing both the title area and the close button — both ending with `</div></div>`. The replacement above splits them so the tabs row sits *between* the header and the form. Replace lines 101–112 of `Sites/Index.vue` (the entire modal header `<div>`) with the block above, stopping before the `<form>` tag.

After the form closing `</form>`, add the Baku Mutu tab panel:
```html
          <!-- Baku Mutu Tab -->
          <div v-if="editingSite && modalTab === 'baku-mutu'" class="p-6">
            <div v-if="loadingRules" class="text-sm text-slate-400 text-center py-4">
              <i class="fas fa-spinner fa-spin mr-2"></i>Memuat aturan...
            </div>
            <div v-else>
              <!-- Rules table -->
              <div class="space-y-3 mb-4">
                <div v-if="!alertRules.length" class="text-sm text-slate-400 text-center py-4">
                  Belum ada aturan baku mutu. Klik "Tambah Aturan" untuk memulai.
                </div>
                <div
                  v-for="rule in alertRules"
                  :key="rule.id"
                  class="grid grid-cols-5 gap-2 items-center p-3 rounded-lg border border-slate-100 bg-slate-50 text-sm"
                >
                  <div class="font-semibold text-slate-700">{{ rule.field.toUpperCase() }}</div>
                  <input v-model.number="rule.warning_min" type="number" step="any" placeholder="Min peringatan"
                    class="form-input text-xs py-1.5" />
                  <input v-model.number="rule.warning_max" type="number" step="any" placeholder="Maks peringatan"
                    class="form-input text-xs py-1.5" />
                  <input v-model.number="rule.danger_max" type="number" step="any" placeholder="Maks bahaya"
                    class="form-input text-xs py-1.5" />
                  <button @click="saveRule(rule)" class="btn-primary text-xs py-1.5">Simpan</button>
                </div>
              </div>

              <!-- Add new rule -->
              <div v-if="showAddRule" class="p-3 rounded-lg border border-primary/20 bg-primary/5 mb-3">
                <div class="grid grid-cols-5 gap-2 items-center">
                  <select v-model="newRule.field" class="form-input text-xs py-1.5">
                    <option value="">Pilih Parameter</option>
                    <option v-for="f in AVAILABLE_FIELDS" :key="f.key" :value="f.key">{{ f.label }}</option>
                  </select>
                  <input v-model.number="newRule.warning_min" type="number" step="any" placeholder="Min peringatan" class="form-input text-xs py-1.5" />
                  <input v-model.number="newRule.warning_max" type="number" step="any" placeholder="Maks peringatan" class="form-input text-xs py-1.5" />
                  <input v-model.number="newRule.danger_max" type="number" step="any" placeholder="Maks bahaya" class="form-input text-xs py-1.5" />
                  <button @click="addRule" class="btn-primary text-xs py-1.5">Tambah</button>
                </div>
              </div>

              <button
                v-if="!showAddRule"
                @click="showAddRule = true"
                class="btn-secondary text-xs flex items-center gap-1.5"
              >
                <i class="fas fa-plus text-xs"></i>Tambah Aturan
              </button>
            </div>
          </div>
```

Wrap the existing `<form>` with `v-if="modalTab === 'info'"`:
```html
          <form v-if="!editingSite || modalTab === 'info'" @submit.prevent="saveSite" class="p-6 space-y-4">
```

- [ ] **Step 3: Commit**

```bash
git add sparing_front/resources/js/Pages/Sites/Index.vue
git commit -m "feat: add Baku Mutu tab to Sites edit modal with AlertRule CRUD"
```

---

## Post-Implementation Checklist

- [ ] Run backend: `cd sparing_api && uvicorn app.main:app --reload` — no startup errors
- [ ] Run frontend: `cd sparing_front && npm run dev` — no build errors
- [ ] Open Sites page, edit a site → "Baku Mutu" tab visible → rules loaded
- [ ] Send test data via `POST /api/post-data` with a pH value outside 6.0–9.0 → Alert created in DB
- [ ] Open app → bell icon shows red badge → dropdown lists the alert → click ACK → badge clears
- [ ] Set SMTP config in `.env` → trigger an alert → email received
- [ ] Check `/docs` → `/alerts` and `/alert-rules` endpoints visible and functional
