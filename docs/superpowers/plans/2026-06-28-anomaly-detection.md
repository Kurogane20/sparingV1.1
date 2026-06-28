# Sensor Data Quality & Anomaly Detection Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Detect sensor data-quality problems (implausible values, flatline, spike, drift) that the baku-mutu alert engine misses, surfacing them as a new `data_quality` alert category plus a per-sensor health badge on the dashboard.

**Architecture:** A new `anomaly_engine.py` module (mirroring the existing `alert_engine.py`) holds pure, stdlib-only detection functions plus DB orchestration. Realtime checks (implausible/flatline/spike) hook into `getdata.py` ingest; drift runs as an hourly APScheduler job. Results write to the existing `alerts` table (new `category`/`anomaly_type`/`detail` columns) and a new `sensor_health` table read by the dashboard. A reserved `score` column lets a future ML scorer plug in without schema change.

**Tech Stack:** Python 3 / FastAPI / SQLAlchemy async / Alembic / MySQL (aiomysql), Vue 3, pytest. Detection uses only the Python stdlib `statistics` module — no numpy/pandas.

**Reference spec:** `docs/superpowers/specs/2026-06-28-anomaly-detection-design.md`

**Scope:** Parameters `ph, tss, cod, nh3n, temp, debit`. Out of scope: `voltage`, `current` (pending sensor research); email notifications (deferred); ML scorer (deferred).

---

## File Structure

**Backend (`sparing_api/`):**
- Create `app/utils/anomaly_engine.py` — config, `AnomalyResult`, 4 pure detectors, DB orchestration.
- Create `app/tests/test_anomaly_engine.py` — unit tests for the pure detectors.
- Modify `app/models/models.py` — add 3 columns to `Alert`; add `SensorHealth` model.
- Create `alembic/versions/0006_add_anomaly_detection.py` — migration.
- Modify `app/api/routers/getdata.py` — fire `detect_realtime` after commit.
- Modify `app/main.py` — register hourly drift job.
- Create `app/schemas/sensor_health.py` — `SensorHealthOut`.
- Modify `app/api/routers/sites.py` — `GET /sites/{uid}/sensor-health`.
- Modify `app/schemas/alert.py` + `app/api/routers/alerts.py` — expose `category/anomaly_type/detail`.

**Frontend (`sparing_front/`):**
- Modify `resources/js/Composables/useApi.js` — `getSensorHealth`.
- Modify `resources/js/Pages/Dashboard/Index.vue` — fetch health, pass to cards.
- Modify `resources/js/Components/SensorCard.vue` — health dot + tooltip.
- Modify `resources/js/Components/AlertDropdown.vue` — distinct `data_quality` rendering.

**Conventions:**
- All backend commands run from `sparing_api/` using the venv interpreter: `.venv/Scripts/python.exe`.
- All `git` commands run from the repo root `c:\Users\nurch\OneDrive\Documents\project\sparingV1.1`.
- The detectors are pure (input → result, no I/O) so they are fully unit-tested. DB orchestration mirrors the proven `alert_engine.py` pattern (own session, total try/except, fire-and-forget) and is verified by a manual smoke test, because the repo has no async-DB test fixture (adding one is out of scope).

---

## Task 0: Test tooling setup

**Files:** none (environment only)

- [ ] **Step 1: Install pytest into the venv**

The repo has test files but pytest is not installed in `.venv`. Install it.

Run (from `sparing_api/`):
```bash
.venv/Scripts/python.exe -m pip install pytest
```
Expected: `Successfully installed pytest-...`

- [ ] **Step 2: Verify existing tests run**

Run (from `sparing_api/`):
```bash
.venv/Scripts/python.exe -m pytest app/tests/test_alert_engine.py -v
```
Expected: 7 passed.

---

## Task 1: Config, `AnomalyResult`, and `check_implausible`

**Files:**
- Create: `sparing_api/app/utils/anomaly_engine.py`
- Test: `sparing_api/app/tests/test_anomaly_engine.py`

- [ ] **Step 1: Write the failing tests**

Create `sparing_api/app/tests/test_anomaly_engine.py`:
```python
from app.utils.anomaly_engine import check_implausible, AnomalyResult, PLAUSIBLE_RANGES, IN_SCOPE_FIELDS


def test_in_scope_fields_exact():
    assert IN_SCOPE_FIELDS == ["ph", "tss", "cod", "nh3n", "temp", "debit"]
    assert "voltage" not in PLAUSIBLE_RANGES
    assert "current" not in PLAUSIBLE_RANGES


def test_implausible_ph_above_range():
    r = check_implausible("ph", 13.9)
    assert isinstance(r, AnomalyResult)
    assert r.anomaly_type == "implausible"
    assert r.severity == "danger"


def test_implausible_ph_in_range_is_none():
    assert check_implausible("ph", 7.5) is None


def test_implausible_tss_below_zero():
    r = check_implausible("tss", -3.0)
    assert r is not None and r.anomaly_type == "implausible"


def test_implausible_boundary_inclusive():
    # exactly on the boundary is NOT implausible
    assert check_implausible("ph", 2.0) is None
    assert check_implausible("ph", 12.0) is None


def test_implausible_unknown_field_is_none():
    assert check_implausible("voltage", 9999.0) is None


def test_implausible_none_value_is_none():
    assert check_implausible("ph", None) is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run (from `sparing_api/`):
```bash
.venv/Scripts/python.exe -m pytest app/tests/test_anomaly_engine.py -v
```
Expected: FAIL — `ModuleNotFoundError: No module named 'app.utils.anomaly_engine'`.

- [ ] **Step 3: Write minimal implementation**

Create `sparing_api/app/utils/anomaly_engine.py`:
```python
"""Sensor data-quality / anomaly detection.

Pure detection functions (stdlib only) + DB orchestration that mirrors
app/utils/alert_engine.py. Never raises into the ingest path.
"""
from dataclasses import dataclass


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
```

- [ ] **Step 4: Run tests to verify they pass**

Run (from `sparing_api/`):
```bash
.venv/Scripts/python.exe -m pytest app/tests/test_anomaly_engine.py -v
```
Expected: 7 passed.

- [ ] **Step 5: Commit**

Run (from repo root):
```bash
git add sparing_api/app/utils/anomaly_engine.py sparing_api/app/tests/test_anomaly_engine.py
git commit -m "feat(anomaly): config, AnomalyResult, implausible-range detector"
```

---

## Task 2: `check_flatline`

**Files:**
- Modify: `sparing_api/app/utils/anomaly_engine.py`
- Test: `sparing_api/app/tests/test_anomaly_engine.py`

- [ ] **Step 1: Write the failing tests**

Append to `sparing_api/app/tests/test_anomaly_engine.py`:
```python
from datetime import datetime, timedelta
from app.utils.anomaly_engine import check_flatline


def _series(start, minutes_step, values):
    return [(start + timedelta(minutes=i * minutes_step), v) for i, v in enumerate(values)]


def test_flatline_stuck_value_over_window():
    start = datetime(2026, 6, 1, 0, 0, 0)
    # 8 identical readings, 2 min apart => spans 14 min... need >= 15 min, use 9 points
    samples = _series(start, 2, [7.2] * 9)  # spans 16 min
    r = check_flatline(samples, "ph")
    assert r is not None and r.anomaly_type == "flatline" and r.severity == "danger"


def test_flatline_varying_values_not_flagged():
    start = datetime(2026, 6, 1, 0, 0, 0)
    samples = _series(start, 2, [7.2, 7.3, 7.2, 7.4, 7.1, 7.2, 7.3, 7.2, 7.5])
    assert check_flatline(samples, "ph") is None


def test_flatline_window_too_short_not_flagged():
    start = datetime(2026, 6, 1, 0, 0, 0)
    samples = _series(start, 2, [7.2, 7.2, 7.2])  # spans only 4 min
    assert check_flatline(samples, "ph") is None


def test_flatline_too_few_samples_not_flagged():
    start = datetime(2026, 6, 1, 0, 0, 0)
    assert check_flatline(_series(start, 2, [7.2]), "ph") is None
    assert check_flatline([], "ph") is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run (from `sparing_api/`):
```bash
.venv/Scripts/python.exe -m pytest app/tests/test_anomaly_engine.py -k flatline -v
```
Expected: FAIL — `ImportError: cannot import name 'check_flatline'`.

- [ ] **Step 3: Write minimal implementation**

Add to `sparing_api/app/utils/anomaly_engine.py` — first add the constant in the config block:
```python
FLATLINE_MIN_MINUTES = 15
```
Then add the function (after `check_implausible`):
```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run (from `sparing_api/`):
```bash
.venv/Scripts/python.exe -m pytest app/tests/test_anomaly_engine.py -v
```
Expected: all passed (11 total).

- [ ] **Step 5: Commit**

Run (from repo root):
```bash
git add sparing_api/app/utils/anomaly_engine.py sparing_api/app/tests/test_anomaly_engine.py
git commit -m "feat(anomaly): flatline (stuck sensor) detector"
```

---

## Task 3: `check_spike` (MAD-based)

**Files:**
- Modify: `sparing_api/app/utils/anomaly_engine.py`
- Test: `sparing_api/app/tests/test_anomaly_engine.py`

- [ ] **Step 1: Write the failing tests**

Append to `sparing_api/app/tests/test_anomaly_engine.py`:
```python
from app.utils.anomaly_engine import check_spike, _mad


def test_mad_basic():
    # median=3, abs devs=[2,1,0,1,2] median=1
    assert _mad([1, 2, 3, 4, 5]) == 1


def test_spike_obvious_outlier_flagged():
    history = [7.0, 7.1, 6.9, 7.0, 7.2, 6.8, 7.1, 7.0, 6.9, 7.1]
    r = check_spike(12.0, history, "ph")
    assert r is not None and r.anomaly_type == "spike" and r.severity == "warning"


def test_spike_normal_value_not_flagged():
    history = [7.0, 7.1, 6.9, 7.0, 7.2, 6.8, 7.1, 7.0, 6.9, 7.1]
    assert check_spike(7.05, history, "ph") is None


def test_spike_insufficient_history_not_flagged():
    assert check_spike(99.0, [7.0, 7.1, 6.9], "ph") is None


def test_spike_small_delta_below_min_abs_not_flagged():
    # flat history (mad=0); tiny delta below per-field min abs delta -> not flagged
    history = [7.0] * 12
    assert check_spike(7.2, history, "ph") is None  # ph min abs delta = 1.0


def test_spike_flat_history_large_delta_flagged():
    history = [7.0] * 12
    r = check_spike(10.0, history, "ph")  # delta 3.0 > min abs 1.0
    assert r is not None and r.anomaly_type == "spike"
```

- [ ] **Step 2: Run tests to verify they fail**

Run (from `sparing_api/`):
```bash
.venv/Scripts/python.exe -m pytest app/tests/test_anomaly_engine.py -k "spike or mad" -v
```
Expected: FAIL — `ImportError: cannot import name 'check_spike'`.

- [ ] **Step 3: Write minimal implementation**

Add to the top of `sparing_api/app/utils/anomaly_engine.py` (imports):
```python
import statistics
```
Add to the config block:
```python
SPIKE_WINDOW_MINUTES = 120
SPIKE_K = 5.0
SPIKE_MIN_POINTS = 10
SPIKE_MIN_ABS_DELTA = {
    "ph": 1.0, "tss": 50.0, "cod": 100.0, "nh3n": 3.0, "temp": 5.0, "debit": 50.0,
}
```
Add the functions:
```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run (from `sparing_api/`):
```bash
.venv/Scripts/python.exe -m pytest app/tests/test_anomaly_engine.py -v
```
Expected: all passed (18 total).

- [ ] **Step 5: Commit**

Run (from repo root):
```bash
git add sparing_api/app/utils/anomaly_engine.py sparing_api/app/tests/test_anomaly_engine.py
git commit -m "feat(anomaly): MAD-based spike detector"
```

---

## Task 4: `check_drift`

**Files:**
- Modify: `sparing_api/app/utils/anomaly_engine.py`
- Test: `sparing_api/app/tests/test_anomaly_engine.py`

- [ ] **Step 1: Write the failing tests**

Append to `sparing_api/app/tests/test_anomaly_engine.py`:
```python
from app.utils.anomaly_engine import check_drift


def test_drift_sustained_shift_flagged():
    baseline = [100.0] * 50
    recent = [140.0] * 20   # +40% shift, > 25%
    r = check_drift(recent, baseline, "cod")
    assert r is not None and r.anomaly_type == "drift" and r.severity == "warning"


def test_drift_stable_not_flagged():
    baseline = [100.0] * 50
    recent = [103.0] * 20   # +3%
    assert check_drift(recent, baseline, "cod") is None


def test_drift_empty_windows_not_flagged():
    assert check_drift([], [100.0], "cod") is None
    assert check_drift([100.0], [], "cod") is None


def test_drift_tiny_baseline_floor_prevents_false_positive():
    # baseline near zero would explode pct; floor keeps it sane
    baseline = [0.1] * 50
    recent = [0.3] * 20
    assert check_drift(recent, baseline, "cod") is None  # cod floor = 10.0
```

- [ ] **Step 2: Run tests to verify they fail**

Run (from `sparing_api/`):
```bash
.venv/Scripts/python.exe -m pytest app/tests/test_anomaly_engine.py -k drift -v
```
Expected: FAIL — `ImportError: cannot import name 'check_drift'`.

- [ ] **Step 3: Write minimal implementation**

Add to the config block:
```python
DRIFT_RECENT_HOURS = 24
DRIFT_BASELINE_DAYS = 7
DRIFT_PCT = 0.25
DRIFT_MIN_BASELINE = {
    "ph": 1.0, "tss": 10.0, "cod": 10.0, "nh3n": 1.0, "temp": 5.0, "debit": 5.0,
}
```
Add the function:
```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run (from `sparing_api/`):
```bash
.venv/Scripts/python.exe -m pytest app/tests/test_anomaly_engine.py -v
```
Expected: all passed (22 total).

- [ ] **Step 5: Commit**

Run (from repo root):
```bash
git add sparing_api/app/utils/anomaly_engine.py sparing_api/app/tests/test_anomaly_engine.py
git commit -m "feat(anomaly): drift detector"
```

---

## Task 5: Data model + Alembic migration

**Files:**
- Modify: `sparing_api/app/models/models.py:151-164` (Alert class) and add `SensorHealth`
- Create: `sparing_api/alembic/versions/0006_add_anomaly_detection.py`

- [ ] **Step 1: Add columns to the `Alert` model**

In `sparing_api/app/models/models.py`, inside `class Alert`, after the `triggered_at` line (line 160) add:
```python
    category: Mapped[str] = mapped_column(String(16), default="compliance", server_default="compliance")
    anomaly_type: Mapped[str | None] = mapped_column(String(16), nullable=True)
    detail: Mapped[str | None] = mapped_column(String(255), nullable=True)
```

- [ ] **Step 2: Add the `SensorHealth` model**

In `sparing_api/app/models/models.py`, immediately after the `Alert` class (before `class MaintenanceLog`), add:
```python
class SensorHealth(Base):
    __tablename__ = "sensor_health"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id", ondelete="CASCADE"), index=True)
    field: Mapped[str] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(String(16), default="ok")  # ok | warning | bad
    anomaly_type: Mapped[str | None] = mapped_column(String(16), nullable=True)
    reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    last_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    score: Mapped[float | None] = mapped_column(Float, nullable=True)  # reserved for future ML scorer
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    __table_args__ = (UniqueConstraint("site_id", "field", name="uq_sensor_health_site_field"),)
```

- [ ] **Step 3: Create the migration**

Create `sparing_api/alembic/versions/0006_add_anomaly_detection.py`:
```python
from alembic import op
import sqlalchemy as sa

revision = '0006_add_anomaly_detection'
down_revision = '0005_add_site_timezone'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('alerts', sa.Column('category', sa.String(16), nullable=False, server_default='compliance'))
    op.add_column('alerts', sa.Column('anomaly_type', sa.String(16), nullable=True))
    op.add_column('alerts', sa.Column('detail', sa.String(255), nullable=True))

    op.create_table(
        'sensor_health',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('site_id', sa.Integer(), sa.ForeignKey('sites.id', ondelete='CASCADE'), nullable=False),
        sa.Column('field', sa.String(32), nullable=False),
        sa.Column('status', sa.String(16), nullable=False, server_default='ok'),
        sa.Column('anomaly_type', sa.String(16), nullable=True),
        sa.Column('reason', sa.String(255), nullable=True),
        sa.Column('last_value', sa.Float(), nullable=True),
        sa.Column('score', sa.Float(), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint('site_id', 'field', name='uq_sensor_health_site_field'),
    )
    op.create_index('ix_sensor_health_site_id', 'sensor_health', ['site_id'])


def downgrade():
    op.drop_index('ix_sensor_health_site_id', table_name='sensor_health')
    op.drop_table('sensor_health')
    op.drop_column('alerts', 'detail')
    op.drop_column('alerts', 'anomaly_type')
    op.drop_column('alerts', 'category')
```

- [ ] **Step 4: Apply and verify the migration (local/dev DB)**

Run (from `sparing_api/`):
```bash
.venv/Scripts/python.exe -m alembic upgrade head
```
Expected: `Running upgrade 0005_add_site_timezone -> 0006_add_anomaly_detection`.

Verify the models import cleanly:
```bash
.venv/Scripts/python.exe -c "from app.models.models import Alert, SensorHealth; print('ok', SensorHealth.__tablename__)"
```
Expected: `ok sensor_health`.

> Note: if no local MySQL is available, skip the `alembic upgrade` here and apply it during deployment (Task 10 verification). The import check still validates the model code.

- [ ] **Step 5: Commit**

Run (from repo root):
```bash
git add sparing_api/app/models/models.py sparing_api/alembic/versions/0006_add_anomaly_detection.py
git commit -m "feat(anomaly): add data_quality alert columns + sensor_health table"
```

---

## Task 6: DB orchestration (`detect_realtime`, `detect_drift_all_sites`)

**Files:**
- Modify: `sparing_api/app/utils/anomaly_engine.py`

This task adds the DB-writing functions. They mirror `app/utils/alert_engine.py` exactly: own session via `SessionLocal`, total `try/except`, dedup before insert. No unit test (no async-DB fixture in repo); verified by the smoke test in Step 3 and end-to-end in Task 7/10.

- [ ] **Step 1: Add orchestration functions**

Add to the top imports of `sparing_api/app/utils/anomaly_engine.py`:
```python
from datetime import datetime, timezone, timedelta
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.logging import logger
```
Append these functions to `sparing_api/app/utils/anomaly_engine.py`:
```python
def _status_for(result: "AnomalyResult | None") -> str:
    if result is None:
        return "ok"
    return "bad" if result.severity == "danger" else "warning"


async def _upsert_health(db, site_id: int, field: str, value, result, now: datetime) -> None:
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


async def _maybe_create_alert(db, site_id, device_uid, field, value, result, now) -> None:
    """Insert a data_quality alert unless an identical one is already active (30-min dedup)."""
    from app.models.models import Alert
    dedup_cutoff = now - timedelta(minutes=30)
    existing = await db.execute(
        select(Alert).where(
            Alert.site_id == site_id,
            Alert.field == field,
            Alert.category == "data_quality",
            Alert.anomaly_type == result.anomaly_type,
            Alert.status == "active",
            Alert.triggered_at >= dedup_cutoff,
        )
    )
    if existing.scalar_one_or_none() is not None:
        return
    db.add(Alert(
        site_id=site_id, device_uid=device_uid, field=field, value=value,
        threshold_type=result.severity, status="active", triggered_at=now,
        category="data_quality", anomaly_type=result.anomaly_type, detail=result.reason,
    ))


async def detect_realtime(site_id: int, site_uid: str, device_uid, reading: dict) -> None:
    """Run implausible/flatline/spike on the latest reading. Own session; never raises."""
    from app.core.db import SessionLocal
    from app.models.models import SensorData
    try:
        async with SessionLocal() as db:
            now = datetime.now(timezone.utc)
            for field in IN_SCOPE_FIELDS:
                raw = reading.get(field)
                if raw is None:
                    continue
                value = float(raw)
                result = check_implausible(field, value)
                if result is None:
                    col = getattr(SensorData, field)
                    rows = (await db.execute(
                        select(SensorData.ts, col).where(
                            SensorData.site_id == site_id,
                            col.isnot(None),
                            SensorData.ts >= now - timedelta(minutes=SPIKE_WINDOW_MINUTES),
                        ).order_by(SensorData.ts.asc())
                    )).all()
                    samples = [(r[0], r[1]) for r in rows]
                    flat_samples = [
                        s for s in samples
                        if s[0] >= now - timedelta(minutes=FLATLINE_MIN_MINUTES)
                    ]
                    result = check_flatline(flat_samples, field)
                    if result is None:
                        history = [v for _, v in samples]
                        result = check_spike(value, history, field)
                await _upsert_health(db, site_id, field, value, result, now)
                if result is not None:
                    await _maybe_create_alert(db, site_id, device_uid, field, value, result, now)
            await db.commit()
    except Exception:
        logger.exception(f"Anomaly realtime detection failed for site {site_uid}")


async def detect_drift_all_sites(db: AsyncSession) -> None:
    """Scheduled drift check across active sites x in-scope fields. Never raises."""
    from app.models.models import Site, SensorData
    try:
        now = datetime.now(timezone.utc)
        recent_cutoff = now - timedelta(hours=DRIFT_RECENT_HOURS)
        baseline_start = now - timedelta(days=DRIFT_BASELINE_DAYS) - timedelta(hours=DRIFT_RECENT_HOURS)
        sites = (await db.execute(select(Site).where(Site.is_active == True))).scalars().all()
        for site in sites:
            for field in IN_SCOPE_FIELDS:
                col = getattr(SensorData, field)
                rows = (await db.execute(
                    select(SensorData.ts, col).where(
                        SensorData.site_id == site.id,
                        col.isnot(None),
                        SensorData.ts >= baseline_start,
                    )
                )).all()
                recent = [v for ts, v in rows if ts >= recent_cutoff]
                baseline = [v for ts, v in rows if ts < recent_cutoff]
                if not recent or not baseline:
                    continue
                result = check_drift(recent, baseline, field)
                if result is not None:
                    last_value = recent[-1]
                    await _upsert_health(db, site.id, field, last_value, result, now)
                    await _maybe_create_alert(db, site.id, None, field, last_value, result, now)
        await db.commit()
    except Exception:
        logger.exception("Anomaly drift detection failed")
```

- [ ] **Step 2: Verify the module imports cleanly**

Run (from `sparing_api/`):
```bash
.venv/Scripts/python.exe -c "import app.utils.anomaly_engine as a; print('ok', a.detect_realtime, a.detect_drift_all_sites)"
```
Expected: `ok <function detect_realtime ...> <function detect_drift_all_sites ...>`.

- [ ] **Step 3: Re-run the unit tests (ensure detectors still pass)**

Run (from `sparing_api/`):
```bash
.venv/Scripts/python.exe -m pytest app/tests/test_anomaly_engine.py -v
```
Expected: 22 passed.

- [ ] **Step 4: Commit**

Run (from repo root):
```bash
git add sparing_api/app/utils/anomaly_engine.py
git commit -m "feat(anomaly): DB orchestration for realtime + drift detection"
```

---

## Task 7: Wire realtime detection into ingest

**Files:**
- Modify: `sparing_api/app/api/routers/getdata.py:12` (import) and `:168-174` (after commit)

- [ ] **Step 1: Add the import**

In `sparing_api/app/api/routers/getdata.py`, after line 12 (`from app.utils.alert_engine import trigger_alerts`), add:
```python
from app.utils.anomaly_engine import detect_realtime
```

- [ ] **Step 2: Fire the detection task after commit**

In `sparing_api/app/api/routers/getdata.py`, locate the existing block (around line 168):
```python
        last_row = rows[-1]
        asyncio.create_task(trigger_alerts(
            site_id=site.id,
            site_uid=uid,
            device_uid=device_id_str,
            data=last_row,
        ))
```
Add immediately after it (still inside the `if rows:` block):
```python
        asyncio.create_task(detect_realtime(
            site_id=site.id,
            site_uid=uid,
            device_uid=device_id_str,
            reading=last_row,
        ))
```

- [ ] **Step 3: Verify the app imports and routes load**

Run (from `sparing_api/`):
```bash
.venv/Scripts/python.exe -c "from app.main import app; print('routes ok', len(app.routes))"
```
Expected: prints a route count, no import error.

- [ ] **Step 4: Smoke test the detector against a DB (manual, optional but recommended)**

Only if a reachable dev/prod DB is configured in `.env`. This inserts a known-implausible reading path by calling the detector directly with a fake reading and a real `site_id`. Create a throwaway script `sparing_api/_smoke_anomaly.py`:
```python
import asyncio
from datetime import datetime, timezone
from app.utils.anomaly_engine import detect_realtime

# Replace 3 with a real site_id; ph=13.9 is implausible (range 2-12)
async def main():
    await detect_realtime(site_id=3, site_uid="PKN-LOG", device_uid="SMOKE",
                          reading={"ph": 13.9, "ts": datetime.now(timezone.utc)})
    print("done")

asyncio.run(main())
```
Run (from `sparing_api/`):
```bash
.venv/Scripts/python.exe _smoke_anomaly.py
```
Then verify a `data_quality` alert + a `sensor_health` row appeared (via your DB client):
```sql
SELECT category, anomaly_type, field, detail FROM alerts WHERE category='data_quality' ORDER BY id DESC LIMIT 3;
SELECT field, status, reason FROM sensor_health WHERE site_id=3;
```
Clean up the throwaway script and test rows:
```bash
rm sparing_api/_smoke_anomaly.py
```
```sql
DELETE FROM alerts WHERE device_uid='SMOKE';
```

- [ ] **Step 5: Commit**

Run (from repo root):
```bash
git add sparing_api/app/api/routers/getdata.py
git commit -m "feat(anomaly): fire realtime detection on ingest in getdata"
```

---

## Task 8: Register the hourly drift job

**Files:**
- Modify: `sparing_api/app/main.py:148-165`

- [ ] **Step 1: Add the drift job wrapper**

In `sparing_api/app/main.py`, after the `_check_offline_devices` function (ends line 157), add:
```python
async def _detect_anomaly_drift():
    """Hourly drift detection across all active sites."""
    from app.core.db import get_db
    from app.utils.anomaly_engine import detect_drift_all_sites
    try:
        async for db in get_db():
            await detect_drift_all_sites(db)
            break
    except Exception:
        logger.exception("Anomaly drift scheduler failed")
```

- [ ] **Step 2: Register the job**

In `sparing_api/app/main.py`, inside `startup_event` (after the `offline_device_check` line 163), add:
```python
    scheduler.add_job(_detect_anomaly_drift, "interval", hours=1, id="anomaly_drift_check")
```

- [ ] **Step 3: Verify the app still imports**

Run (from `sparing_api/`):
```bash
.venv/Scripts/python.exe -c "from app.main import app; print('ok')"
```
Expected: `ok`.

- [ ] **Step 4: Commit**

Run (from repo root):
```bash
git add sparing_api/app/main.py
git commit -m "feat(anomaly): hourly drift detection scheduler job"
```

---

## Task 9: Backend API — expose alert fields + sensor-health endpoint

**Files:**
- Modify: `sparing_api/app/schemas/alert.py:33-45` (AlertOut)
- Modify: `sparing_api/app/api/routers/alerts.py:14-30` (_build_alert_out)
- Create: `sparing_api/app/schemas/sensor_health.py`
- Modify: `sparing_api/app/api/routers/sites.py` (new endpoint + imports)

- [ ] **Step 1: Extend `AlertOut`**

In `sparing_api/app/schemas/alert.py`, add three fields to `class AlertOut` after `acknowledged_by_user_id`:
```python
    category: str = "compliance"
    anomaly_type: str | None = None
    detail: str | None = None
```

- [ ] **Step 2: Populate them in `_build_alert_out`**

In `sparing_api/app/api/routers/alerts.py`, inside `_build_alert_out`, add to the `AlertOut(...)` constructor call (after `acknowledged_by_user_id=alert.acknowledged_by_user_id,`):
```python
        category=getattr(alert, "category", "compliance"),
        anomaly_type=alert.anomaly_type,
        detail=alert.detail,
```

- [ ] **Step 3: Create the sensor-health schema**

Create `sparing_api/app/schemas/sensor_health.py`:
```python
from pydantic import BaseModel
from datetime import datetime


class SensorHealthOut(BaseModel):
    field: str
    status: str
    anomaly_type: str | None = None
    reason: str | None = None
    last_value: float | None = None
    updated_at: datetime | None = None
```

- [ ] **Step 4: Add the endpoint to `sites.py`**

In `sparing_api/app/api/routers/sites.py`, add to the imports at the top (the model import on line 7 and schema import on line 8):
```python
from app.models.models import Site, SensorHealth
from app.schemas.sensor_health import SensorHealthOut
```
(Update the existing `from app.models.models import Site` line to include `SensorHealth`; add the new schema import line.)

Then add this endpoint (place it after the `get_site` function, before `update_site`):
```python
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
```

- [ ] **Step 5: Verify the app imports and the route is registered**

Run (from `sparing_api/`):
```bash
.venv/Scripts/python.exe -c "from app.main import app; print([r.path for r in app.routes if 'sensor-health' in getattr(r,'path','')])"
```
Expected: `['/sites/{uid}/sensor-health']`.

- [ ] **Step 6: Commit**

Run (from repo root):
```bash
git add sparing_api/app/schemas/alert.py sparing_api/app/api/routers/alerts.py sparing_api/app/schemas/sensor_health.py sparing_api/app/api/routers/sites.py
git commit -m "feat(anomaly): expose data_quality alert fields + sensor-health endpoint"
```

---

## Task 10: Frontend — health badge + data_quality alert display

**Files:**
- Modify: `sparing_front/resources/js/Composables/useApi.js:106` (after getSite)
- Modify: `sparing_front/resources/js/Components/SensorCard.vue`
- Modify: `sparing_front/resources/js/Pages/Dashboard/Index.vue`
- Modify: `sparing_front/resources/js/Components/AlertDropdown.vue`

There is no JS test setup in the repo; verification is a production build (`npm run build`).

- [ ] **Step 1: Add the API call**

In `sparing_front/resources/js/Composables/useApi.js`, after the `getSite` line (106), add:
```javascript
  const getSensorHealth = (uid) => request('GET', `/sites/${uid}/sensor-health`);
```
Then add `getSensorHealth,` to the returned object (in the same block where `getSite,` is returned).

- [ ] **Step 2: Add a `health` prop + status dot to `SensorCard.vue`**

In `sparing_front/resources/js/Components/SensorCard.vue`, add to `defineProps` (after `decimals`):
```javascript
  health:    { type: Object,            default: null },
```
Add a computed (after the `accentColor` computed):
```javascript
const healthDot = computed(() => {
  const s = props.health?.status;
  if (s === 'bad')     return { cls: 'bg-rose-500',   title: props.health.reason || 'Sensor bermasalah' };
  if (s === 'warning') return { cls: 'bg-amber-400',  title: props.health.reason || 'Perlu perhatian' };
  if (s === 'ok')      return { cls: 'bg-emerald-500', title: 'Sensor normal' };
  return null;
});
```
In the template, inside the label row, add the dot next to the label. Replace the label `<p>` line:
```html
        <p class="text-[10px] font-bold text-slate-400 uppercase tracking-[0.12em] leading-none">{{ label }}</p>
```
with:
```html
        <div class="flex items-center gap-1.5">
          <span v-if="healthDot" :class="['w-1.5 h-1.5 rounded-full', healthDot.cls]" :title="healthDot.title"></span>
          <p class="text-[10px] font-bold text-slate-400 uppercase tracking-[0.12em] leading-none">{{ label }}</p>
        </div>
```

- [ ] **Step 3: Fetch health in the dashboard and pass to cards**

In `sparing_front/resources/js/Pages/Dashboard/Index.vue`:

(a) Add `getSensorHealth` to the `useApi()` destructure (the line around 336 that lists `getLatestData, getData, getDevices, getSites`):
```javascript
const { getLatestData, getData, getDevices, getSites, getSensorHealth } = useApi();
```

(b) Add state (near the other `ref(...)` declarations, e.g. after `chartData`):
```javascript
const sensorHealth = ref({});  // map: field -> health object
```

(c) Add a loader function (near `loadLatestData`):
```javascript
const loadSensorHealth = async () => {
  if (!currentSite.value) return;
  try {
    const list = await getSensorHealth(currentSite.value.uid);
    const map = {};
    (Array.isArray(list) ? list : []).forEach(h => { map[h.field] = h; });
    sensorHealth.value = map;
  } catch (e) {
    logger.error('Failed to load sensor health:', e);
    sensorHealth.value = {};
  }
};
```

(d) Call it in `onSiteChange` (add to the `Promise.all`) and in `onMounted` (add to its `Promise.all`):
```javascript
    await Promise.all([loadLatestData(), loadDevices(), loadChartData(), loadSensorHealth()]);
```
(apply to both the `onSiteChange` block and the `onMounted` block).

(e) Pass `:health` to each water-quality `SensorCard` in the template. For the six in-scope params, add the prop. Example for pH (line 59) — add `:health="sensorHealth.ph"`:
```html
      <SensorCard label="pH"         :value="latestData?.ph"      icon="fas fa-flask"           icon-class="bg-blue-100 text-blue-600"    :trend="getTrend('ph')"      field="ph"      :decimals="2" :health="sensorHealth.ph" />
```
Do the same for `tss` (`:health="sensorHealth.tss"`), `cod` (`sensorHealth.cod`), `nh3n` (`sensorHealth.nh3n`), `debit` (`sensorHealth.debit`), `temp` (`sensorHealth.temp`). Leave `voltage` and `current` cards unchanged (out of scope).

- [ ] **Step 4: Distinguish `data_quality` alerts in `AlertDropdown.vue`**

In `sparing_front/resources/js/Components/AlertDropdown.vue`, add a helper after `getFieldLabel` (line 96):
```javascript
const ANOMALY_LABELS = {
  implausible: 'Nilai tidak wajar', flatline: 'Sensor nyangkut',
  spike: 'Lonjakan', drift: 'Drift kalibrasi',
};
const isDataQuality = (a) => a.category === 'data_quality';
const getAlertTitle = (a) => isDataQuality(a)
  ? `${getFieldLabel(a.field)} — ${ANOMALY_LABELS[a.anomaly_type] || 'Kualitas data'}`
  : `${getFieldLabel(a.field)}`;
```
In the alert row template, replace the field/value line (lines 52-55):
```html
                <div class="text-sm font-semibold mt-0.5" :class="alert.threshold_type === 'danger' ? 'text-red-600' : 'text-amber-600'">
                  {{ getFieldLabel(alert.field) }}:
                  <span class="font-mono">{{ alert.field === 'device_offline' ? 'Offline' : formatAlertValue(alert) }}</span>
                </div>
```
with:
```html
                <div class="text-sm font-semibold mt-0.5" :class="alert.threshold_type === 'danger' ? 'text-red-600' : 'text-amber-600'">
                  <i v-if="isDataQuality(alert)" class="fas fa-wrench text-[10px] mr-1"></i>
                  {{ getAlertTitle(alert) }}:
                  <span class="font-mono">{{ alert.field === 'device_offline' ? 'Offline' : formatAlertValue(alert) }}</span>
                </div>
                <div v-if="isDataQuality(alert) && alert.detail" class="text-[11px] text-slate-400 mt-0.5">{{ alert.detail }}</div>
```

- [ ] **Step 5: Build the frontend to verify no errors**

Run (from `sparing_front/`):
```bash
npm run build
```
Expected: build succeeds, emits `dist/assets/index-*.js`.

- [ ] **Step 6: Commit**

Run (from repo root):
```bash
git add sparing_front/resources/js/Composables/useApi.js sparing_front/resources/js/Components/SensorCard.vue sparing_front/resources/js/Pages/Dashboard/Index.vue sparing_front/resources/js/Components/AlertDropdown.vue
git commit -m "feat(anomaly): sensor health badge + data_quality alert display"
```

---

## Deployment notes (run after all tasks; not part of task commits)

Per project memory (`project_deployment.md`): production has a git repo at `/opt/sparing/repo` and a separate gunicorn deployment at `/opt/sparing/api`. To ship:

1. Apply the migration on the server DB: from the deployment dir, `.venv/.../python -m alembic upgrade head` (or the project's existing migration step).
2. Sync the API code to `/opt/sparing/api` and `sudo systemctl restart sparing-api.service`.
3. Build the frontend (`npm run build`) and rsync `dist/` to `/var/www/sparing/frontend/`.

---

## Self-Review Notes

- **Spec coverage:** implausible (Task 1), flatline (Task 2), spike (Task 3), drift (Task 4), `data_quality` alert category + `sensor_health` table (Task 5/6), realtime hook in getdata (Task 7), hourly drift job (Task 8), sensor-health API + alert fields (Task 9), dashboard badge + bell display, no email (Task 10). `score` column reserved (Task 5). voltage/current excluded throughout. All spec sections mapped.
- **Type consistency:** `AnomalyResult(anomaly_type, severity, reason)` used identically across Tasks 1-6; `SensorHealth` columns match between model (Task 5), migration (Task 5), orchestration (Task 6), and schema/endpoint (Task 9); `AlertOut` fields match the model columns added in Task 5.
- **No email** is built (deferred per spec). Detection is stdlib-only (no numpy/pandas added).
