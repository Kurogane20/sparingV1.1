# Logger Monitoring — Backend Implementation Plan (Plan 1 of 3)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship the server half of logger monitoring — heartbeat + event ingestion endpoints, per-site logger status, a dead-man's switch that raises a `logger` alarm within ~10 minutes of silence, sensor-failure alarms, and the `op_status` fix that preserves *why* parameters are absent during calibration/maintenance.

**Architecture:** Two additive Alembic migrations (0009, 0010). Device-facing endpoints reuse the **exact** JWT scheme `/api/post-data` already uses (body `{"token": <jwt>}`, payload inside the JWT, verified with `site.device_secret`) — extracted once into a shared helper so there is a single implementation. Web-facing endpoints are viewer-scoped and use the `{items,total,page,per_page}` pagination convention. Liveness is judged on server-recorded `received_at`/`last_heartbeat_at`, never on logger-reported clocks.

**Tech Stack:** FastAPI, SQLAlchemy 2 async, Alembic, MySQL (prod) / aiosqlite (tests), PyJWT, APScheduler, pytest + the existing async harness (`app/tests/conftest.py`).

**Reference spec:** `docs/superpowers/specs/2026-07-20-logger-monitoring-design.md` (Parts 2 and the §2.5 fix).

**Conventions:** backend commands run from `sparing_api/` with `.venv/Scripts/python.exe`; git from the repo root. Current Alembic head is `0008_sensor_data_quality_flag`. Frontend and the logger app are out of scope for this plan (Plans 2 and 3).

---

## File Structure

- Create: `app/utils/device_auth.py` — single shared device-JWT verifier
- Modify: `app/api/routers/getdata.py` — use the shared verifier; sentinel → `op_status`
- Modify: `app/models/models.py` — `LoggerStatus`, `LoggerEvent`, `SensorData.op_status`
- Create: `alembic/versions/0009_logger_monitoring.py`, `alembic/versions/0010_sensor_data_op_status.py`
- Create: `app/schemas/logger.py` — response models
- Create: `app/api/routers/logger.py` — the 4 endpoints
- Create: `app/utils/logger_monitor.py` — dead-man's switch + sensor-fail alarms
- Modify: `app/main.py` — register router + scheduler job
- Modify: `app/utils/anomaly_engine.py`, `app/api/routers/stats.py` — exclude `op_status` rows
- Tests: `app/tests/test_device_auth.py`, `app/tests/test_logger_api.py`, `app/tests/test_logger_monitor.py` (create); extend `app/tests/test_getdata_api.py`

---

### Task 0: Baseline — suite green

- [ ] **Step 1: Run the full suite**

Run (from `sparing_api/`):
```bash
.venv/Scripts/python.exe -m pytest app/tests/ -q
```
Expected: `104 passed`. If red, stop and report — do not build on a broken baseline.

---

### Task 1: Extract the device-JWT verifier (TDD)

Today the verification logic lives inline in `getdata.post_data`. The logger endpoints must use the identical scheme, so extract it once rather than copy it.

**Files:** Create `app/utils/device_auth.py`, `app/tests/test_device_auth.py`; modify `app/api/routers/getdata.py`

- [ ] **Step 1: Write the failing test**

Create `app/tests/test_device_auth.py`:

```python
import jwt
import pytest
from fastapi import HTTPException

from app.models.models import Site
from app.utils.device_auth import verify_device_token


async def _site(db, uid="DEV-1", secret="s3cret"):
    s = Site(uid=uid, name="T", company_name="C", is_active=True, device_secret=secret)
    db.add(s)
    await db.commit()
    await db.refresh(s)
    return s


@pytest.mark.anyio
async def test_valid_token_returns_site_and_payload(db_session):
    await _site(db_session)
    token = jwt.encode({"uid": "DEV-1", "hello": "world"}, "s3cret", algorithm="HS256")
    site, payload = await verify_device_token(token, db_session)
    assert site.uid == "DEV-1"
    assert payload["hello"] == "world"


@pytest.mark.anyio
async def test_wrong_secret_rejected(db_session):
    await _site(db_session)
    token = jwt.encode({"uid": "DEV-1"}, "WRONG", algorithm="HS256")
    with pytest.raises(HTTPException) as exc:
        await verify_device_token(token, db_session)
    assert exc.value.status_code == 400


@pytest.mark.anyio
async def test_unknown_uid_401(db_session):
    token = jwt.encode({"uid": "NOPE"}, "s3cret", algorithm="HS256")
    with pytest.raises(HTTPException) as exc:
        await verify_device_token(token, db_session)
    assert exc.value.status_code == 401


@pytest.mark.anyio
async def test_missing_token_400(db_session):
    with pytest.raises(HTTPException) as exc:
        await verify_device_token("", db_session)
    assert exc.value.status_code == 400
```

- [ ] **Step 2: Run to verify it fails**

Run: `.venv/Scripts/python.exe -m pytest app/tests/test_device_auth.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.utils.device_auth'`.

- [ ] **Step 3: Implement**

Create `app/utils/device_auth.py` — this mirrors `getdata.py` steps 1–3 exactly:

```python
"""Device-JWT verification shared by every device-facing endpoint.

The scheme (unchanged from /api/post-data): the request body carries
{"token": "<jwt>"}; the JWT payload holds the actual data and a `uid`; the
signature is verified with that site's device_secret (falling back to the
global getdata secret). Extracted here so heartbeat/event endpoints cannot
drift from the data endpoint's auth.
"""
import jwt
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.models import Site


def global_secret() -> str:
    return settings.getdata_secret


async def verify_device_token(token: str, db: AsyncSession) -> tuple[Site, dict]:
    """Return (site, decoded_payload) or raise HTTPException."""
    if not token:
        raise HTTPException(400, "Token is required")
    try:
        unverified = jwt.decode(
            token,
            options={"verify_signature": False, "verify_exp": False},
            algorithms=["HS256"],
        )
    except jwt.InvalidTokenError:
        raise HTTPException(400, "Invalid token format")

    uid = unverified.get("uid")
    if not uid:
        raise HTTPException(400, "Invalid data format")

    site = (await db.execute(select(Site).where(Site.uid == uid))).scalar_one_or_none()
    if not site:
        raise HTTPException(401, "Invalid UID")

    signing_secret = site.device_secret or global_secret()
    try:
        decoded = jwt.decode(token, signing_secret, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        raise HTTPException(400, "Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(400, "Invalid token format")
    return site, decoded
```

Then in `app/api/routers/getdata.py`, replace the inline Steps 1–3 (the block from
`# Step 1: Decode without verification…` through the `jwt.InvalidTokenError` handler
that produces `decode`) with:
```python
    site, decode = await verify_device_token(token, db)
```
Add `from app.utils.device_auth import verify_device_token` to the imports. Keep the
existing `_global_secret()` function and the `get_key` endpoint untouched (other code
may reference them).

- [ ] **Step 4: Run the full suite**

Run: `.venv/Scripts/python.exe -m pytest app/tests/ -q` → Expected: `108 passed`
(104 + 4 new). The existing `test_getdata_api.py` signature tests must still pass —
they are the regression guard that the extraction preserved behaviour.

- [ ] **Step 5: Commit**

```bash
git add sparing_api/app/utils/device_auth.py sparing_api/app/api/routers/getdata.py sparing_api/app/tests/test_device_auth.py
git commit -m "refactor(ingest): extract shared device-JWT verifier"
```

---

### Task 2: Logger tables (models + migration 0009)

**Files:** Modify `app/models/models.py`; create `alembic/versions/0009_logger_monitoring.py`

- [ ] **Step 1: Add the models**

Append to `app/models/models.py` (imports `Boolean`, `SmallInteger`, `Text`, `Float`,
`DateTime`, `ForeignKey`, `String`, `Integer` are already present — verify and add only
what is genuinely missing):

```python
class LoggerStatus(Base):
    """Latest heartbeat snapshot — exactly one row per site (upserted)."""
    __tablename__ = "logger_status"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id", ondelete="CASCADE"), unique=True, index=True)
    last_heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    logger_version: Mapped[str | None] = mapped_column(String(32), nullable=True)
    uptime_s: Mapped[int | None] = mapped_column(Integer, nullable=True)
    op_status: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    ph_ok: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    tss_ok: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    debit_ok: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    cod_ok: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    nh3n_ok: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    consec_fail: Mapped[int | None] = mapped_column(Integer, nullable=True)
    internet_ok: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    last_send_ok_mm: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    last_send_ok_klhk: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    buffer_depth: Mapped[int | None] = mapped_column(Integer, nullable=True)
    daily_sent: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cpu_temp: Mapped[float | None] = mapped_column(Float, nullable=True)
    cpu_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    mem_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    disk_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    state: Mapped[str] = mapped_column(String(16), default="alive", server_default="alive")
    state_since: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    site: Mapped["Site"] = relationship()


class LoggerEvent(Base):
    """Append-only log of logger state changes. `event_uid` is the idempotency key:
    the logger may re-upload unsynced events after a reconnect."""
    __tablename__ = "logger_events"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id", ondelete="CASCADE"), index=True)
    event_uid: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    type: Mapped[str] = mapped_column(String(32), index=True)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True))          # logger clock
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))  # server clock
    severity: Mapped[str] = mapped_column(String(16), default="info")
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    site: Mapped["Site"] = relationship()
```

- [ ] **Step 2: Create the migration**

Create `alembic/versions/0009_logger_monitoring.py`:

```python
from alembic import op
import sqlalchemy as sa

revision = '0009_logger_monitoring'
down_revision = '0008_sensor_data_quality_flag'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'logger_status',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('site_id', sa.Integer(), nullable=False),
        sa.Column('last_heartbeat_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('logger_version', sa.String(32), nullable=True),
        sa.Column('uptime_s', sa.Integer(), nullable=True),
        sa.Column('op_status', sa.SmallInteger(), nullable=True),
        sa.Column('ph_ok', sa.Boolean(), nullable=True),
        sa.Column('tss_ok', sa.Boolean(), nullable=True),
        sa.Column('debit_ok', sa.Boolean(), nullable=True),
        sa.Column('cod_ok', sa.Boolean(), nullable=True),
        sa.Column('nh3n_ok', sa.Boolean(), nullable=True),
        sa.Column('consec_fail', sa.Integer(), nullable=True),
        sa.Column('internet_ok', sa.Boolean(), nullable=True),
        sa.Column('last_send_ok_mm', sa.Boolean(), nullable=True),
        sa.Column('last_send_ok_klhk', sa.Boolean(), nullable=True),
        sa.Column('buffer_depth', sa.Integer(), nullable=True),
        sa.Column('daily_sent', sa.Integer(), nullable=True),
        sa.Column('cpu_temp', sa.Float(), nullable=True),
        sa.Column('cpu_pct', sa.Float(), nullable=True),
        sa.Column('mem_pct', sa.Float(), nullable=True),
        sa.Column('disk_pct', sa.Float(), nullable=True),
        sa.Column('state', sa.String(16), nullable=False, server_default='alive'),
        sa.Column('state_since', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['site_id'], ['sites.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('site_id', name='uq_logger_status_site'),
    )
    op.create_table(
        'logger_events',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('site_id', sa.Integer(), nullable=False),
        sa.Column('event_uid', sa.String(64), nullable=False),
        sa.Column('type', sa.String(32), nullable=False),
        sa.Column('ts', sa.DateTime(timezone=True), nullable=False),
        sa.Column('received_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('severity', sa.String(16), nullable=False, server_default='info'),
        sa.Column('detail', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['site_id'], ['sites.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('event_uid', name='uq_logger_event_uid'),
    )
    op.create_index('ix_logger_events_site_id', 'logger_events', ['site_id'])
    op.create_index('ix_logger_events_type', 'logger_events', ['type'])


def downgrade():
    op.drop_index('ix_logger_events_type', table_name='logger_events')
    op.drop_index('ix_logger_events_site_id', table_name='logger_events')
    op.drop_table('logger_events')
    op.drop_table('logger_status')
```

- [ ] **Step 3: Verify models import and the suite is still green**

```bash
.venv/Scripts/python.exe -c "from app.models.models import LoggerStatus, LoggerEvent; print('ok')"
.venv/Scripts/python.exe -m pytest app/tests/ -q
```
Expected: `ok`, then `108 passed` (the harness builds tables from the models).
Do NOT run `alembic upgrade` — no local MySQL; migrations run at deploy.

- [ ] **Step 4: Commit**

```bash
git add sparing_api/app/models/models.py sparing_api/alembic/versions/0009_logger_monitoring.py
git commit -m "feat(logger): logger_status + logger_events tables (migration 0009)"
```

---

### Task 3: `op_status` column + sentinel handling at ingest (TDD)

**Files:** Modify `app/models/models.py`, `app/schemas/data.py`, `app/api/routers/getdata.py`, `app/api/routers/data.py`; create `alembic/versions/0010_sensor_data_op_status.py`; extend `app/tests/test_getdata_api.py`

- [ ] **Step 1: Write the failing tests** — append to `app/tests/test_getdata_api.py`:

```python
@pytest.mark.anyio
async def test_calibration_sentinel_stored_as_op_status(client, db_session):
    """All water params carrying the same negative sentinel = an operational-status
    row, not readings: params NULL, op_status recorded (spec §2.5)."""
    site = await _make_site(db_session)
    token = _token(site, [{
        "datetime": 1753000000,
        "pH": -2, "tss": -2, "debit": -2, "cod": -2, "nh3n": -2,
    }])
    res = await client.post("/api/post-data", json={"token": token})
    assert res.status_code == 200
    row = (await db_session.execute(select(SensorData))).scalars().first()
    assert row.op_status == -2
    assert row.ph is None and row.tss is None and row.cod is None
    assert row.nh3n is None      # the one that used to slip through unbounded
    assert row.debit is None


@pytest.mark.anyio
async def test_partial_negative_is_not_a_sentinel_row(client, db_session):
    """Only some params negative => ordinary impossible-value handling, no op_status."""
    site = await _make_site(db_session, uid="TST-P")
    token = _token(site, [{
        "datetime": 1753000100,
        "pH": 7.1, "tss": 20.0, "debit": 5.0, "cod": 30.0, "nh3n": -2,
    }])
    res = await client.post("/api/post-data", json={"token": token})
    assert res.status_code == 200
    row = (await db_session.execute(select(SensorData))).scalars().first()
    assert row.op_status is None
    assert row.ph == 7.1
    assert row.nh3n is None      # dropped as impossible, not treated as sentinel
```
Adjust `_make_site`/`_token` usage to match the helpers already in that file (read them
first; `_token` must sign with the site's secret exactly as the existing tests do, and
`select`/`SensorData` may need importing).

- [ ] **Step 2: Run to verify they fail**

Run: `.venv/Scripts/python.exe -m pytest app/tests/test_getdata_api.py -q`
Expected: FAIL — `op_status` does not exist yet, and `nh3n` currently stores `-2`.

- [ ] **Step 3: Implement**

(a) `app/models/models.py`, in `class SensorData` after `quality_flag`:
```python
    op_status: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)  # -1 stopped, -2 calibration, -3 malfunction (KLHK Pasal 6.2.6.6g)
```

(b) `app/schemas/data.py`, in `DataOut` after `quality_flag`:
```python
    op_status: int | None = None
```

(c) `app/api/routers/getdata.py` — add a sentinel detector above `post_data`:
```python
WATER_PARAM_KEYS = (("pH", "ph"), ("tss", "TSS"), ("cod", "COD"),
                    ("debit", "Debit"), ("nh3n", "NH3N", "nh3N"))
OP_STATUS_SENTINELS = (-1, -2, -3)


def _sentinel_status(d: dict) -> int | None:
    """Return the operational-status code when EVERY present water parameter
    carries the same negative sentinel, else None. Partial negatives are not a
    status row — they fall through to _num()'s impossible-value handling."""
    seen = set()
    for keys in WATER_PARAM_KEYS:
        raw = next((d[k] for k in keys if d.get(k) is not None), None)
        if raw is None:
            continue
        try:
            v = float(raw)
        except (TypeError, ValueError):
            return None
        if v not in OP_STATUS_SENTINELS:
            return None
        seen.add(int(v))
    return seen.pop() if len(seen) == 1 else None
```
Then inside the per-row loop, before the `_num(...)` extractions, add:
```python
        op_status = _sentinel_status(d)
        if op_status is not None:
            ph = cod = tss = debit = nh3n = None
        else:
            ...existing _num(...) lines for ph/cod/tss/debit/nh3n...
```
Keep `voltage`/`current` extraction outside that branch — they are never
sentinel-coded and must still be stored. Pass `op_status=op_status` into the
`SensorData(...)`/insert values.

(d) `app/api/routers/data.py`: add `op_status=r.op_status` to the `DataOut(...)`
construction, add `"op_status"` to the fields-filter keep-tuple, and add
`"op_status": row.op_status,` to `last_record`'s dict.

(e) Create `alembic/versions/0010_sensor_data_op_status.py`:
```python
from alembic import op
import sqlalchemy as sa

revision = '0010_sensor_data_op_status'
down_revision = '0009_logger_monitoring'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('sensor_data', sa.Column('op_status', sa.SmallInteger(), nullable=True))


def downgrade():
    op.drop_column('sensor_data', 'op_status')
```

- [ ] **Step 4: Run the full suite**

Run: `.venv/Scripts/python.exe -m pytest app/tests/ -q` → Expected: `110 passed`.

- [ ] **Step 5: Commit**

```bash
git add sparing_api/app/models/models.py sparing_api/app/schemas/data.py sparing_api/app/api/routers/getdata.py sparing_api/app/api/routers/data.py sparing_api/alembic/versions/0010_sensor_data_op_status.py sparing_api/app/tests/test_getdata_api.py
git commit -m "feat(ingest): preserve KLHK operational status as op_status instead of discarding sentinels (migration 0010)"
```

---

### Task 4: Exclude `op_status` rows from anomaly + compliance (TDD)

Operational-status rows are not measurements; they must not be analysed.

**Files:** Modify `app/utils/anomaly_engine.py`, `app/api/routers/stats.py`, `app/api/routers/data.py`; extend `app/tests/test_stats_api.py`

- [ ] **Step 1: Write the failing test** — append to `app/tests/test_stats_api.py`:

```python
@pytest.mark.anyio
async def test_compliance_excludes_op_status_rows(client, db_session):
    headers = await _auth_headers(client, db_session)
    site = await _make_site(db_session)
    db_session.add(AlertRule(site_id=site.id, field="tss",
                             warning_min=None, warning_max=150.0,
                             danger_min=None, danger_max=200.0, is_active=True,
                             created_at=datetime.now(timezone.utc),
                             updated_at=datetime.now(timezone.utc)))
    now = datetime.now(timezone.utc)
    db_session.add(_row(site.id, now - timedelta(hours=1), tss=50.0))
    # a calibration row: params NULL, op_status set — must not be counted at all
    db_session.add(_row(site.id, now - timedelta(hours=2), tss=None, op_status=-2))
    await db_session.commit()

    res = await client.get("/stats/compliance", params={"days": 30}, headers=headers)
    body = res.json()
    assert body["checked"] == 1        # only the real reading
    assert body["compliance_pct"] == 100.0
```
(`_row` already forwards `**vals`, so `op_status=-2` works once the column exists.)

- [ ] **Step 2: Run to verify it fails**

Run: `.venv/Scripts/python.exe -m pytest app/tests/test_stats_api.py -q`
Expected: PASS-by-accident is possible here because `tss=None` is already excluded by
`col.isnot(None)`. **If it passes, still do Step 3** — add an explicit exclusion so the
intent is enforced rather than incidental, and extend the test with a row that has both
`op_status` and a non-null value:
```python
    db_session.add(_row(site.id, now - timedelta(hours=3), tss=999.0, op_status=-3))
```
which MUST also be excluded (`checked` stays 1). Re-run: that assertion fails before
the fix.

- [ ] **Step 3: Implement**

(a) `app/api/routers/stats.py` — in `_compliance_window`'s `base` tuple and in
`compliance_daily`'s `base` tuple, add:
```python
            SensorData.op_status.is_(None),
```
next to the existing `SensorData.quality_flag.is_(None)`.

(b) `app/api/routers/data.py` — in the aggregation branch, extend the filter:
```python
            stmt.where(SensorData.quality_flag.is_(None), SensorData.op_status.is_(None))
```

(c) `app/utils/anomaly_engine.py` — in `detect_realtime`'s history query and in
`detect_drift_all_sites`, add `SensorData.op_status.is_(None)` to the WHERE clauses so
calibration rows never enter a detector window.

- [ ] **Step 4: Run the full suite**

Run: `.venv/Scripts/python.exe -m pytest app/tests/ -q` → Expected: `111 passed`.

- [ ] **Step 5: Commit**

```bash
git add sparing_api/app/api/routers/stats.py sparing_api/app/api/routers/data.py sparing_api/app/utils/anomaly_engine.py sparing_api/app/tests/test_stats_api.py
git commit -m "feat(stats): exclude operational-status rows from compliance, aggregation and anomaly detection"
```

---

### Task 5: `POST /logger/heartbeat` (TDD)

**Files:** Create `app/schemas/logger.py`, `app/api/routers/logger.py`, `app/tests/test_logger_api.py`; modify `app/main.py`

- [ ] **Step 1: Write the failing tests**

Create `app/tests/test_logger_api.py`:

```python
from datetime import datetime, timezone, timedelta

import jwt
import pytest
from sqlalchemy import select

from app.core.security import hash_password
from app.models.models import User, Site, LoggerStatus, LoggerEvent


async def _site(db, uid="LOG-1", secret="s3cret"):
    s = Site(uid=uid, name="Test Site", company_name="C", is_active=True, device_secret=secret)
    db.add(s)
    await db.commit()
    await db.refresh(s)
    return s


def _hb_token(uid, status, secret="s3cret"):
    return jwt.encode({"uid": uid, "status": status}, secret, algorithm="HS256")


async def _auth_headers(client, db, email="op@example.com", role="operator"):
    db.add(User(name="Op", email=email, password_hash=hash_password("Secret123"),
                role=role, is_active=True))
    await db.commit()
    res = await client.post("/auth/login", json={"email": email, "password": "Secret123"})
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


STATUS = {
    "uptime_s": 3600, "logger_version": "1.4.0", "op_status": 0,
    "ph_ok": True, "tss_ok": False, "debit_ok": True, "cod_ok": None, "nh3n_ok": None,
    "consec_fail": 0, "internet_ok": True,
    "last_send_ok_mm": True, "last_send_ok_klhk": False,
    "buffer_depth": 12, "daily_sent": 640,
    "cpu_temp": 52.3, "cpu_pct": 18.0, "mem_pct": 41.2, "disk_pct": 63.5,
}


@pytest.mark.anyio
async def test_heartbeat_creates_then_updates_single_row(client, db_session):
    site = await _site(db_session)
    r1 = await client.post("/logger/heartbeat", json={"token": _hb_token("LOG-1", STATUS)})
    assert r1.status_code == 200
    r2 = await client.post("/logger/heartbeat", json={"token": _hb_token("LOG-1", {**STATUS, "buffer_depth": 3})})
    assert r2.status_code == 200

    rows = (await db_session.execute(select(LoggerStatus))).scalars().all()
    assert len(rows) == 1                     # upsert, not insert-per-beat
    st = rows[0]
    assert st.site_id == site.id
    assert st.state == "alive"
    assert st.buffer_depth == 3               # latest wins
    assert st.tss_ok is False
    assert st.logger_version == "1.4.0"
    assert st.last_heartbeat_at is not None


@pytest.mark.anyio
async def test_heartbeat_rejects_bad_signature(client, db_session):
    await _site(db_session)
    bad = _hb_token("LOG-1", STATUS, secret="WRONG")
    res = await client.post("/logger/heartbeat", json={"token": bad})
    assert res.status_code == 400


@pytest.mark.anyio
async def test_heartbeat_unknown_site_401(client, db_session):
    res = await client.post("/logger/heartbeat", json={"token": _hb_token("NOPE", STATUS)})
    assert res.status_code == 401
```

- [ ] **Step 2: Run to verify they fail** — Expected: 404 (router absent).

- [ ] **Step 3: Implement**

Create `app/schemas/logger.py`:
```python
from datetime import datetime
from pydantic import BaseModel


class LoggerStatusOut(BaseModel):
    site_id: int
    site_uid: str
    site_name: str
    state: str
    state_since: datetime | None = None
    last_heartbeat_at: datetime | None = None
    minutes_since_heartbeat: float | None = None
    logger_version: str | None = None
    uptime_s: int | None = None
    op_status: int | None = None
    ph_ok: bool | None = None
    tss_ok: bool | None = None
    debit_ok: bool | None = None
    cod_ok: bool | None = None
    nh3n_ok: bool | None = None
    consec_fail: int | None = None
    internet_ok: bool | None = None
    last_send_ok_mm: bool | None = None
    last_send_ok_klhk: bool | None = None
    buffer_depth: int | None = None
    daily_sent: int | None = None
    cpu_temp: float | None = None
    cpu_pct: float | None = None
    mem_pct: float | None = None
    disk_pct: float | None = None


class LoggerEventOut(BaseModel):
    id: int
    site_id: int
    site_uid: str
    site_name: str
    event_uid: str
    type: str
    ts: datetime
    received_at: datetime
    severity: str
    detail: str | None = None
```

Create `app/api/routers/logger.py`:
```python
"""Logger telemetry: device-facing ingest + web-facing read endpoints.

Liveness is always judged on the SERVER clock (last_heartbeat_at), never on the
logger-reported timestamp — a Pi with a skewed clock must not look alive or dead
incorrectly.
"""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.models.models import LoggerStatus, Site
from app.utils.device_auth import verify_device_token

router = APIRouter()

_STATUS_FIELDS = (
    "logger_version", "uptime_s", "op_status", "ph_ok", "tss_ok", "debit_ok",
    "cod_ok", "nh3n_ok", "consec_fail", "internet_ok", "last_send_ok_mm",
    "last_send_ok_klhk", "buffer_depth", "daily_sent", "cpu_temp", "cpu_pct",
    "mem_pct", "disk_pct",
)


@router.post("/heartbeat")
async def heartbeat(request: Request, db: AsyncSession = Depends(get_db)):
    body = await request.json()
    site, payload = await verify_device_token(body.get("token") or "", db)
    status = payload.get("status") or {}
    if not isinstance(status, dict):
        raise HTTPException(400, "Invalid data format")

    now = datetime.now(timezone.utc)
    st = (await db.execute(
        select(LoggerStatus).where(LoggerStatus.site_id == site.id).limit(1)
    )).scalars().first()
    if st is None:
        st = LoggerStatus(site_id=site.id, state="alive", state_since=now)
        db.add(st)
    was_down = st.state == "down"
    for f in _STATUS_FIELDS:
        if f in status:
            setattr(st, f, status[f])
    st.last_heartbeat_at = now
    if was_down:
        st.state = "alive"
        st.state_since = now
    await db.commit()

    if was_down:
        from app.utils.logger_monitor import resolve_logger_down_alert
        await resolve_logger_down_alert(db, site.id, now)
    return {"ok": True, "state": st.state}
```
(The `resolve_logger_down_alert` import is deferred until Task 7 creates it — write
the call now but implement the function in Task 7. To keep Task 5 green, create
`app/utils/logger_monitor.py` in this task containing only a stub:
```python
async def resolve_logger_down_alert(db, site_id: int, now) -> None:
    """Filled in by Task 7."""
    return None
```
)

In `app/main.py`: add `logger` to the routers import and register it:
```python
app.include_router(logger.router, prefix="/logger", tags=["Logger"])
```
Also add `"/logger"` to the ingest `RateLimitMiddleware` `routes_prefix` list so
device traffic is throttled like `/api` and `/ingest`.

- [ ] **Step 4: Run the full suite** → Expected: `114 passed`.

- [ ] **Step 5: Commit**

```bash
git add sparing_api/app/schemas/logger.py sparing_api/app/api/routers/logger.py sparing_api/app/utils/logger_monitor.py sparing_api/app/main.py sparing_api/app/tests/test_logger_api.py
git commit -m "feat(logger): POST /logger/heartbeat with per-site status upsert"
```

---

### Task 6: `POST /logger/events` — idempotent batch (TDD)

**Files:** Modify `app/api/routers/logger.py`; extend `app/tests/test_logger_api.py`

- [ ] **Step 1: Write the failing tests** — append:

```python
def _ev_token(uid, events, secret="s3cret"):
    return jwt.encode({"uid": uid, "events": events}, secret, algorithm="HS256")


@pytest.mark.anyio
async def test_events_batch_insert_and_idempotent_replay(client, db_session):
    await _site(db_session)
    events = [
        {"event_uid": "e-1", "type": "started", "ts": 1753000000,
         "severity": "info", "detail": "previous_shutdown_clean=false"},
        {"event_uid": "e-2", "type": "net_down", "ts": 1753000100, "severity": "warning"},
    ]
    r1 = await client.post("/logger/events", json={"token": _ev_token("LOG-1", events)})
    assert r1.status_code == 200
    assert r1.json()["accepted"] == 2

    # The logger re-uploads the same batch after a flaky connection: no duplicates.
    r2 = await client.post("/logger/events", json={"token": _ev_token("LOG-1", events)})
    assert r2.status_code == 200
    assert r2.json()["duplicates"] == 2

    rows = (await db_session.execute(select(LoggerEvent))).scalars().all()
    assert len(rows) == 2
    started = [r for r in rows if r.type == "started"][0]
    assert started.severity == "info"
    assert started.received_at is not None


@pytest.mark.anyio
async def test_events_rejects_oversized_batch(client, db_session):
    await _site(db_session)
    events = [{"event_uid": f"x-{i}", "type": "net_up", "ts": 1753000000} for i in range(201)]
    res = await client.post("/logger/events", json={"token": _ev_token("LOG-1", events)})
    assert res.status_code == 400
```

- [ ] **Step 2: Run to verify they fail** — Expected: 404.

- [ ] **Step 3: Implement** — append to `app/api/routers/logger.py`:

```python
MAX_EVENT_BATCH = 200
_KNOWN_EVENT_TYPES = {
    "started", "stopping", "stopped", "sensor_fail", "sensor_recover",
    "net_down", "net_up", "send_fail", "opstatus_change", "buffer_high",
}


@router.post("/events")
async def ingest_events(request: Request, db: AsyncSession = Depends(get_db)):
    """Batch-insert logger events. `event_uid` is the idempotency key so a logger
    that re-uploads after a reconnect can never create duplicates."""
    from app.models.models import LoggerEvent

    body = await request.json()
    site, payload = await verify_device_token(body.get("token") or "", db)
    events = payload.get("events")
    if not isinstance(events, list) or not events:
        raise HTTPException(400, "Invalid data format")
    if len(events) > MAX_EVENT_BATCH:
        raise HTTPException(400, f"Batch too large (max {MAX_EVENT_BATCH})")

    now = datetime.now(timezone.utc)
    uids = [e.get("event_uid") for e in events if e.get("event_uid")]
    existing = set((await db.execute(
        select(LoggerEvent.event_uid).where(LoggerEvent.event_uid.in_(uids))
    )).scalars().all()) if uids else set()

    accepted = 0
    duplicates = 0
    for e in events:
        uid = e.get("event_uid")
        etype = e.get("type")
        if not uid or not etype:
            continue
        if uid in existing:
            duplicates += 1
            continue
        try:
            ts = datetime.fromtimestamp(int(e.get("ts") or 0), tz=timezone.utc)
        except (TypeError, ValueError, OSError):
            ts = now
        db.add(LoggerEvent(
            site_id=site.id, event_uid=uid,
            type=etype if etype in _KNOWN_EVENT_TYPES else "unknown",
            ts=ts, received_at=now,
            severity=e.get("severity") or "info",
            detail=e.get("detail"),
        ))
        existing.add(uid)   # guard against duplicates inside the same batch
        accepted += 1
    await db.commit()
    return {"ok": True, "accepted": accepted, "duplicates": duplicates}
```

- [ ] **Step 4: Run the full suite** → Expected: `116 passed`.

- [ ] **Step 5: Commit**

```bash
git add sparing_api/app/api/routers/logger.py sparing_api/app/tests/test_logger_api.py
git commit -m "feat(logger): idempotent POST /logger/events batch ingest"
```

---

### Task 7: Dead-man's switch + logger alarms (TDD)

**Files:** Modify `app/utils/logger_monitor.py`, `app/main.py`; create `app/tests/test_logger_monitor.py`

- [ ] **Step 1: Write the failing tests**

Create `app/tests/test_logger_monitor.py`:

```python
from datetime import datetime, timezone, timedelta

import pytest
from sqlalchemy import select

from app.models.models import Site, LoggerStatus, Alert
from app.utils.logger_monitor import scan_logger_liveness, resolve_logger_down_alert


async def _site_with_status(db, uid, minutes_ago, state="alive"):
    s = Site(uid=uid, name=uid, company_name="C", is_active=True)
    db.add(s)
    await db.commit()
    await db.refresh(s)
    st = LoggerStatus(
        site_id=s.id, state=state,
        last_heartbeat_at=datetime.now(timezone.utc) - timedelta(minutes=minutes_ago),
        state_since=datetime.now(timezone.utc) - timedelta(minutes=minutes_ago),
    )
    db.add(st)
    await db.commit()
    return s


@pytest.mark.anyio
async def test_silent_logger_marked_down_and_alerted(db_session):
    site = await _site_with_status(db_session, "L-DOWN", minutes_ago=15)
    await scan_logger_liveness(db_session)

    st = (await db_session.execute(select(LoggerStatus))).scalars().first()
    assert st.state == "down"
    alerts = (await db_session.execute(select(Alert))).scalars().all()
    assert len(alerts) == 1
    a = alerts[0]
    assert a.category == "logger" and a.field == "logger_down"
    assert a.threshold_type == "danger" and a.status == "active"
    assert a.site_id == site.id


@pytest.mark.anyio
async def test_recent_heartbeat_not_alerted(db_session):
    await _site_with_status(db_session, "L-OK", minutes_ago=3)
    await scan_logger_liveness(db_session)
    st = (await db_session.execute(select(LoggerStatus))).scalars().first()
    assert st.state == "alive"
    assert (await db_session.execute(select(Alert))).scalars().first() is None


@pytest.mark.anyio
async def test_scan_is_idempotent_across_concurrent_workers(db_session):
    """Two gunicorn workers run the scheduler; a second pass must not duplicate."""
    await _site_with_status(db_session, "L-DUP", minutes_ago=20)
    await scan_logger_liveness(db_session)
    await scan_logger_liveness(db_session)
    alerts = (await db_session.execute(select(Alert))).scalars().all()
    assert len(alerts) == 1


@pytest.mark.anyio
async def test_recovery_resolves_with_system_note(db_session):
    site = await _site_with_status(db_session, "L-BACK", minutes_ago=20)
    await scan_logger_liveness(db_session)
    now = datetime.now(timezone.utc)
    await resolve_logger_down_alert(db_session, site.id, now)

    a = (await db_session.execute(select(Alert))).scalars().first()
    assert a.status == "resolved"
    assert a.resolved_at is not None
    assert a.followup_note   # system note, so the mandatory-note rule isn't tripped
```

- [ ] **Step 2: Run to verify they fail** — Expected: ImportError for
`scan_logger_liveness` (only the stub exists).

- [ ] **Step 3: Implement** — replace `app/utils/logger_monitor.py` with:

```python
"""Server-side liveness inference for field loggers.

A dead logger cannot announce its own death, so absence of heartbeats is the
signal. Judged on the server-recorded last_heartbeat_at (never the logger clock).
Both gunicorn workers run this on a schedule, so every write is idempotent:
one active alert per (site, field), found with .first() rather than
scalar_one_or_none so historical duplicates can't raise.
"""
from datetime import datetime, timezone, timedelta

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import logger as applog
from app.models.models import Alert, LoggerStatus, Site

DOWN_AFTER_MINUTES = 10          # silence threshold (spec: ~10 min)
SENSOR_FAIL_MINUTES = 15         # a sensor failing this long raises a warning
LOGGER_DOWN_FIELD = "logger_down"
LOGGER_CATEGORY = "logger"
AUTO_RESOLVE_NOTE = "Pulih otomatis — logger kembali mengirim heartbeat"


async def _active_alert(db: AsyncSession, site_id: int, field: str):
    return (await db.execute(
        select(Alert).where(
            Alert.site_id == site_id,
            Alert.field == field,
            Alert.category == LOGGER_CATEGORY,
            Alert.status == "active",
        ).limit(1)
    )).scalars().first()


async def scan_logger_liveness(db: AsyncSession) -> int:
    """Flip silent loggers to 'down' and raise one alert each. Returns count flipped."""
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(minutes=DOWN_AFTER_MINUTES)
    rows = (await db.execute(
        select(LoggerStatus, Site).join(Site, Site.id == LoggerStatus.site_id)
        .where(Site.is_active == True)
    )).all()

    flipped = 0
    for st, site in rows:
        last = st.last_heartbeat_at
        if last is not None and last.tzinfo is None:
            last = last.replace(tzinfo=timezone.utc)   # MySQL returns naive UTC
        silent = last is None or last < cutoff
        if not silent:
            continue
        if st.state != "down":
            st.state = "down"
            st.state_since = now
            flipped += 1
        if await _active_alert(db, site.id, LOGGER_DOWN_FIELD) is None:
            minutes = 999.0 if last is None else round((now - last).total_seconds() / 60, 1)
            db.add(Alert(
                site_id=site.id, device_uid=None, field=LOGGER_DOWN_FIELD,
                value=minutes, threshold_type="danger", status="active",
                triggered_at=now, category=LOGGER_CATEGORY,
                detail=f"Tidak ada heartbeat selama {minutes:.0f} menit",
            ))
    await db.commit()
    if flipped:
        applog.warning("logger liveness: %d logger(s) marked down", flipped)
    return flipped


async def resolve_logger_down_alert(db: AsyncSession, site_id: int, now: datetime) -> None:
    """Auto-resolve on heartbeat return. Writes a system note so recovery is never
    blocked by the mandatory-note rule that governs manual closure."""
    await db.execute(
        update(Alert).where(
            Alert.site_id == site_id,
            Alert.field == LOGGER_DOWN_FIELD,
            Alert.category == LOGGER_CATEGORY,
            Alert.status == "active",
        ).values(status="resolved", resolved_at=now, followup_note=AUTO_RESOLVE_NOTE)
    )
    await db.commit()
```

In `app/main.py`, add the scheduler job alongside the existing ones:
```python
async def _check_logger_liveness():
    """Dead-man's switch for field loggers — runs every 2 minutes."""
    from app.core.db import get_db
    from app.utils.logger_monitor import scan_logger_liveness
    try:
        async for db in get_db():
            await scan_logger_liveness(db)
            break
    except Exception:
        logger.exception("Logger liveness scheduler failed")
```
and in `startup_event`:
```python
    scheduler.add_job(_check_logger_liveness, "interval", minutes=2, id="logger_liveness")
```

- [ ] **Step 4: Run the full suite** → Expected: `120 passed`.

- [ ] **Step 5: Commit**

```bash
git add sparing_api/app/utils/logger_monitor.py sparing_api/app/main.py sparing_api/app/tests/test_logger_monitor.py
git commit -m "feat(logger): dead-man's switch raising logger_down alarms with auto-resolve"
```

---

### Task 8: Sensor-failure alarm (TDD)

A sensor reporting `*_ok=false` on every heartbeat for >15 minutes raises a `warning`.

**Files:** Modify `app/utils/logger_monitor.py`; extend `app/tests/test_logger_monitor.py`

- [ ] **Step 1: Write the failing test** — append:

```python
@pytest.mark.anyio
async def test_persistent_sensor_failure_raises_warning(db_session):
    site = await _site_with_status(db_session, "L-SENS", minutes_ago=1)
    st = (await db_session.execute(select(LoggerStatus))).scalars().first()
    st.tss_ok = False
    st.sensor_fail_since = datetime.now(timezone.utc) - timedelta(minutes=20)
    await db_session.commit()

    await scan_logger_liveness(db_session)
    alerts = (await db_session.execute(select(Alert))).scalars().all()
    sensor_alerts = [a for a in alerts if a.field == "sensor_tss"]
    assert len(sensor_alerts) == 1
    assert sensor_alerts[0].threshold_type == "warning"
    assert sensor_alerts[0].category == "logger"


@pytest.mark.anyio
async def test_brief_sensor_failure_not_alerted(db_session):
    await _site_with_status(db_session, "L-BRIEF", minutes_ago=1)
    st = (await db_session.execute(select(LoggerStatus))).scalars().first()
    st.tss_ok = False
    st.sensor_fail_since = datetime.now(timezone.utc) - timedelta(minutes=3)
    await db_session.commit()

    await scan_logger_liveness(db_session)
    alerts = (await db_session.execute(select(Alert))).scalars().all()
    assert not [a for a in alerts if a.field.startswith("sensor_")]
```

- [ ] **Step 2: Run to verify they fail** — Expected: AttributeError
(`sensor_fail_since` does not exist).

- [ ] **Step 3: Implement**

(a) The heartbeat must remember *when* a sensor first started failing. Add to
`LoggerStatus` (model) and to migration `0009` (it has not shipped yet — edit it
rather than adding 0011):
```python
    sensor_fail_since: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
```
and in `0009_logger_monitoring.py`'s `logger_status` table:
```python
        sa.Column('sensor_fail_since', sa.DateTime(timezone=True), nullable=True),
```

(b) In `app/api/routers/logger.py`'s `heartbeat`, after applying the status fields:
```python
    any_failed = any(getattr(st, f) is False for f in ("ph_ok", "tss_ok", "debit_ok", "cod_ok", "nh3n_ok"))
    if any_failed and st.sensor_fail_since is None:
        st.sensor_fail_since = now
    elif not any_failed:
        st.sensor_fail_since = None
```

(c) In `scan_logger_liveness`, after the liveness block (still inside the loop, for
sites that are NOT silent):
```python
        # (place this before `if not silent: continue` is evaluated — restructure so
        # sensor checks run for live loggers)
```
Concretely, restructure the loop body to:
```python
    for st, site in rows:
        last = st.last_heartbeat_at
        if last is not None and last.tzinfo is None:
            last = last.replace(tzinfo=timezone.utc)
        silent = last is None or last < cutoff

        if silent:
            ...existing down-marking + alert block...
            continue

        if st.state != "alive":
            st.state = "alive"
            st.state_since = now

        fail_since = st.sensor_fail_since
        if fail_since is not None and fail_since.tzinfo is None:
            fail_since = fail_since.replace(tzinfo=timezone.utc)
        if fail_since is not None and fail_since < now - timedelta(minutes=SENSOR_FAIL_MINUTES):
            for name in ("ph", "tss", "debit", "cod", "nh3n"):
                if getattr(st, f"{name}_ok") is False:
                    field = f"sensor_{name}"
                    if await _active_alert(db, site.id, field) is None:
                        db.add(Alert(
                            site_id=site.id, device_uid=None, field=field,
                            value=0.0, threshold_type="warning", status="active",
                            triggered_at=now, category=LOGGER_CATEGORY,
                            detail=f"Sensor {name.upper()} gagal dibaca sejak {fail_since:%H:%M}",
                        ))
```

- [ ] **Step 4: Run the full suite** → Expected: `122 passed`.

- [ ] **Step 5: Commit**

```bash
git add sparing_api/app/utils/logger_monitor.py sparing_api/app/api/routers/logger.py sparing_api/app/models/models.py sparing_api/alembic/versions/0009_logger_monitoring.py sparing_api/app/tests/test_logger_monitor.py
git commit -m "feat(logger): warning alarm for sensors failing longer than 15 minutes"
```

---

### Task 9: Web read endpoints — `GET /logger/status` and `/logger/events` (TDD)

**Files:** Modify `app/api/routers/logger.py`; extend `app/tests/test_logger_api.py`

- [ ] **Step 1: Write the failing tests** — append to `app/tests/test_logger_api.py`:

```python
from app.models.models import ViewerSite


@pytest.mark.anyio
async def test_status_list_returns_derived_state(client, db_session):
    await _site(db_session)
    await client.post("/logger/heartbeat", json={"token": _hb_token("LOG-1", STATUS)})
    headers = await _auth_headers(client, db_session)

    res = await client.get("/logger/status", headers=headers)
    assert res.status_code == 200
    item = res.json()[0]
    assert item["site_uid"] == "LOG-1"
    assert item["state"] == "alive"
    assert item["minutes_since_heartbeat"] < 1
    assert item["tss_ok"] is False
    assert item["buffer_depth"] == 12


@pytest.mark.anyio
async def test_viewer_only_sees_assigned_sites(client, db_session):
    a = await _site(db_session, uid="LOG-A")
    await _site(db_session, uid="LOG-B")
    await client.post("/logger/heartbeat", json={"token": _hb_token("LOG-A", STATUS)})
    await client.post("/logger/heartbeat", json={"token": _hb_token("LOG-B", STATUS)})

    db_session.add(User(name="V", email="v@example.com",
                        password_hash=hash_password("Secret123"), role="viewer", is_active=True))
    await db_session.commit()
    viewer = (await db_session.execute(select(User).where(User.email == "v@example.com"))).scalars().first()
    db_session.add(ViewerSite(user_id=viewer.id, site_id=a.id))
    await db_session.commit()
    login = await client.post("/auth/login", json={"email": "v@example.com", "password": "Secret123"})
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    res = await client.get("/logger/status", headers=headers)
    uids = {i["site_uid"] for i in res.json()}
    assert uids == {"LOG-A"}


@pytest.mark.anyio
async def test_events_list_filters_and_paginates(client, db_session):
    await _site(db_session)
    events = [{"event_uid": f"p-{i}", "type": "started" if i % 2 else "net_down",
               "ts": 1753000000 + i, "severity": "info"} for i in range(5)]
    await client.post("/logger/events", json={"token": _ev_token("LOG-1", events)})
    headers = await _auth_headers(client, db_session)

    bare = await client.get("/logger/events", headers=headers)
    assert isinstance(bare.json(), list)

    paged = await client.get("/logger/events", params={"page": 1, "per_page": 2}, headers=headers)
    body = paged.json()
    assert body["total"] == 5 and len(body["items"]) == 2

    filtered = await client.get("/logger/events", params={"type": "started"}, headers=headers)
    assert all(e["type"] == "started" for e in filtered.json())
```

- [ ] **Step 2: Run to verify they fail** — Expected: 404 on the GET routes.

- [ ] **Step 3: Implement** — append to `app/api/routers/logger.py`:

```python
from app.api.deps import get_current_user, get_viewer_site_uids
from app.models.models import LoggerEvent, User
from app.schemas.logger import LoggerStatusOut, LoggerEventOut


async def _scoped_site_ids(db: AsyncSession, viewer_uids: list[str]) -> list[int] | None:
    """None = no restriction (admin/operator); a list = viewer's sites."""
    if not viewer_uids:
        return None
    return list((await db.execute(select(Site.id).where(Site.uid.in_(viewer_uids)))).scalars().all())


@router.get("/status", response_model=list[LoggerStatusOut])
async def list_logger_status(
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
    viewer_uids: list[str] = Depends(get_viewer_site_uids),
):
    scoped = await _scoped_site_ids(db, viewer_uids)
    if scoped is not None and not scoped:
        return []
    q = select(LoggerStatus, Site).join(Site, Site.id == LoggerStatus.site_id)
    if scoped is not None:
        q = q.where(LoggerStatus.site_id.in_(scoped))
    now = datetime.now(timezone.utc)
    out = []
    for st, site in (await db.execute(q)).all():
        last = st.last_heartbeat_at
        if last is not None and last.tzinfo is None:
            last = last.replace(tzinfo=timezone.utc)
        mins = None if last is None else round((now - last).total_seconds() / 60, 2)
        out.append(LoggerStatusOut(
            site_id=site.id, site_uid=site.uid, site_name=site.name,
            state=st.state, state_since=st.state_since,
            last_heartbeat_at=st.last_heartbeat_at, minutes_since_heartbeat=mins,
            **{f: getattr(st, f) for f in _STATUS_FIELDS},
        ))
    return out


@router.get("/events")
async def list_logger_events(
    site_uid: str | None = Query(default=None),
    type: str | None = Query(default=None),
    severity: str | None = Query(default=None),
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
    limit: int = Query(default=50, le=200),
    page: int | None = Query(default=None, ge=1),
    per_page: int = Query(default=50, le=200),
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
    viewer_uids: list[str] = Depends(get_viewer_site_uids),
):
    """Bare list when `page` is absent; {items,total,page,per_page} when given."""
    from sqlalchemy import func

    scoped = await _scoped_site_ids(db, viewer_uids)
    if scoped is not None and not scoped:
        return {"items": [], "total": 0, "page": page, "per_page": per_page} if page else []

    conds = []
    if scoped is not None:
        conds.append(LoggerEvent.site_id.in_(scoped))
    if site_uid:
        s = (await db.execute(select(Site).where(Site.uid == site_uid))).scalars().first()
        if not s:
            return {"items": [], "total": 0, "page": page, "per_page": per_page} if page else []
        conds.append(LoggerEvent.site_id == s.id)
    if type:
        conds.append(LoggerEvent.type == type)
    if severity:
        conds.append(LoggerEvent.severity == severity)
    if date_from:
        conds.append(LoggerEvent.ts >= date_from)
    if date_to:
        conds.append(LoggerEvent.ts < date_to)

    base = select(LoggerEvent, Site).join(Site, Site.id == LoggerEvent.site_id).where(*conds) \
        .order_by(LoggerEvent.ts.desc())

    def _out(ev, site):
        return LoggerEventOut(
            id=ev.id, site_id=site.id, site_uid=site.uid, site_name=site.name,
            event_uid=ev.event_uid, type=ev.type, ts=ev.ts, received_at=ev.received_at,
            severity=ev.severity, detail=ev.detail,
        )

    if page is None:
        rows = (await db.execute(base.limit(limit))).all()
        return [_out(ev, site) for ev, site in rows]

    total = (await db.execute(
        select(func.count(LoggerEvent.id)).where(*conds)
    )).scalar_one()
    rows = (await db.execute(base.offset((page - 1) * per_page).limit(per_page))).all()
    return {"items": [_out(ev, site) for ev, site in rows],
            "total": total, "page": page, "per_page": per_page}
```

- [ ] **Step 4: Run the full suite** → Expected: `125 passed`.

- [ ] **Step 5: Commit**

```bash
git add sparing_api/app/api/routers/logger.py sparing_api/app/tests/test_logger_api.py
git commit -m "feat(logger): viewer-scoped GET /logger/status and /logger/events"
```

---

### Task 10: Full suite, deploy, production verification

- [ ] **Step 1: Full suite + app import**

```bash
.venv/Scripts/python.exe -m pytest app/tests/ -q
.venv/Scripts/python.exe -c "from app.main import app; print('routes:', len(app.routes))"
```
Expected: `125 passed`; the route count grows by 4.

- [ ] **Step 2: Push and deploy backend**

```bash
git push origin main
ssh mitramutiara-prod "sudo bash /opt/sparing/repo/scripts/deploy.sh backend"
```
Expected: `import ok`, `Running upgrade 0008 -> 0009`, `0009 -> 0010`, restart, `healthy`.
(Prod deploy over SSH is usually gated by the auto-mode classifier — the user must approve.)

- [ ] **Step 3: Production verification**

New device routes must exist (they reject unsigned calls rather than 404):
```bash
B=https://sparingapi.mitramutiara.co.id
curl -s -o /dev/null -w 'heartbeat -> %{http_code}\n' -X POST "$B/logger/heartbeat" -H 'Content-Type: application/json' -d '{}'
curl -s -o /dev/null -w 'events    -> %{http_code}\n' -X POST "$B/logger/events" -H 'Content-Type: application/json' -d '{}'
curl -s -o /dev/null -w 'status    -> %{http_code}\n' "$B/logger/status"
curl -s -o /dev/null -w 'events(g) -> %{http_code}\n' "$B/logger/events"
```
Expected: the two POSTs return **400** ("Token is required" — route exists, auth
enforced), the two GETs return **401** (auth required). A **404** means the router did
not register.

Confirm the migrations applied:
```bash
ssh mitramutiara-prod "cd /opt/sparing/api && sudo -u www-data ./.venv/bin/python -m alembic current"
```
Expected: `0010_sensor_data_op_status (head)`.

- [ ] **Step 4: Report** the deployed state and hand off to Plan 2 (logger app).

---

## Self-Review Notes

- **Spec coverage:** §2.1 tables → Task 2 (+ `sensor_fail_since` folded into 0009 in
  Task 8, since 0009 has not shipped); §2.2 endpoints → Tasks 5, 6, 9; §2.3 dead-man's
  switch → Task 7; §2.4 noise policy → Tasks 7 (logger_down danger) and 8 (sensor
  warning); internet-down and restart deliberately raise **no** alert, matching the
  policy; §2.5 op_status → Tasks 3 and 4. The shared device-auth extraction (Task 1)
  is an enabling refactor the spec implies by requiring identical auth.
- **Type consistency:** `_STATUS_FIELDS` is the single list used by both the heartbeat
  writer and the `LoggerStatusOut` builder, so the two cannot drift; `state` is only
  ever `alive`/`down`; `event_uid` is the unique idempotency key in the model,
  migration, and the ingest path.
- **Concurrency:** every scheduler write is dedup-guarded with `.first()` (never
  `scalar_one_or_none`), matching the pattern proven in `alert_engine`.
- **Naive/aware datetimes:** MySQL returns naive UTC, so every comparison against
  `now` normalises with `.replace(tzinfo=timezone.utc)` first — the bug class that
  previously broke the anomaly engine.
- **Deliberately deferred:** Plan 2 (logger app `telemetry.py`, event log, crash
  marker, `ExecStopPost`) and Plan 3 (frontend `/loggers` page, dashboard chip, Alarm
  category, History badge).
