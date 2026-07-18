# UI v2 Upgrade — Backend Implementation Plan (Plan 1 of 2)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship the backend half of the UI v2 upgrade — alert follow-up workflow with mandatory closing note, `/stats` endpoints (compliance, daily heatmap, completeness), `/data` interval aggregation, and per-row `quality_flag` — all additive and deployable before any frontend change.

**Architecture:** Two additive Alembic migrations (0007, 0008). Alert lifecycle endpoints enforce the note rule; the alert-engine auto-resolve path writes a system note instead. New `stats.py` router computes windowed aggregates with portable SQL (COUNT/DATE only — runs on prod MySQL and the SQLite test harness). `/data` aggregation buckets in Python (dialect-portable, windows are small). Anomaly engine marks flagged rows during its existing per-burst scan.

**Tech Stack:** FastAPI, SQLAlchemy 2 async, Alembic, MySQL (prod) / aiosqlite (tests), pytest + the existing async harness (`app/tests/conftest.py`).

**Reference spec:** `docs/superpowers/specs/2026-07-18-ui-v2-upgrade-design.md` (Part 1)

**Spec deviation (documented):** stats endpoints are **not** TTL-cached in this plan. The cache is process-global while results are viewer-scoped — naive keys would leak admin-scoped numbers to viewers, and the global cache would also poison the test harness between tests. The windowed COUNT queries are cheap at 4 sites; add scoped caching later only if measurements demand it.

**Conventions:** backend commands run from `sparing_api/` with `.venv/Scripts/python.exe`; git commands from the repo root. Frontend is untouched by this plan.

---

## File Structure

- Modify: `app/models/models.py` (Alert +4 cols; SensorData +1 col)
- Create: `alembic/versions/0007_alert_followup.py`, `alembic/versions/0008_sensor_data_quality_flag.py`
- Modify: `app/schemas/alert.py` (AlertOut fields, `AlertActionIn`)
- Modify: `app/api/routers/alerts.py` (followup/resolve, filters+pagination)
- Modify: `app/utils/alert_engine.py` (auto-resolve system note)
- Create: `app/api/routers/stats.py`; Modify: `app/main.py` (register)
- Modify: `app/api/routers/data.py` (quality_flag passthrough, interval aggregation)
- Modify: `app/schemas/data.py` (DataOut.quality_flag)
- Modify: `app/utils/anomaly_engine.py` (mark quality_flag on hits)
- Tests: `app/tests/test_alerts_api.py` (create), `app/tests/test_stats_api.py` (create), `app/tests/test_data_api.py` (create)

---

### Task 0: Baseline — suite green

- [ ] **Step 1: Run the full test suite**

Run (from `sparing_api/`):
```bash
.venv/Scripts/python.exe -m pytest app/tests/ -q
```
Expected: `86 passed` (current baseline). If anything fails, stop and report — do not start on a red baseline.

---

### Task 1: Alert follow-up columns (model + migration 0007)

**Files:**
- Modify: `app/models/models.py` (class Alert)
- Create: `alembic/versions/0007_alert_followup.py`

- [ ] **Step 1: Add columns to the Alert model**

In `app/models/models.py`, inside `class Alert`, after the `detail` column line
(`detail: Mapped[str | None] = mapped_column(String(255), nullable=True)`), add:

```python
    followup_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    followup_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    followup_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
```

(`Text`, `ForeignKey`, `DateTime`, `datetime` are already imported at the top of models.py.)

- [ ] **Step 2: Create the migration**

Create `alembic/versions/0007_alert_followup.py`:

```python
from alembic import op
import sqlalchemy as sa

revision = '0007_alert_followup'
down_revision = '0006_add_anomaly_detection'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('alerts', sa.Column('followup_note', sa.Text(), nullable=True))
    op.add_column('alerts', sa.Column('followup_by_user_id', sa.Integer(), nullable=True))
    op.add_column('alerts', sa.Column('followup_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('alerts', sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True))
    op.create_foreign_key(
        'fk_alerts_followup_user', 'alerts', 'users',
        ['followup_by_user_id'], ['id'], ondelete='SET NULL',
    )


def downgrade():
    op.drop_constraint('fk_alerts_followup_user', 'alerts', type_='foreignkey')
    op.drop_column('alerts', 'resolved_at')
    op.drop_column('alerts', 'followup_at')
    op.drop_column('alerts', 'followup_by_user_id')
    op.drop_column('alerts', 'followup_note')
```

- [ ] **Step 3: Verify model import + migration syntax**

Run (from `sparing_api/`):
```bash
.venv/Scripts/python.exe -c "from app.models.models import Alert; print('ok', [c.name for c in Alert.__table__.columns if 'followup' in c.name or c.name=='resolved_at'])"
.venv/Scripts/python.exe -c "import ast; ast.parse(open('alembic/versions/0007_alert_followup.py').read()); print('migration ok')"
```
Expected: `ok ['followup_note', 'followup_by_user_id', 'followup_at', 'resolved_at']` then `migration ok`.

- [ ] **Step 4: Run the suite (models feed the test DB via create_all)**

Run: `.venv/Scripts/python.exe -m pytest app/tests/ -q` → Expected: `86 passed`.

- [ ] **Step 5: Commit**

```bash
git add sparing_api/app/models/models.py sparing_api/alembic/versions/0007_alert_followup.py
git commit -m "feat(alerts): follow-up columns on alerts (migration 0007)"
```

---

### Task 2: `quality_flag` column + passthrough in /data (model + migration 0008, TDD)

**Files:**
- Modify: `app/models/models.py` (class SensorData), `app/schemas/data.py`, `app/api/routers/data.py`
- Create: `alembic/versions/0008_sensor_data_quality_flag.py`
- Test: `app/tests/test_data_api.py` (create)

- [ ] **Step 1: Write the failing test**

Create `app/tests/test_data_api.py`:

```python
from datetime import datetime, timezone, timedelta

import pytest

from app.core.security import hash_password
from app.models.models import User, Site, SensorData


async def _auth_headers(client, db, email="op@example.com"):
    db.add(User(name="Op", email=email, password_hash=hash_password("Secret123"),
                role="operator", is_active=True))
    await db.commit()
    res = await client.post("/auth/login", json={"email": email, "password": "Secret123"})
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


async def _make_site(db, uid="TST-1"):
    site = Site(uid=uid, name="Test", company_name="C", is_active=True)
    db.add(site)
    await db.commit()
    await db.refresh(site)
    return site


def _row(site_id, ts, **vals):
    return SensorData(site_id=site_id, ts=ts,
                      created_at=datetime.now(timezone.utc), **vals)


@pytest.mark.anyio
async def test_data_returns_quality_flag(client, db_session):
    headers = await _auth_headers(client, db_session)
    site = await _make_site(db_session)
    t0 = datetime(2026, 7, 1, 10, 0, tzinfo=timezone.utc)
    db_session.add(_row(site.id, t0, ph=7.0))
    db_session.add(_row(site.id, t0 + timedelta(minutes=2), ph=13.5, quality_flag="anomaly"))
    await db_session.commit()

    res = await client.get("/data", params={"site_uid": "TST-1", "order": "asc"},
                           headers=headers)
    assert res.status_code == 200
    items = res.json()["items"]
    assert len(items) == 2
    assert items[0]["quality_flag"] is None
    assert items[1]["quality_flag"] == "anomaly"
```

- [ ] **Step 2: Run to verify it fails**

Run: `.venv/Scripts/python.exe -m pytest app/tests/test_data_api.py -q`
Expected: FAIL — `TypeError: 'quality_flag' is an invalid keyword argument for SensorData` (column doesn't exist yet).

- [ ] **Step 3: Implement**

(a) `app/models/models.py`, inside `class SensorData`, after the `current` column, add:
```python
    quality_flag: Mapped[str | None] = mapped_column(String(16), nullable=True)  # NULL = valid, 'anomaly' = flagged by anomaly engine
```

(b) `app/schemas/data.py`, in `class DataOut`, after `current`, add:
```python
    quality_flag: str | None = None
```

(c) `app/api/routers/data.py`:
- in `list_data`, add `quality_flag=r.quality_flag` to the `DataOut(...)` construction, and make the fields-filter always keep it — change the keep-tuple line to:
```python
            d = {k:v for k,v in d.items() if k in selected or k in ("id","ts","site_id","device_id","quality_flag")}
```
- in `last_record`, add `"quality_flag": row.quality_flag,` to the returned dict.

(d) Create `alembic/versions/0008_sensor_data_quality_flag.py`:
```python
from alembic import op
import sqlalchemy as sa

revision = '0008_sensor_data_quality_flag'
down_revision = '0007_alert_followup'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('sensor_data', sa.Column('quality_flag', sa.String(16), nullable=True))


def downgrade():
    op.drop_column('sensor_data', 'quality_flag')
```

- [ ] **Step 4: Run to verify it passes (plus full suite)**

Run: `.venv/Scripts/python.exe -m pytest app/tests/ -q` → Expected: `87 passed`.

- [ ] **Step 5: Commit**

```bash
git add sparing_api/app/models/models.py sparing_api/app/schemas/data.py sparing_api/app/api/routers/data.py sparing_api/alembic/versions/0008_sensor_data_quality_flag.py sparing_api/app/tests/test_data_api.py
git commit -m "feat(data): sensor_data.quality_flag column + API passthrough (migration 0008)"
```

---

### Task 3: Follow-up / resolve endpoints with mandatory note (TDD)

**Files:**
- Modify: `app/schemas/alert.py`, `app/api/routers/alerts.py`, `app/utils/alert_engine.py`
- Test: `app/tests/test_alerts_api.py` (create)

- [ ] **Step 1: Write the failing tests**

Create `app/tests/test_alerts_api.py`:

```python
from datetime import datetime, timezone

import pytest

from app.core.security import hash_password
from app.models.models import User, Site, Alert


async def _auth_headers(client, db, email="op@example.com"):
    db.add(User(name="Operator Satu", email=email,
                password_hash=hash_password("Secret123"), role="operator", is_active=True))
    await db.commit()
    res = await client.post("/auth/login", json={"email": email, "password": "Secret123"})
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


async def _make_alert(db, site_uid="TST-1", **overrides):
    site = Site(uid=site_uid, name="Test", company_name="C", is_active=True)
    db.add(site)
    await db.commit()
    await db.refresh(site)
    fields = dict(site_id=site.id, field="tss", value=250.0, threshold_type="danger",
                  status="active", triggered_at=datetime.now(timezone.utc),
                  category="compliance")
    fields.update(overrides)
    alert = Alert(**fields)
    db.add(alert)
    await db.commit()
    await db.refresh(alert)
    return alert


@pytest.mark.anyio
async def test_resolve_without_note_400(client, db_session):
    headers = await _auth_headers(client, db_session)
    alert = await _make_alert(db_session)
    res = await client.patch(f"/alerts/{alert.id}/resolve", json={}, headers=headers)
    assert res.status_code == 400
    res2 = await client.patch(f"/alerts/{alert.id}/resolve", json={"note": "   "}, headers=headers)
    assert res2.status_code == 400


@pytest.mark.anyio
async def test_resolve_with_note_stores_fields(client, db_session):
    headers = await _auth_headers(client, db_session)
    alert = await _make_alert(db_session)
    res = await client.patch(f"/alerts/{alert.id}/resolve",
                             json={"note": "Sensor dibersihkan, nilai normal"}, headers=headers)
    assert res.status_code == 200
    await db_session.refresh(alert)
    assert alert.status == "resolved"
    assert alert.followup_note == "Sensor dibersihkan, nilai normal"
    assert alert.resolved_at is not None
    assert alert.followup_by_user_id is not None


@pytest.mark.anyio
async def test_followup_sets_acknowledged_note_optional(client, db_session):
    headers = await _auth_headers(client, db_session)
    alert = await _make_alert(db_session)
    res = await client.patch(f"/alerts/{alert.id}/followup", json={}, headers=headers)
    assert res.status_code == 200
    await db_session.refresh(alert)
    assert alert.status == "acknowledged"
    assert alert.followup_at is not None
    assert alert.followup_by_user_id is not None
    # then resolving still demands a note
    res2 = await client.patch(f"/alerts/{alert.id}/resolve", json={}, headers=headers)
    assert res2.status_code == 400


@pytest.mark.anyio
async def test_alert_out_includes_followup_fields(client, db_session):
    headers = await _auth_headers(client, db_session)
    alert = await _make_alert(db_session)
    await client.patch(f"/alerts/{alert.id}/followup",
                       json={"note": "Cek panel listrik"}, headers=headers)
    res = await client.get("/alerts", params={"status": "acknowledged"}, headers=headers)
    assert res.status_code == 200
    item = res.json()[0]
    assert item["followup_note"] == "Cek panel listrik"
    assert item["followup_by_name"] == "Operator Satu"
    assert item["followup_at"] is not None
```

- [ ] **Step 2: Run to verify they fail**

Run: `.venv/Scripts/python.exe -m pytest app/tests/test_alerts_api.py -q`
Expected: FAIL (404 on /followup; resolve returns 200 without note; missing fields).

- [ ] **Step 3: Implement**

(a) `app/schemas/alert.py` — add after `AlertCountOut`:
```python
class AlertActionIn(BaseModel):
    note: str | None = None
```
and extend `AlertOut` after `detail`:
```python
    followup_note: str | None = None
    followup_by_name: str | None = None
    followup_at: datetime | None = None
    resolved_at: datetime | None = None
```

(b) `app/api/routers/alerts.py`:
- import: add `AlertActionIn` to the schema import, and `User` is already imported.
- in `_build_alert_out`, before the return, add:
```python
    followup_by_name = None
    if alert.followup_by_user_id:
        ures = await db.execute(select(User).where(User.id == alert.followup_by_user_id))
        u = ures.scalar_one_or_none()
        followup_by_name = u.name if u else None
```
and add to the `AlertOut(...)` call:
```python
        followup_note=alert.followup_note,
        followup_by_name=followup_by_name,
        followup_at=alert.followup_at,
        resolved_at=alert.resolved_at,
```
- replace the existing `resolve_alert` endpoint with:
```python
@router.patch("/{alert_id}/resolve")
async def resolve_alert(
    alert_id: int,
    body: AlertActionIn | None = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Close an alert. A follow-up note is mandatory (SOP: no closure without a record)."""
    note = ((body.note if body else None) or "").strip()
    if not note:
        raise HTTPException(400, "Catatan tindak lanjut wajib diisi")
    result = await db.execute(select(Alert).where(Alert.id == alert_id))
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(404, "Alert not found")
    now = datetime.now(timezone.utc)
    alert.status = "resolved"
    alert.resolved_at = now
    alert.followup_note = note
    alert.followup_by_user_id = user.id
    if alert.followup_at is None:
        alert.followup_at = now
    await db.commit()
    return {"ok": True}
```
- add a new endpoint after it:
```python
@router.patch("/{alert_id}/followup")
async def followup_alert(
    alert_id: int,
    body: AlertActionIn | None = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Mark an alert as being worked on (Dalam tindak lanjut). Note optional at this stage."""
    result = await db.execute(select(Alert).where(Alert.id == alert_id))
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(404, "Alert not found")
    now = datetime.now(timezone.utc)
    alert.status = "acknowledged"
    alert.acknowledged_at = now
    alert.followup_at = now
    alert.followup_by_user_id = user.id
    if body and body.note and body.note.strip():
        alert.followup_note = body.note.strip()
    await db.commit()
    return {"ok": True}
```

(c) `app/utils/alert_engine.py` — auto-resolve keeps working without a note. Add a module constant under the imports:
```python
AUTO_RESOLVE_NOTE = "Pulih otomatis — nilai kembali normal"
```
and in the recovery block of `trigger_alerts`, change `.values(status="resolved")` to:
```python
                        ).values(
                            status="resolved",
                            resolved_at=now,
                            followup_note=func.coalesce(Alert.followup_note, AUTO_RESOLVE_NOTE),
                        )
```
(`func` needs importing there: change `from sqlalchemy import select, update` to `from sqlalchemy import select, update, func`.) `coalesce` preserves an operator's in-progress note instead of overwriting it.

- [ ] **Step 4: Run to verify green (full suite)**

Run: `.venv/Scripts/python.exe -m pytest app/tests/ -q` → Expected: `91 passed`.

- [ ] **Step 5: Commit**

```bash
git add sparing_api/app/schemas/alert.py sparing_api/app/api/routers/alerts.py sparing_api/app/utils/alert_engine.py sparing_api/app/tests/test_alerts_api.py
git commit -m "feat(alerts): follow-up workflow with mandatory closing note"
```

---

### Task 4: `/alerts` filters + optional pagination wrapper (TDD)

**Files:**
- Modify: `app/api/routers/alerts.py`
- Test: `app/tests/test_alerts_api.py` (append)

- [ ] **Step 1: Write the failing tests** — append to `app/tests/test_alerts_api.py`:

```python
@pytest.mark.anyio
async def test_alerts_bare_list_without_page_param(client, db_session):
    headers = await _auth_headers(client, db_session)
    await _make_alert(db_session)
    res = await client.get("/alerts", headers=headers)
    assert res.status_code == 200
    assert isinstance(res.json(), list)  # AlertDropdown compatibility


@pytest.mark.anyio
async def test_alerts_paginated_wrapper_with_page_param(client, db_session):
    headers = await _auth_headers(client, db_session)
    site = None
    for i in range(3):
        alert = await _make_alert(db_session, site_uid=f"TST-{i}")
    res = await client.get("/alerts", params={"page": 1, "per_page": 2}, headers=headers)
    assert res.status_code == 200
    body = res.json()
    assert body["total"] == 3
    assert body["page"] == 1
    assert len(body["items"]) == 2


@pytest.mark.anyio
async def test_alerts_filters(client, db_session):
    headers = await _auth_headers(client, db_session)
    await _make_alert(db_session, site_uid="TST-A")  # compliance/danger
    await _make_alert(db_session, site_uid="TST-B",
                      category="data_quality", anomaly_type="flatline",
                      threshold_type="warning")
    r1 = await client.get("/alerts", params={"category": "data_quality"}, headers=headers)
    assert len(r1.json()) == 1 and r1.json()[0]["category"] == "data_quality"
    r2 = await client.get("/alerts", params={"threshold_type": "danger"}, headers=headers)
    assert len(r2.json()) == 1 and r2.json()[0]["threshold_type"] == "danger"
    r3 = await client.get("/alerts", params={"status": "all"}, headers=headers)
    assert len(r3.json()) == 2
```

- [ ] **Step 2: Run to verify they fail**

Run: `.venv/Scripts/python.exe -m pytest app/tests/test_alerts_api.py -q`
Expected: FAIL (unknown params ignored → wrong counts; page returns list not wrapper).

- [ ] **Step 3: Implement** — replace `list_alerts` in `app/api/routers/alerts.py` with:

```python
@router.get("")
async def list_alerts(
    status: str = Query(default="active"),
    site_uid: str | None = Query(default=None),
    category: str | None = Query(default=None),
    threshold_type: str | None = Query(default=None),
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
    limit: int = Query(default=20, le=100),
    page: int | None = Query(default=None, ge=1),
    per_page: int = Query(default=20, le=100),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    viewer_uids: list[str] = Depends(get_viewer_site_uids),
):
    """Bare list (existing behavior) when `page` is absent; {items,total,page,per_page}
    wrapper when `page` is given (Alarm page). Filters are additive."""
    conds = []
    if status != "all":
        conds.append(Alert.status == status)
    if category:
        conds.append(Alert.category == category)
    if threshold_type:
        conds.append(Alert.threshold_type == threshold_type)
    if date_from:
        conds.append(Alert.triggered_at >= date_from)
    if date_to:
        conds.append(Alert.triggered_at < date_to)

    if user._role == "viewer":
        if not viewer_uids:
            return {"items": [], "total": 0, "page": page, "per_page": per_page} if page else []
        if site_uid and site_uid not in viewer_uids:
            raise HTTPException(403, "Forbidden")

    if site_uid:
        site_result = await db.execute(select(Site).where(Site.uid == site_uid))
        site = site_result.scalar_one_or_none()
        if site:
            conds.append(Alert.site_id == site.id)
    elif user._role == "viewer":
        site_ids_result = await db.execute(select(Site.id).where(Site.uid.in_(viewer_uids)))
        conds.append(Alert.site_id.in_(list(site_ids_result.scalars().all())))

    stmt = select(Alert).where(*conds).order_by(Alert.triggered_at.desc())

    if page is None:
        rows = (await db.execute(stmt.limit(limit))).scalars().all()
        return [await _build_alert_out(a, db) for a in rows]

    total = (await db.execute(select(func.count(Alert.id)).where(*conds))).scalar_one()
    rows = (await db.execute(stmt.offset((page - 1) * per_page).limit(per_page))).scalars().all()
    items = [await _build_alert_out(a, db) for a in rows]
    return {"items": items, "total": total, "page": page, "per_page": per_page}
```
Note: the old `response_model=list[AlertOut]` annotation on this route must be removed (the return shape is now a union); `func` is already imported in alerts.py.

- [ ] **Step 4: Run to verify green (full suite)**

Run: `.venv/Scripts/python.exe -m pytest app/tests/ -q` → Expected: `94 passed`.

- [ ] **Step 5: Commit**

```bash
git add sparing_api/app/api/routers/alerts.py sparing_api/app/tests/test_alerts_api.py
git commit -m "feat(alerts): filters + optional pagination wrapper on GET /alerts"
```

---

### Task 5: Stats router — completeness (TDD)

**Files:**
- Create: `app/api/routers/stats.py`
- Modify: `app/main.py`
- Test: `app/tests/test_stats_api.py` (create)

- [ ] **Step 1: Write the failing test** — create `app/tests/test_stats_api.py`:

```python
from datetime import datetime, timezone, timedelta

import pytest

from app.core.security import hash_password
from app.models.models import User, Site, SensorData, AlertRule


async def _auth_headers(client, db, email="op@example.com"):
    db.add(User(name="Op", email=email, password_hash=hash_password("Secret123"),
                role="operator", is_active=True))
    await db.commit()
    res = await client.post("/auth/login", json={"email": email, "password": "Secret123"})
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


async def _make_site(db, uid="TST-1"):
    site = Site(uid=uid, name="Test", company_name="C", is_active=True)
    db.add(site)
    await db.commit()
    await db.refresh(site)
    return site


def _row(site_id, ts, **vals):
    return SensorData(site_id=site_id, ts=ts,
                      created_at=datetime.now(timezone.utc), **vals)


@pytest.mark.anyio
async def test_completeness_counts_window(client, db_session):
    headers = await _auth_headers(client, db_session)
    site = await _make_site(db_session)
    now = datetime.now(timezone.utc)
    for i in range(45):  # 45 rows inside the last 24h
        db_session.add(_row(site.id, now - timedelta(minutes=5 * i), ph=7.0))
    db_session.add(_row(site.id, now - timedelta(hours=30), ph=7.0))  # outside window
    await db_session.commit()

    res = await client.get("/stats/completeness", params={"hours": 24}, headers=headers)
    assert res.status_code == 200
    body = res.json()
    assert body["actual"] == 45
    assert body["expected"] == 1 * 30 * 24  # sites * 30/hour * hours
    assert body["pct"] == round(45 * 100.0 / 720, 1)
```

- [ ] **Step 2: Run to verify it fails**

Run: `.venv/Scripts/python.exe -m pytest app/tests/test_stats_api.py -q`
Expected: FAIL — 404 (router doesn't exist).

- [ ] **Step 3: Implement**

Create `app/api/routers/stats.py`:

```python
"""Aggregate statistics for the v2 dashboard/analytics.

Intentionally uncached: results are viewer-scoped, and a process-global TTL
cache keyed naively would leak admin-scoped numbers to viewers (and poison the
test harness). The windowed COUNT/DATE queries are cheap at this fleet size.
"""
from datetime import datetime, timezone, timedelta, date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.api.deps import get_viewer_site_uids
from app.models.models import Site, SensorData, AlertRule

router = APIRouter()

READINGS_PER_SITE_PER_HOUR = 30  # devices deliver hourly bursts of ~30 readings


async def _scoped_sites(db: AsyncSession, viewer_uids: list[str]) -> list[Site]:
    q = select(Site).where(Site.is_active == True)
    if viewer_uids:
        q = q.where(Site.uid.in_(viewer_uids))
    return list((await db.execute(q)).scalars().all())


@router.get("/completeness")
async def completeness(
    hours: int = Query(default=24, ge=1, le=1080),
    db: AsyncSession = Depends(get_db),
    viewer_uids: list[str] = Depends(get_viewer_site_uids),
):
    now = datetime.now(timezone.utc)
    since = now - timedelta(hours=hours)
    sites = await _scoped_sites(db, viewer_uids)
    site_ids = [s.id for s in sites]
    actual = 0
    if site_ids:
        actual = (await db.execute(
            select(func.count(SensorData.id)).where(
                SensorData.site_id.in_(site_ids),
                SensorData.ts >= since,
            )
        )).scalar_one()
    expected = len(site_ids) * READINGS_PER_SITE_PER_HOUR * hours
    pct = 0.0 if expected == 0 else min(100.0, round(actual * 100.0 / expected, 1))
    return {"actual": actual, "expected": expected, "pct": pct, "hours": hours}
```

In `app/main.py`: add `stats` to the routers import line and register after reports:
```python
app.include_router(stats.router, prefix="/stats", tags=["Stats"])
```

- [ ] **Step 4: Run to verify green (full suite)**

Run: `.venv/Scripts/python.exe -m pytest app/tests/ -q` → Expected: `95 passed`.

- [ ] **Step 5: Commit**

```bash
git add sparing_api/app/api/routers/stats.py sparing_api/app/main.py sparing_api/app/tests/test_stats_api.py
git commit -m "feat(stats): /stats/completeness endpoint"
```

---

### Task 6: Stats — compliance percentage (TDD)

**Files:**
- Modify: `app/api/routers/stats.py`
- Test: `app/tests/test_stats_api.py` (append)

- [ ] **Step 1: Write the failing test** — append to `app/tests/test_stats_api.py`:

```python
@pytest.mark.anyio
async def test_compliance_math_with_anomaly_exclusion(client, db_session):
    headers = await _auth_headers(client, db_session)
    site = await _make_site(db_session)
    db_session.add(AlertRule(site_id=site.id, field="tss",
                             warning_min=None, warning_max=150.0,
                             danger_min=None, danger_max=200.0, is_active=True,
                             created_at=datetime.now(timezone.utc),
                             updated_at=datetime.now(timezone.utc)))
    now = datetime.now(timezone.utc)
    # window: 3 compliant + 1 violation + 1 flagged-anomaly violation (excluded)
    for v in (50.0, 60.0, 70.0):
        db_session.add(_row(site.id, now - timedelta(hours=1), tss=v))
    db_session.add(_row(site.id, now - timedelta(hours=2), tss=250.0))
    db_session.add(_row(site.id, now - timedelta(hours=3), tss=999.0, quality_flag="anomaly"))
    await db_session.commit()

    res = await client.get("/stats/compliance", params={"days": 30}, headers=headers)
    assert res.status_code == 200
    body = res.json()
    assert body["checked"] == 4          # anomaly row excluded
    assert body["violations"] == 1
    assert body["compliance_pct"] == 75.0
    assert body["prev_pct"] == 100.0     # empty previous window counts as fully compliant
    assert body["delta_pct"] == -25.0
```

- [ ] **Step 2: Run to verify it fails** — `pytest app/tests/test_stats_api.py -q` → FAIL (404).

- [ ] **Step 3: Implement** — append to `app/api/routers/stats.py`:

```python
async def _compliance_window(db: AsyncSession, rules, t_from: datetime, t_to: datetime):
    """(checks, violations) for every reading x its site's active danger rule.
    Readings flagged as anomalies are excluded (spec: excluded from computations,
    retained for audit)."""
    checks, violations = 0, 0
    for rule in rules:
        col = getattr(SensorData, rule.field, None)
        if col is None:
            continue
        base = (
            SensorData.site_id == rule.site_id,
            col.isnot(None),
            SensorData.quality_flag.is_(None),
            SensorData.ts >= t_from,
            SensorData.ts < t_to,
        )
        checks += (await db.execute(select(func.count(SensorData.id)).where(*base))).scalar_one()
        vio = []
        if rule.danger_min is not None:
            vio.append(col < rule.danger_min)
        if rule.danger_max is not None:
            vio.append(col > rule.danger_max)
        if vio:
            violations += (await db.execute(
                select(func.count(SensorData.id)).where(*base, or_(*vio))
            )).scalar_one()
    return checks, violations


def _pct(checks: int, violations: int) -> float:
    return 100.0 if checks == 0 else round(100.0 * (1 - violations / checks), 1)


@router.get("/compliance")
async def compliance(
    days: int = Query(default=30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    viewer_uids: list[str] = Depends(get_viewer_site_uids),
):
    now = datetime.now(timezone.utc)
    since = now - timedelta(days=days)
    prev_since = since - timedelta(days=days)
    sites = await _scoped_sites(db, viewer_uids)
    site_ids = [s.id for s in sites]
    rules = []
    if site_ids:
        rules = list((await db.execute(
            select(AlertRule).where(AlertRule.site_id.in_(site_ids), AlertRule.is_active == True)
        )).scalars().all())
    checks, violations = await _compliance_window(db, rules, since, now)
    prev_checks, prev_violations = await _compliance_window(db, rules, prev_since, since)
    cur, prev = _pct(checks, violations), _pct(prev_checks, prev_violations)
    return {
        "compliance_pct": cur, "prev_pct": prev, "delta_pct": round(cur - prev, 1),
        "checked": checks, "violations": violations, "days": days,
    }
```

- [ ] **Step 4: Run full suite** — Expected: `96 passed`.

- [ ] **Step 5: Commit**

```bash
git add sparing_api/app/api/routers/stats.py sparing_api/app/tests/test_stats_api.py
git commit -m "feat(stats): /stats/compliance with previous-window delta"
```

---

### Task 7: Stats — daily compliance heatmap (TDD)

**Files:**
- Modify: `app/api/routers/stats.py`
- Test: `app/tests/test_stats_api.py` (append)

- [ ] **Step 1: Write the failing test** — append:

```python
@pytest.mark.anyio
async def test_compliance_daily_statuses(client, db_session):
    headers = await _auth_headers(client, db_session)
    site = await _make_site(db_session)
    db_session.add(AlertRule(site_id=site.id, field="tss",
                             warning_min=None, warning_max=150.0,
                             danger_min=None, danger_max=200.0, is_active=True,
                             created_at=datetime.now(timezone.utc),
                             updated_at=datetime.now(timezone.utc)))
    # day 1: compliant; day 2: warning-band; day 3: danger violation; day 4: no data
    db_session.add(_row(site.id, datetime(2026, 7, 1, 10, 0, tzinfo=timezone.utc), tss=50.0))
    db_session.add(_row(site.id, datetime(2026, 7, 2, 10, 0, tzinfo=timezone.utc), tss=170.0))
    db_session.add(_row(site.id, datetime(2026, 7, 3, 10, 0, tzinfo=timezone.utc), tss=250.0))
    await db_session.commit()

    res = await client.get("/stats/compliance-daily", params={"month": "2026-07"}, headers=headers)
    assert res.status_code == 200
    days = {d["date"]: d["status"] for d in res.json()["days"]}
    assert days["2026-07-01"] == "ok"
    assert days["2026-07-02"] == "warning"
    assert days["2026-07-03"] == "violation"
    assert days["2026-07-04"] == "none"
    assert len(days) >= 28


@pytest.mark.anyio
async def test_compliance_daily_bad_month_400(client, db_session):
    headers = await _auth_headers(client, db_session)
    res = await client.get("/stats/compliance-daily", params={"month": "banana"}, headers=headers)
    assert res.status_code == 400
```

- [ ] **Step 2: Run to verify fails** — FAIL (404).

- [ ] **Step 3: Implement** — append to `stats.py`:

```python
@router.get("/compliance-daily")
async def compliance_daily(
    month: str = Query(..., description="YYYY-MM"),
    db: AsyncSession = Depends(get_db),
    viewer_uids: list[str] = Depends(get_viewer_site_uids),
):
    try:
        year, mon = int(month[:4]), int(month[5:7])
        start = datetime(year, mon, 1, tzinfo=timezone.utc)
    except (ValueError, IndexError):
        raise HTTPException(400, "month harus berformat YYYY-MM")
    end = datetime(year + 1, 1, 1, tzinfo=timezone.utc) if mon == 12 else \
          datetime(year, mon + 1, 1, tzinfo=timezone.utc)

    sites = await _scoped_sites(db, viewer_uids)
    site_ids = [s.id for s in sites]
    day_expr = func.date(SensorData.ts)

    def _norm(d) -> str:  # SQLite returns 'YYYY-MM-DD' strings, MySQL date objects
        return d if isinstance(d, str) else d.isoformat()

    data_days, danger_days, warning_days = set(), set(), set()
    if site_ids:
        rows = (await db.execute(
            select(day_expr).where(SensorData.site_id.in_(site_ids),
                                   SensorData.ts >= start, SensorData.ts < end)
            .group_by(day_expr)
        )).all()
        data_days = {_norm(r[0]) for r in rows}

        rules = list((await db.execute(
            select(AlertRule).where(AlertRule.site_id.in_(site_ids), AlertRule.is_active == True)
        )).scalars().all())
        for rule in rules:
            col = getattr(SensorData, rule.field, None)
            if col is None:
                continue
            base = (SensorData.site_id == rule.site_id, col.isnot(None),
                    SensorData.quality_flag.is_(None),
                    SensorData.ts >= start, SensorData.ts < end)
            for level, bucket in (("danger", danger_days), ("warning", warning_days)):
                conds = []
                mn, mx = getattr(rule, f"{level}_min"), getattr(rule, f"{level}_max")
                if mn is not None:
                    conds.append(col < mn)
                if mx is not None:
                    conds.append(col > mx)
                if conds:
                    hit = (await db.execute(
                        select(day_expr).where(*base, or_(*conds)).group_by(day_expr)
                    )).all()
                    bucket.update(_norm(r[0]) for r in hit)

    days = []
    d = start
    while d < end:
        key = d.date().isoformat()
        if key in danger_days:
            status = "violation"
        elif key in warning_days:
            status = "warning"
        elif key in data_days:
            status = "ok"
        else:
            status = "none"
        days.append({"date": key, "status": status})
        d += timedelta(days=1)
    return {"month": month, "days": days}
```

- [ ] **Step 4: Run full suite** — Expected: `98 passed`.

- [ ] **Step 5: Commit**

```bash
git add sparing_api/app/api/routers/stats.py sparing_api/app/tests/test_stats_api.py
git commit -m "feat(stats): /stats/compliance-daily heatmap statuses"
```

---

### Task 8: `/data` interval aggregation (TDD)

**Files:**
- Modify: `app/api/routers/data.py`
- Test: `app/tests/test_data_api.py` (append)

- [ ] **Step 1: Write the failing tests** — append to `app/tests/test_data_api.py`:

```python
@pytest.mark.anyio
async def test_hourly_aggregation_excludes_anomaly(client, db_session):
    headers = await _auth_headers(client, db_session)
    site = await _make_site(db_session, uid="TST-AGG")
    base = datetime(2026, 7, 1, 10, 0, tzinfo=timezone.utc)
    db_session.add(_row(site.id, base, tss=10.0))
    db_session.add(_row(site.id, base + timedelta(minutes=10), tss=20.0))
    db_session.add(_row(site.id, base + timedelta(minutes=20), tss=900.0, quality_flag="anomaly"))
    db_session.add(_row(site.id, base + timedelta(hours=1, minutes=5), tss=30.0))
    await db_session.commit()

    res = await client.get("/data", params={
        "site_uid": "TST-AGG", "interval": "hourly", "order": "asc",
        "date_from": "2026-07-01T00:00:00Z", "fields": "tss",
    }, headers=headers)
    assert res.status_code == 200
    body = res.json()
    assert body["total"] == 2                       # two hourly buckets
    assert body["items"][0]["tss"] == 15.0          # (10+20)/2, anomaly excluded
    assert body["items"][0]["count"] == 2
    assert body["items"][1]["tss"] == 30.0


@pytest.mark.anyio
async def test_daily_aggregation_single_bucket(client, db_session):
    headers = await _auth_headers(client, db_session)
    site = await _make_site(db_session, uid="TST-DAY")
    base = datetime(2026, 7, 1, 8, 0, tzinfo=timezone.utc)
    for i, v in enumerate((6.0, 7.0, 8.0)):
        db_session.add(_row(site.id, base + timedelta(hours=i), ph=v))
    await db_session.commit()

    res = await client.get("/data", params={
        "site_uid": "TST-DAY", "interval": "daily", "order": "asc",
        "date_from": "2026-07-01T00:00:00Z", "fields": "ph",
    }, headers=headers)
    body = res.json()
    assert body["total"] == 1
    assert body["items"][0]["ph"] == 7.0
    assert body["items"][0]["count"] == 3


@pytest.mark.anyio
async def test_aggregation_requires_date_from(client, db_session):
    headers = await _auth_headers(client, db_session)
    await _make_site(db_session, uid="TST-G")
    res = await client.get("/data", params={"site_uid": "TST-G", "interval": "hourly"},
                           headers=headers)
    assert res.status_code == 400
```

- [ ] **Step 2: Run to verify they fail** — FAIL (interval ignored → raw shape/wrong totals).

- [ ] **Step 3: Implement** — in `app/api/routers/data.py`:

(a) Add `interval: str = "raw"` to the `list_data` signature (after `fields`).

(b) At the top of the function body, after the `per_page` guard, add:
```python
    if interval not in ("raw", "hourly", "daily"):
        raise HTTPException(400, "interval must be raw|hourly|daily")
    if interval != "raw" and date_from is None:
        raise HTTPException(400, "date_from wajib untuk interval agregasi")
```

(c) After the filter conditions are applied (right before `total = ...`), insert the aggregated branch:
```python
    NUMERIC_FIELDS = ("ph", "tss", "debit", "nh3n", "cod", "temp", "rh",
                      "wind_speed_kmh", "wind_deg", "noise", "co", "so2", "no2",
                      "o3", "pm25", "pm10", "tvoc", "voltage", "current")

    if interval != "raw":
        # Python-side bucketing: dialect-portable (MySQL prod / SQLite tests) and
        # windows are small (date_from is mandatory). Anomaly-flagged rows are
        # excluded from averages entirely (retained only in raw mode for audit).
        rows = (await db.execute(
            stmt.where(SensorData.quality_flag.is_(None)).order_by(SensorData.ts.asc())
        )).scalars().all()
        buckets: dict = {}
        for r in rows:
            ts = r.ts
            key = ts.replace(minute=0, second=0, microsecond=0) if interval == "hourly" \
                else ts.replace(hour=0, minute=0, second=0, microsecond=0)
            b = buckets.setdefault(key, {"count": 0, "sums": {}, "ns": {}})
            b["count"] += 1
            for f in NUMERIC_FIELDS:
                v = getattr(r, f)
                if v is not None:
                    b["sums"][f] = b["sums"].get(f, 0.0) + v
                    b["ns"][f] = b["ns"].get(f, 0) + 1
        keys = sorted(buckets.keys(), reverse=(order.lower() == "desc"))
        total = len(keys)
        page_keys = keys[(page - 1) * per_page: (page - 1) * per_page + per_page]
        items = []
        for k in page_keys:
            b = buckets[k]
            d = {"ts": k.isoformat(), "count": b["count"]}
            for f in NUMERIC_FIELDS:
                d[f] = round(b["sums"][f] / b["ns"][f], 3) if b["ns"].get(f) else None
            if selected := (set(x.strip() for x in fields.split(",") if x.strip()) if fields else None):
                d = {kk: vv for kk, vv in d.items() if kk in selected or kk in ("ts", "count")}
            items.append(d)
        return {"total": total, "page": page, "per_page": per_page, "items": items}
```

- [ ] **Step 4: Run full suite** — Expected: `101 passed`.

- [ ] **Step 5: Commit**

```bash
git add sparing_api/app/api/routers/data.py sparing_api/app/tests/test_data_api.py
git commit -m "feat(data): interval=hourly|daily aggregation excluding anomaly rows"
```

---

### Task 9: Anomaly engine marks `quality_flag` on hit rows

**Files:**
- Modify: `app/utils/anomaly_engine.py`

No harness test: `detect_realtime` opens its own `SessionLocal` (prod MySQL engine), same as the rest of the engine — verified by code review + the prod smoke in Task 10. The pure detectors stay fully tested.

- [ ] **Step 1: Implement**

(a) In `app/utils/anomaly_engine.py`, change the sqlalchemy import line to include `update`:
```python
from sqlalchemy import select, func, update
```

(b) In `detect_realtime`, extend the hits loop (currently `for ts, value, result in hits:` → `_maybe_create_alert(...)`) to also flag the row for single-reading anomaly types:
```python
                hits = scan_batch(samples, new_since, field)
                for ts, value, result in hits:
                    await _maybe_create_alert(db, site_id, device_uid, field, value, result, now)
                    if result.anomaly_type in ("implausible", "spike"):
                        # Flag the exact reading for the History "Validasi" column and
                        # aggregation exclusion. DB stores naive UTC — bind naive.
                        await db.execute(
                            update(SensorData).where(
                                SensorData.site_id == site_id,
                                SensorData.ts == (ts.replace(tzinfo=None) if ts.tzinfo else ts),
                            ).values(quality_flag="anomaly")
                        )
```
(Flatline/drift describe windows, not single readings — they do not flag rows.)

- [ ] **Step 2: Verify import + detectors still green**

```bash
.venv/Scripts/python.exe -c "import app.utils.anomaly_engine as a; print('ok')"
.venv/Scripts/python.exe -m pytest app/tests/test_anomaly_engine.py -q
```
Expected: `ok`, then `31 passed`.

- [ ] **Step 3: Commit**

```bash
git add sparing_api/app/utils/anomaly_engine.py
git commit -m "feat(anomaly): flag anomalous readings on sensor_data.quality_flag"
```

---

### Task 10: Full suite, deploy, production verification

- [ ] **Step 1: Full suite + app import**

```bash
.venv/Scripts/python.exe -m pytest app/tests/ -q
.venv/Scripts/python.exe -c "from app.main import app; print('routes:', len(app.routes))"
```
Expected: `101 passed`; route count grows by 5 (followup + 3 stats + unchanged others).

- [ ] **Step 2: Push and deploy backend**

```bash
git push origin main
ssh mitramutiara-prod "sudo bash /opt/sparing/repo/scripts/deploy.sh backend"
```
Expected: deploy script shows `import ok`, `Running upgrade 0006 -> 0007`, `0007 -> 0008`, restart, `healthy`.

- [ ] **Step 3: Production verification (read-only + one guard check)**

Obtain a token (use real operator credentials via env vars, never inline):
```bash
TOKEN=$(curl -s -X POST https://sparingapi.mitramutiara.co.id/auth/login \
  -H 'Content-Type: application/json' \
  -d "{\"email\":\"$SPARING_EMAIL\",\"password\":\"$SPARING_PASS\"}" | jq -r .access_token)

curl -s -H "Authorization: Bearer $TOKEN" 'https://sparingapi.mitramutiara.co.id/stats/completeness?hours=24'
curl -s -H "Authorization: Bearer $TOKEN" 'https://sparingapi.mitramutiara.co.id/stats/compliance?days=30'
curl -s -H "Authorization: Bearer $TOKEN" 'https://sparingapi.mitramutiara.co.id/stats/compliance-daily?month=2026-07' | head -c 300
# mandatory-note guard (expects 400):
curl -s -o /dev/null -w '%{http_code}\n' -X PATCH -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' -d '{}' \
  'https://sparingapi.mitramutiara.co.id/alerts/1/resolve'
# bare-list compat for the deployed AlertDropdown (expects JSON array):
curl -s -H "Authorization: Bearer $TOKEN" 'https://sparingapi.mitramutiara.co.id/alerts?status=active' | head -c 120
```
Expected: JSON numbers for stats; `400` for the empty-note resolve; `[` as the first character of the bare list.

---

## Self-Review Notes

- **Spec coverage (Part 1):** §1.1 → Tasks 1, 3, 4 (columns, endpoints, auto-resolve note, filters+pagination); §1.2 → Tasks 5–7 (all three stats endpoints, viewer-scoped, anomaly-excluded); §1.3 → Task 8 (interval + exclusion + bucket pagination + mandatory date_from guard); §1.4 → Tasks 2, 9 (column, API passthrough, engine marking). Cache deviation documented in the header and in stats.py's docstring.
- **Type consistency:** `AlertActionIn.note` optional in schema, enforced non-empty only in resolve; `AlertOut` new fields match model columns; `quality_flag` string `'anomaly'`/NULL used identically in engine, stats (`quality_flag.is_(None)`), and aggregation.
- **Compat:** `/alerts` bare-list preserved when `page` absent (Task 4 test asserts `isinstance(..., list)`); `/data` raw path untouched.
