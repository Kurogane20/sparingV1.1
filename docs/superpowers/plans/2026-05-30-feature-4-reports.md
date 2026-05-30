# Feature 4: Regulatory Report Generator — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Generate formatted compliance reports for KLHK regulatory submission — per site, per period — with parameter statistics, violation lists, trend analysis, and PDF/Excel export.

**Architecture:** A new `GET /reports/generate` endpoint aggregates `SensorData` using SQL for performance (one query per parameter + one daily-summary query + one violations query), sourcing baku mutu limits from `AlertRule` table (Feature 1) with fallback to system defaults. The frontend shows a form → preview in a single page (`/reports`), reuses existing jsPDF for PDF export, and adds `xlsx` for Excel. No new DB tables or migrations needed.

**Tech Stack:** FastAPI + SQLAlchemy async SQL aggregation · Vue 3 + jsPDF (already installed) + xlsx (new)

---

## File Map

### Backend — Create
- `sparing_api/app/schemas/report.py` — Pydantic schemas for report response
- `sparing_api/app/utils/report_helpers.py` — pure helper functions (period label, trend, compliance)
- `sparing_api/app/api/routers/reports.py` — `GET /reports/generate` endpoint
- `sparing_api/app/tests/test_report_helpers.py` — unit tests for helper functions

### Backend — Modify
- `sparing_api/app/main.py` — register reports router

### Frontend — Create
- `sparing_front/resources/js/Pages/Reports/Index.vue` — full reports page

### Frontend — Modify
- `sparing_front/package.json` — add `xlsx` dependency
- `sparing_front/resources/js/app.js` — add `/reports` route
- `sparing_front/resources/js/Components/Sidebar.vue` — add Laporan menu item
- `sparing_front/resources/js/Components/Header.vue` — add `/reports` page title
- `sparing_front/resources/js/Composables/useApi.js` — add `generateReport` method

---

## Task 1: Backend schemas + helper functions with tests

**Files:**
- Create: `sparing_api/app/schemas/report.py`
- Create: `sparing_api/app/utils/report_helpers.py`
- Create: `sparing_api/app/tests/test_report_helpers.py`

- [ ] **Step 1: Write failing tests**

Create `sparing_api/app/tests/test_report_helpers.py`:

```python
from datetime import date
from app.utils.report_helpers import make_period_label, calculate_trend, compliance_pct

def test_period_label_full_month():
    assert make_period_label(date(2025, 1, 1), date(2025, 1, 31)) == "Januari 2025"

def test_period_label_custom_range():
    result = make_period_label(date(2025, 1, 5), date(2025, 1, 20))
    assert "5 Jan" in result and "20 Jan" in result

def test_trend_stable():
    assert calculate_trend(7.0, 7.2) == "stable"

def test_trend_increasing():
    assert calculate_trend(5.0, 7.0) == "increasing"

def test_trend_decreasing():
    assert calculate_trend(7.0, 5.0) == "decreasing"

def test_trend_zero_base():
    assert calculate_trend(0, 5.0) == "stable"

def test_trend_none():
    assert calculate_trend(None, 5.0) == "stable"

def test_compliance_full():
    assert compliance_pct(100, 0) == 100.0

def test_compliance_partial():
    assert compliance_pct(10, 2) == 80.0

def test_compliance_zero_total():
    assert compliance_pct(0, 0) == 100.0
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
cd sparing_api && python -m pytest app/tests/test_report_helpers.py -v
```

Expected: `ImportError`

- [ ] **Step 3: Create helper utilities**

Create `sparing_api/app/utils/report_helpers.py`:

```python
from datetime import date

MONTH_NAMES = [
    "Januari","Februari","Maret","April","Mei","Juni",
    "Juli","Agustus","September","Oktober","November","Desember",
]

SYSTEM_BAKU_MUTU = {
    "ph":    {"warning_min": 6.5, "warning_max": 8.5, "danger_min": 6.0, "danger_max": 9.0, "unit": ""},
    "tss":   {"warning_min": None, "warning_max": 150,  "danger_min": None, "danger_max": 200,  "unit": "mg/L"},
    "cod":   {"warning_min": None, "warning_max": 200,  "danger_min": None, "danger_max": 300,  "unit": "mg/L"},
    "nh3n":  {"warning_min": None, "warning_max": 7,    "danger_min": None, "danger_max": 10,   "unit": "mg/L"},
    "debit": {"warning_min": 0,    "warning_max": None, "danger_min": 0,    "danger_max": None, "unit": "L/min"},
    "temp":  {"warning_min": None, "warning_max": 30,   "danger_min": None, "danger_max": 35,   "unit": "°C"},
}

PARAM_LABELS = {
    "ph": "pH", "tss": "TSS", "cod": "COD",
    "nh3n": "NH3-N", "debit": "Debit", "temp": "Temperatur",
}

REPORT_PARAMS = ["ph", "tss", "cod", "nh3n", "debit", "temp"]


def make_period_label(from_date: date, to_date: date) -> str:
    """Return 'Januari 2025' for a full calendar month, else '5 Jan – 20 Jan 2025'."""
    import calendar
    last_day = calendar.monthrange(from_date.year, from_date.month)[1]
    if from_date.day == 1 and to_date.day == last_day and from_date.month == to_date.month and from_date.year == to_date.year:
        return f"{MONTH_NAMES[from_date.month - 1]} {from_date.year}"
    mn = MONTH_NAMES[from_date.month - 1][:3]
    mn2 = MONTH_NAMES[to_date.month - 1][:3]
    return f"{from_date.day} {mn} – {to_date.day} {mn2} {to_date.year}"


def calculate_trend(avg_first: float | None, avg_second: float | None) -> str:
    """Return 'stable', 'increasing', or 'decreasing' based on half-period comparison."""
    if avg_first is None or avg_second is None:
        return "stable"
    if avg_first == 0:
        return "stable"
    change_pct = ((avg_second - avg_first) / abs(avg_first)) * 100
    if abs(change_pct) < 5:
        return "stable"
    return "increasing" if change_pct > 0 else "decreasing"


def compliance_pct(total_with_value: int, violation_count: int) -> float:
    """Return compliance percentage given total valid readings and violation count."""
    if total_with_value == 0:
        return 100.0
    compliant = total_with_value - violation_count
    return round(compliant / total_with_value * 100, 1)


def get_baku_mutu(field: str, alert_rule) -> dict:
    """Return baku mutu dict for a field, preferring AlertRule over system defaults."""
    default = SYSTEM_BAKU_MUTU.get(field, {})
    if alert_rule:
        return {
            "min": alert_rule.danger_min,
            "max": alert_rule.danger_max,
            "unit": default.get("unit", ""),
        }
    return {
        "min": default.get("danger_min"),
        "max": default.get("danger_max"),
        "unit": default.get("unit", ""),
    }


def overall_status(compliance: float) -> str:
    if compliance >= 90:
        return "good"
    if compliance >= 70:
        return "warning"
    return "danger"
```

- [ ] **Step 4: Run tests — confirm they pass**

```bash
cd sparing_api && python -m pytest app/tests/test_report_helpers.py -v
```

Expected: 10 tests pass.

- [ ] **Step 5: Create schema file**

Create `sparing_api/app/schemas/report.py`:

```python
from pydantic import BaseModel
from datetime import datetime

class BakuMutuOut(BaseModel):
    min: float | None
    max: float | None
    unit: str

class StatsOut(BaseModel):
    avg: float | None
    min: float | None
    max: float | None
    std_dev: float | None
    count: int

class ParameterReportOut(BaseModel):
    field: str
    label: str
    baku_mutu: BakuMutuOut
    stats: StatsOut
    compliance_pct: float
    violation_count: int
    trend: str

class DailySummaryOut(BaseModel):
    date: str  # YYYY-MM-DD
    ph_avg: float | None = None
    tss_avg: float | None = None
    cod_avg: float | None = None
    nh3n_avg: float | None = None
    debit_avg: float | None = None
    temp_avg: float | None = None

class ViolationOut(BaseModel):
    ts: datetime
    field: str
    value: float
    limit_type: str  # above_max | below_min
    limit: float

class ReportSummaryOut(BaseModel):
    total_records: int
    compliance_overall: float
    overall_status: str

class ReportOut(BaseModel):
    site: dict
    period: dict
    generated_at: datetime
    summary: ReportSummaryOut
    parameters: list[ParameterReportOut]
    daily_summary: list[DailySummaryOut]
    violations: list[ViolationOut]
```

- [ ] **Step 6: Verify imports**

```bash
cd sparing_api && python -c "from app.schemas.report import ReportOut; from app.utils.report_helpers import make_period_label; print('OK')"
```

Expected: `OK`

- [ ] **Step 7: Commit**

```bash
git add sparing_api/app/schemas/report.py sparing_api/app/utils/report_helpers.py sparing_api/app/tests/test_report_helpers.py
git commit -m "feat: add report schemas and helper utilities with tests"
```

---

## Task 2: Backend reports router + registration

**Files:**
- Create: `sparing_api/app/api/routers/reports.py`
- Modify: `sparing_api/app/main.py`

- [ ] **Step 1: Create reports.py router**

Create `sparing_api/app/api/routers/reports.py`:

```python
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, text
from datetime import datetime, timezone, date, timedelta

from app.core.db import get_db
from app.api.deps import get_current_user, get_viewer_site_uids
from app.models.models import Site, SensorData, AlertRule
from app.schemas.report import (
    ReportOut, ReportSummaryOut, ParameterReportOut, DailySummaryOut,
    ViolationOut, BakuMutuOut, StatsOut,
)
from app.utils.report_helpers import (
    make_period_label, calculate_trend, compliance_pct,
    get_baku_mutu, overall_status, REPORT_PARAMS, PARAM_LABELS,
)

router = APIRouter()


@router.get("/generate", response_model=ReportOut)
async def generate_report(
    site_uid: str = Query(...),
    period_from: str = Query(..., description="YYYY-MM-DD"),
    period_to: str = Query(..., description="YYYY-MM-DD"),
    db: AsyncSession = Depends(get_db),
    _user=Depends(get_current_user),
    viewer_uids: list[str] = Depends(get_viewer_site_uids),
):
    # Site lookup
    site = (await db.execute(select(Site).where(Site.uid == site_uid))).scalar_one_or_none()
    if not site:
        raise HTTPException(404, "Site not found")

    # Viewer site access check
    if viewer_uids and site_uid not in viewer_uids:
        raise HTTPException(403, "Forbidden")

    # Parse dates
    try:
        from_date = date.fromisoformat(period_from)
        to_date = date.fromisoformat(period_to)
    except ValueError:
        raise HTTPException(400, "Invalid date format. Use YYYY-MM-DD")

    from_dt = datetime(from_date.year, from_date.month, from_date.day, 0, 0, 0, tzinfo=timezone.utc)
    to_dt = datetime(to_date.year, to_date.month, to_date.day, 23, 59, 59, tzinfo=timezone.utc)
    mid_dt = from_dt + (to_dt - from_dt) / 2

    # Load alert rules for this site (for baku mutu limits)
    rules_result = await db.execute(
        select(AlertRule).where(AlertRule.site_id == site.id, AlertRule.is_active == True)
    )
    rules_by_field = {r.field: r for r in rules_result.scalars().all()}

    # Total records in period
    total_records = (await db.execute(
        select(func.count(SensorData.id)).where(
            SensorData.site_id == site.id,
            SensorData.ts.between(from_dt, to_dt),
        )
    )).scalar_one() or 0

    # Per-parameter stats
    parameters = []
    all_compliance = []

    for field in REPORT_PARAMS:
        col = getattr(SensorData, field)
        bm_rule = rules_by_field.get(field)
        bm = get_baku_mutu(field, bm_rule)

        # Full-period stats
        stats_row = (await db.execute(
            select(
                func.avg(col),
                func.min(col),
                func.max(col),
                func.count(col),
                func.stddev_pop(col),
            ).where(
                SensorData.site_id == site.id,
                SensorData.ts.between(from_dt, to_dt),
                col.isnot(None),
            )
        )).one()

        avg_val, min_val, max_val, count_val, stddev_val = stats_row
        count_val = count_val or 0

        # Trend: first half vs second half average
        avg_first = (await db.execute(
            select(func.avg(col)).where(
                SensorData.site_id == site.id,
                SensorData.ts.between(from_dt, mid_dt),
                col.isnot(None),
            )
        )).scalar_one_or_none()

        avg_second = (await db.execute(
            select(func.avg(col)).where(
                SensorData.site_id == site.id,
                SensorData.ts.between(mid_dt, to_dt),
                col.isnot(None),
            )
        )).scalar_one_or_none()

        trend = calculate_trend(float(avg_first) if avg_first else None, float(avg_second) if avg_second else None)

        # Violation count for this field
        viol_count = 0
        if count_val > 0:
            viol_filter = _build_violation_filter(col, bm)
            if viol_filter is not None:
                viol_count = (await db.execute(
                    select(func.count(SensorData.id)).where(
                        SensorData.site_id == site.id,
                        SensorData.ts.between(from_dt, to_dt),
                        col.isnot(None),
                        viol_filter,
                    )
                )).scalar_one() or 0

        cpct = compliance_pct(count_val, viol_count)
        all_compliance.append(cpct)

        parameters.append(ParameterReportOut(
            field=field,
            label=PARAM_LABELS[field],
            baku_mutu=BakuMutuOut(min=bm["min"], max=bm["max"], unit=bm["unit"]),
            stats=StatsOut(
                avg=round(float(avg_val), 3) if avg_val is not None else None,
                min=round(float(min_val), 3) if min_val is not None else None,
                max=round(float(max_val), 3) if max_val is not None else None,
                std_dev=round(float(stddev_val), 3) if stddev_val is not None else None,
                count=count_val,
            ),
            compliance_pct=cpct,
            violation_count=viol_count,
            trend=trend,
        ))

    # Overall compliance
    overall_compliance = round(sum(all_compliance) / len(all_compliance), 1) if all_compliance else 100.0

    # Daily summary
    daily_rows = (await db.execute(
        select(
            func.date(SensorData.ts).label("day"),
            func.avg(SensorData.ph).label("ph_avg"),
            func.avg(SensorData.tss).label("tss_avg"),
            func.avg(SensorData.cod).label("cod_avg"),
            func.avg(SensorData.nh3n).label("nh3n_avg"),
            func.avg(SensorData.debit).label("debit_avg"),
            func.avg(SensorData.temp).label("temp_avg"),
        ).where(
            SensorData.site_id == site.id,
            SensorData.ts.between(from_dt, to_dt),
        ).group_by(func.date(SensorData.ts))
        .order_by(func.date(SensorData.ts))
    )).all()

    daily_summary = [
        DailySummaryOut(
            date=str(row.day),
            ph_avg=round(float(row.ph_avg), 2) if row.ph_avg is not None else None,
            tss_avg=round(float(row.tss_avg), 2) if row.tss_avg is not None else None,
            cod_avg=round(float(row.cod_avg), 2) if row.cod_avg is not None else None,
            nh3n_avg=round(float(row.nh3n_avg), 2) if row.nh3n_avg is not None else None,
            debit_avg=round(float(row.debit_avg), 2) if row.debit_avg is not None else None,
            temp_avg=round(float(row.temp_avg), 2) if row.temp_avg is not None else None,
        )
        for row in daily_rows
    ]

    # Violations (max 200 rows, most recent first)
    violations = []
    for field in REPORT_PARAMS:
        col = getattr(SensorData, field)
        bm = get_baku_mutu(field, rules_by_field.get(field))
        viol_filter = _build_violation_filter(col, bm)
        if viol_filter is None:
            continue
        viol_rows = (await db.execute(
            select(SensorData.ts, col.label("value")).where(
                SensorData.site_id == site.id,
                SensorData.ts.between(from_dt, to_dt),
                col.isnot(None),
                viol_filter,
            ).order_by(SensorData.ts.desc()).limit(50)
        )).all()
        for row in viol_rows:
            if bm["max"] is not None and float(row.value) > bm["max"]:
                violations.append(ViolationOut(
                    ts=row.ts, field=field, value=round(float(row.value), 3),
                    limit_type="above_max", limit=bm["max"],
                ))
            elif bm["min"] is not None and float(row.value) < bm["min"]:
                violations.append(ViolationOut(
                    ts=row.ts, field=field, value=round(float(row.value), 3),
                    limit_type="below_min", limit=bm["min"],
                ))

    violations.sort(key=lambda v: v.ts, reverse=True)
    violations = violations[:200]

    return ReportOut(
        site={"uid": site.uid, "name": site.name, "company_name": site.company_name},
        period={
            "from": period_from,
            "to": period_to,
            "label": make_period_label(from_date, to_date),
        },
        generated_at=datetime.now(timezone.utc),
        summary=ReportSummaryOut(
            total_records=total_records,
            compliance_overall=overall_compliance,
            overall_status=overall_status(overall_compliance),
        ),
        parameters=parameters,
        daily_summary=daily_summary,
        violations=violations,
    )


def _build_violation_filter(col, bm: dict):
    """Build SQLAlchemy WHERE clause for values outside baku mutu limits."""
    from sqlalchemy import or_, and_
    conditions = []
    if bm.get("max") is not None:
        conditions.append(col > bm["max"])
    if bm.get("min") is not None:
        conditions.append(col < bm["min"])
    if not conditions:
        return None
    return or_(*conditions)
```

- [ ] **Step 2: Register router in main.py**

Read `sparing_api/app/main.py`. Change the import line:
```python
from app.api.routers import auth, sites, devices, ingest, data, metrics, admin, getdata, alerts, alert_rules
```
to:
```python
from app.api.routers import auth, sites, devices, ingest, data, metrics, admin, getdata, alerts, alert_rules, reports
```

After `app.include_router(alert_rules.router, ...)`, add:
```python
app.include_router(reports.router, prefix="/reports", tags=["Reports"])
```

- [ ] **Step 3: Verify**

```bash
cd sparing_api && python -c "from app.api.routers.reports import router; print('OK')"
```

Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add sparing_api/app/api/routers/reports.py sparing_api/app/main.py
git commit -m "feat: add reports router with GET /reports/generate endpoint"
```

---

## Task 3: Frontend routing, sidebar, header, useApi

**Files:**
- Modify: `sparing_front/package.json` (add xlsx)
- Modify: `sparing_front/resources/js/app.js`
- Modify: `sparing_front/resources/js/Components/Sidebar.vue`
- Modify: `sparing_front/resources/js/Components/Header.vue`
- Modify: `sparing_front/resources/js/Composables/useApi.js`

- [ ] **Step 1: Install xlsx package**

```bash
cd sparing_front && npm install xlsx
```

Expected: xlsx added to node_modules, package.json updated.

- [ ] **Step 2: Add route to app.js**

Read `sparing_front/resources/js/app.js`.

Add import after the existing page imports:
```javascript
import Reports from './Pages/Reports/Index.vue';
```

Add route after the `/history` route:
```javascript
    {
      path: '/reports',
      name: 'reports',
      component: Reports,
      meta: { requiresAuth: true },
    },
```

- [ ] **Step 3: Add Laporan menu item to Sidebar.vue**

Read `sparing_front/resources/js/Components/Sidebar.vue`.

In `allMenuItems`, add after the Analytics item (`path: '/analytics'`):
```javascript
  { path: '/reports',   icon: 'fas fa-file-alt',       label: 'Laporan',      roles: ['admin','operator','viewer'] },
```

- [ ] **Step 4: Add page title to Header.vue**

Read `sparing_front/resources/js/Components/Header.vue`.

In the `pageTitles` object, add:
```javascript
  '/reports': 'Laporan Regulasi',
```

- [ ] **Step 5: Add generateReport to useApi.js**

Read `sparing_front/resources/js/Composables/useApi.js`.

After the device health/maintenance methods and before `return {`, add:
```javascript
  // Reports
  const generateReport = (params) => request('GET', '/reports/generate', null, { params });
```

Add to return object:
```javascript
    // Reports
    generateReport,
```

- [ ] **Step 6: Create empty Reports page stub**

Create `sparing_front/resources/js/Pages/Reports/Index.vue`:

```vue
<template>
  <AppLayout>
    <div class="space-y-6">
      <div>
        <h2 class="text-xl font-bold text-slate-800">Laporan Regulasi</h2>
        <p class="text-slate-500 text-sm mt-0.5">Generate laporan kepatuhan baku mutu untuk pelaporan KLHK</p>
      </div>
      <div class="card p-6 text-center text-slate-400">
        <i class="fas fa-file-alt text-4xl mb-3 block"></i>
        <p>Halaman laporan sedang dimuat...</p>
      </div>
    </div>
  </AppLayout>
</template>

<script setup>
import AppLayout from '@/Layouts/AppLayout.vue';
</script>
```

- [ ] **Step 7: Commit**

```bash
git add sparing_front/package.json sparing_front/package-lock.json sparing_front/resources/js/app.js sparing_front/resources/js/Components/Sidebar.vue sparing_front/resources/js/Components/Header.vue sparing_front/resources/js/Composables/useApi.js sparing_front/resources/js/Pages/Reports/Index.vue
git commit -m "feat: add Reports route, sidebar item, useApi method, xlsx package"
```

---

## Task 4: Reports page — full implementation with form, preview, and export

**Files:**
- Modify: `sparing_front/resources/js/Pages/Reports/Index.vue`

- [ ] **Step 1: Replace stub with full Reports page**

Overwrite `sparing_front/resources/js/Pages/Reports/Index.vue` with:

```vue
<template>
  <AppLayout>
    <div class="space-y-6">
      <!-- Page Header -->
      <div class="flex justify-between items-center">
        <div>
          <h2 class="text-xl font-bold text-slate-800">Laporan Regulasi</h2>
          <p class="text-slate-500 text-sm mt-0.5">Generate laporan kepatuhan baku mutu untuk pelaporan KLHK</p>
        </div>
        <div v-if="report" class="flex gap-2">
          <button @click="exportExcel" class="btn-secondary flex items-center gap-2 text-sm" style="color:#059669;border-color:#6ee7b7;">
            <i class="fas fa-file-excel"></i>Excel
          </button>
          <button @click="exportPdf" :disabled="exportingPdf" class="btn-primary flex items-center gap-2 text-sm disabled:opacity-50">
            <i :class="exportingPdf ? 'fas fa-spinner fa-spin' : 'fas fa-file-pdf'"></i>
            {{ exportingPdf ? 'Mengunduh...' : 'PDF' }}
          </button>
        </div>
      </div>

      <!-- Form Card -->
      <div class="card p-5 md:p-6">
        <h3 class="card-title mb-4">Parameter Laporan</h3>
        <div class="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
          <div>
            <label class="block text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1.5">Lokasi</label>
            <select v-model="form.siteUid" class="form-input text-sm">
              <option value="">Pilih Lokasi</option>
              <option v-for="site in sites" :key="site.uid" :value="site.uid">{{ site.name }} — {{ site.company_name }}</option>
            </select>
          </div>
          <div>
            <label class="block text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1.5">Tipe Periode</label>
            <select v-model="form.periodType" class="form-input text-sm">
              <option value="monthly">Bulanan</option>
              <option value="custom">Custom</option>
            </select>
          </div>
          <div v-if="form.periodType === 'monthly'" class="grid grid-cols-2 gap-2">
            <div>
              <label class="block text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1.5">Bulan</label>
              <select v-model="form.month" class="form-input text-sm">
                <option v-for="(m, i) in MONTHS" :key="i" :value="i+1">{{ m }}</option>
              </select>
            </div>
            <div>
              <label class="block text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1.5">Tahun</label>
              <select v-model="form.year" class="form-input text-sm">
                <option v-for="y in years" :key="y" :value="y">{{ y }}</option>
              </select>
            </div>
          </div>
          <div v-else class="grid grid-cols-2 gap-2">
            <div>
              <label class="block text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1.5">Dari</label>
              <input v-model="form.dateFrom" type="date" class="form-input text-sm" />
            </div>
            <div>
              <label class="block text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1.5">Sampai</label>
              <input v-model="form.dateTo" type="date" class="form-input text-sm" />
            </div>
          </div>
        </div>
        <button @click="generateReport" :disabled="loading || !form.siteUid" class="btn-primary text-sm disabled:opacity-50 flex items-center gap-2">
          <i :class="loading ? 'fas fa-spinner fa-spin' : 'fas fa-chart-bar'" class="text-xs"></i>
          {{ loading ? 'Memproses...' : 'Generate Laporan' }}
        </button>
      </div>

      <!-- Report Preview -->
      <div v-if="report" ref="reportRef" class="space-y-5">
        <!-- Report Header -->
        <div class="card p-6 text-center border-t-4 border-primary">
          <div class="text-xs text-slate-400 uppercase tracking-widest mb-1">Laporan Pemantauan Kualitas Air Limbah</div>
          <h2 class="text-lg font-bold text-slate-800">{{ report.site.company_name }}</h2>
          <p class="text-slate-600 font-medium">{{ report.site.name }}</p>
          <div class="flex items-center justify-center gap-4 mt-3 text-xs text-slate-400 font-mono">
            <span>Periode: {{ report.period.label }}</span>
            <span>·</span>
            <span>Dibuat: {{ new Date(report.generated_at).toLocaleDateString('id-ID', { day: '2-digit', month: 'long', year: 'numeric' }) }}</span>
          </div>
        </div>

        <!-- Ringkasan Kepatuhan -->
        <div class="card p-5">
          <h3 class="card-title mb-4">Ringkasan Kepatuhan</h3>
          <div class="grid grid-cols-3 gap-4 mb-4">
            <div class="text-center p-4 rounded-xl" :class="statusBgClass(report.summary.overall_status)">
              <div class="text-3xl font-bold font-mono" :class="statusTextClass(report.summary.overall_status)">
                {{ report.summary.compliance_overall }}%
              </div>
              <div class="text-xs mt-1 font-semibold uppercase tracking-wide" :class="statusTextClass(report.summary.overall_status)">
                {{ statusLabel(report.summary.overall_status) }}
              </div>
            </div>
            <div class="text-center p-4 rounded-xl bg-slate-50">
              <div class="text-3xl font-bold font-mono text-slate-800">{{ report.summary.total_records.toLocaleString('id-ID') }}</div>
              <div class="text-xs text-slate-400 mt-1">Total Data</div>
            </div>
            <div class="text-center p-4 rounded-xl bg-slate-50">
              <div class="text-3xl font-bold font-mono text-slate-800">{{ report.violations.length }}</div>
              <div class="text-xs text-slate-400 mt-1">Pelanggaran</div>
            </div>
          </div>
          <!-- Compliance bar -->
          <div class="h-2 bg-slate-100 rounded-full overflow-hidden">
            <div class="h-full rounded-full transition-all duration-500" :class="statusBgBarClass(report.summary.overall_status)"
              :style="{ width: report.summary.compliance_overall + '%' }"></div>
          </div>
        </div>

        <!-- Tabel Hasil Pengukuran -->
        <div class="card overflow-hidden">
          <div class="px-5 py-4 border-b border-slate-100">
            <h3 class="card-title">Tabel Hasil Pengukuran</h3>
          </div>
          <div class="overflow-x-auto">
            <table class="w-full text-sm">
              <thead class="bg-slate-50">
                <tr>
                  <th class="text-left px-4 py-3 text-[10px] font-bold text-slate-500 uppercase tracking-wider">Parameter</th>
                  <th class="text-center px-4 py-3 text-[10px] font-bold text-slate-500 uppercase tracking-wider">Baku Mutu</th>
                  <th class="text-right px-4 py-3 text-[10px] font-bold text-slate-500 uppercase tracking-wider">Min</th>
                  <th class="text-right px-4 py-3 text-[10px] font-bold text-slate-500 uppercase tracking-wider">Rata-Rata</th>
                  <th class="text-right px-4 py-3 text-[10px] font-bold text-slate-500 uppercase tracking-wider">Maks</th>
                  <th class="text-right px-4 py-3 text-[10px] font-bold text-slate-500 uppercase tracking-wider">Kepatuhan</th>
                  <th class="text-center px-4 py-3 text-[10px] font-bold text-slate-500 uppercase tracking-wider">Tren</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-slate-50">
                <tr v-for="p in report.parameters" :key="p.field" class="hover:bg-blue-50/30">
                  <td class="px-4 py-3 font-semibold text-slate-800">
                    {{ p.label }}
                    <span class="text-[10px] text-slate-400 font-mono ml-1">{{ p.baku_mutu.unit }}</span>
                  </td>
                  <td class="px-4 py-3 text-center text-xs font-mono text-slate-600">
                    <span v-if="p.baku_mutu.min !== null && p.baku_mutu.max !== null">{{ p.baku_mutu.min }} – {{ p.baku_mutu.max }}</span>
                    <span v-else-if="p.baku_mutu.max !== null">≤ {{ p.baku_mutu.max }}</span>
                    <span v-else-if="p.baku_mutu.min !== null">≥ {{ p.baku_mutu.min }}</span>
                    <span v-else>—</span>
                  </td>
                  <td class="px-4 py-3 text-right font-mono text-slate-700">{{ p.stats.min !== null ? p.stats.min.toFixed(2) : '—' }}</td>
                  <td class="px-4 py-3 text-right font-mono font-semibold text-slate-800">{{ p.stats.avg !== null ? p.stats.avg.toFixed(2) : '—' }}</td>
                  <td class="px-4 py-3 text-right font-mono text-slate-700">{{ p.stats.max !== null ? p.stats.max.toFixed(2) : '—' }}</td>
                  <td class="px-4 py-3 text-right">
                    <span :class="['font-bold font-mono text-sm', p.compliance_pct >= 90 ? 'text-emerald-600' : p.compliance_pct >= 70 ? 'text-amber-500' : 'text-red-500']">
                      {{ p.compliance_pct }}%
                    </span>
                  </td>
                  <td class="px-4 py-3 text-center">
                    <span class="text-xs font-semibold" :class="trendClass(p.trend)">
                      <i :class="trendIcon(p.trend)"></i>
                      {{ trendLabel(p.trend) }}
                    </span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <!-- Grafik Tren -->
        <div class="card p-5">
          <h3 class="card-title mb-4">Grafik Tren Harian</h3>
          <VueApexCharts
            v-if="trendChartOptions && report.daily_summary.length"
            type="line"
            height="280"
            :options="trendChartOptions"
            :series="trendChartSeries"
          />
          <div v-else class="text-center text-sm text-slate-400 py-6">Tidak ada data harian untuk ditampilkan.</div>
        </div>

        <!-- Daftar Pelanggaran -->
        <div v-if="report.violations.length" class="card overflow-hidden">
          <div class="px-5 py-4 border-b border-slate-100 flex items-center justify-between">
            <h3 class="card-title">Daftar Pelanggaran</h3>
            <span class="text-xs font-mono text-slate-400">{{ report.violations.length }} kejadian</span>
          </div>
          <div class="overflow-x-auto max-h-64 overflow-y-auto">
            <table class="w-full text-sm">
              <thead class="bg-slate-50 sticky top-0">
                <tr>
                  <th class="text-left px-4 py-2.5 text-[10px] font-bold text-slate-500 uppercase tracking-wider">Waktu</th>
                  <th class="text-left px-4 py-2.5 text-[10px] font-bold text-slate-500 uppercase tracking-wider">Parameter</th>
                  <th class="text-right px-4 py-2.5 text-[10px] font-bold text-slate-500 uppercase tracking-wider">Nilai</th>
                  <th class="text-right px-4 py-2.5 text-[10px] font-bold text-slate-500 uppercase tracking-wider">Batas</th>
                  <th class="text-center px-4 py-2.5 text-[10px] font-bold text-slate-500 uppercase tracking-wider">Jenis</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-slate-50">
                <tr v-for="v in report.violations" :key="`${v.ts}-${v.field}`" class="hover:bg-red-50/20">
                  <td class="px-4 py-2 font-mono text-xs text-slate-500">{{ new Date(v.ts).toLocaleString('id-ID', { dateStyle: 'short', timeStyle: 'short' }) }}</td>
                  <td class="px-4 py-2 font-semibold text-slate-700">{{ PARAM_LABELS[v.field] || v.field }}</td>
                  <td class="px-4 py-2 text-right font-mono text-red-600 font-bold">{{ v.value.toFixed(2) }}</td>
                  <td class="px-4 py-2 text-right font-mono text-slate-500">{{ v.limit.toFixed(2) }}</td>
                  <td class="px-4 py-2 text-center">
                    <span :class="['text-[10px] font-bold px-2 py-0.5 rounded uppercase', v.limit_type === 'above_max' ? 'bg-red-50 text-red-700' : 'bg-amber-50 text-amber-700']">
                      {{ v.limit_type === 'above_max' ? 'Melewati' : 'Di bawah' }}
                    </span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
        <div v-else class="card p-4 text-center text-sm text-emerald-600 font-semibold">
          <i class="fas fa-check-circle mr-2"></i>Tidak ada pelanggaran baku mutu pada periode ini.
        </div>

        <!-- Rekomendasi -->
        <div class="card p-5">
          <h3 class="card-title mb-4">Rekomendasi</h3>
          <div class="space-y-2">
            <div v-for="(rec, i) in recommendations" :key="i"
              :class="['flex items-start gap-3 p-3 rounded-lg text-sm', recBgClass(rec.type)]">
              <i :class="['shrink-0 mt-0.5', recIcon(rec.type)]"></i>
              <span>{{ rec.text }}</span>
            </div>
            <div v-if="!recommendations.length" class="text-sm text-slate-400 text-center py-2">
              Semua parameter dalam kondisi baik.
            </div>
          </div>
        </div>
      </div>
    </div>
  </AppLayout>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { jsPDF } from 'jspdf';
import * as XLSX from 'xlsx';
import VueApexCharts from 'vue3-apexcharts';
import AppLayout from '@/Layouts/AppLayout.vue';
import { useApi } from '@/Composables/useApi';
import { useAuth } from '@/Composables/useAuth';
import { useToast } from '@/Composables/useToast';
import { formatNumber } from '@/Utils/helpers';
import { generateRecommendations, calculateTrend, calculateCompliance, calculateStats, detectAnomalies } from '@/Utils/analysis';

const { getSites, generateReport: apiGenerateReport } = useApi();
const { filterSitesByUser } = useAuth();
const toast = useToast();

const MONTHS = ['Januari','Februari','Maret','April','Mei','Juni','Juli','Agustus','September','Oktober','November','Desember'];
const PARAM_LABELS = { ph: 'pH', tss: 'TSS', cod: 'COD', nh3n: 'NH3-N', debit: 'Debit', temp: 'Temperatur' };

const sites = ref([]);
const report = ref(null);
const loading = ref(false);
const exportingPdf = ref(false);
const reportRef = ref(null);

const now = new Date();
const form = ref({
  siteUid: '',
  periodType: 'monthly',
  month: now.getMonth() + 1,
  year: now.getFullYear(),
  dateFrom: '',
  dateTo: '',
});

const years = computed(() => {
  const y = now.getFullYear();
  return [y, y - 1, y - 2, y - 3];
});

const getPeriodDates = () => {
  if (form.value.periodType === 'monthly') {
    const lastDay = new Date(form.value.year, form.value.month, 0).getDate();
    const m = String(form.value.month).padStart(2, '0');
    return { from: `${form.value.year}-${m}-01`, to: `${form.value.year}-${m}-${lastDay}` };
  }
  return { from: form.value.dateFrom, to: form.value.dateTo };
};

const generateReport = async () => {
  if (!form.value.siteUid) return;
  const { from, to } = getPeriodDates();
  if (!from || !to) { toast.error('Pilih periode terlebih dahulu'); return; }
  loading.value = true;
  try {
    report.value = await apiGenerateReport({ site_uid: form.value.siteUid, period_from: from, period_to: to });
    toast.success('Laporan berhasil dibuat');
  } catch {
    toast.error('Gagal membuat laporan');
    report.value = null;
  } finally {
    loading.value = false;
  }
};

// Recommendations using existing analysis utility
const recommendations = computed(() => {
  if (!report.value) return [];
  const recs = [];
  for (const p of report.value.parameters) {
    if (p.stats.count === 0) continue;
    const stats = { avg: p.stats.avg, min: p.stats.min, max: p.stats.max, stdDev: p.stats.std_dev, count: p.stats.count };
    const compliance = { percentage: p.compliance_pct, compliantCount: Math.round(p.stats.count * p.compliance_pct / 100), total: p.stats.count };
    const trend = { direction: p.trend, percentage: 0 };
    const anomalies = { hasAnomalies: false, anomalies: [], count: 0 };
    const paramRecs = generateRecommendations(p.field, stats, compliance, trend, anomalies);
    recs.push(...paramRecs);
  }
  return recs.slice(0, 8);
});

// Status helpers
const statusLabel = (s) => s === 'good' ? 'BAIK' : s === 'warning' ? 'PERHATIAN' : 'KRITIS';
const statusBgClass = (s) => s === 'good' ? 'bg-emerald-50' : s === 'warning' ? 'bg-amber-50' : 'bg-red-50';
const statusTextClass = (s) => s === 'good' ? 'text-emerald-600' : s === 'warning' ? 'text-amber-600' : 'text-red-600';
const statusBgBarClass = (s) => s === 'good' ? 'bg-emerald-500' : s === 'warning' ? 'bg-amber-400' : 'bg-red-500';

const trendLabel = (t) => t === 'increasing' ? 'Naik' : t === 'decreasing' ? 'Turun' : 'Stabil';
const trendIcon = (t) => t === 'increasing' ? 'fas fa-arrow-up' : t === 'decreasing' ? 'fas fa-arrow-down' : 'fas fa-minus';
const trendClass = (t) => t === 'increasing' ? 'text-red-500' : t === 'decreasing' ? 'text-blue-500' : 'text-slate-400';

const recBgClass = (type) => ({ danger: 'bg-red-50 text-red-700', warning: 'bg-amber-50 text-amber-700', info: 'bg-blue-50 text-blue-700', success: 'bg-emerald-50 text-emerald-700' }[type] || 'bg-slate-50 text-slate-600');
const recIcon = (type) => ({ danger: 'fas fa-exclamation-circle text-red-500', warning: 'fas fa-exclamation-triangle text-amber-500', info: 'fas fa-info-circle text-blue-500', success: 'fas fa-check-circle text-emerald-500' }[type] || 'fas fa-circle text-slate-400');

// Trend chart data derived from daily_summary
const TREND_COLORS = { ph: '#3b82f6', tss: '#0ea5e9', cod: '#6366f1', nh3n: '#10b981', debit: '#14b8a6', temp: '#f97316' };

const trendChartSeries = computed(() => {
  if (!report.value?.daily_summary?.length) return [];
  return Object.entries(PARAM_LABELS).map(([field, label]) => ({
    name: label,
    data: report.value.daily_summary.map(d => d[`${field}_avg`] ?? null),
  })).filter(s => s.data.some(v => v !== null));
});

const trendChartOptions = computed(() => {
  if (!report.value?.daily_summary?.length) return null;
  return {
    chart: { type: 'line', toolbar: { show: false }, zoom: { enabled: false }, background: 'transparent' },
    colors: Object.values(TREND_COLORS),
    stroke: { curve: 'smooth', width: 2 },
    xaxis: {
      categories: report.value.daily_summary.map(d => d.date),
      labels: { style: { fontSize: '10px' }, rotate: -30 },
    },
    yaxis: { labels: { style: { fontSize: '10px' } } },
    legend: { position: 'top', fontSize: '11px' },
    tooltip: { shared: true, intersect: false },
    grid: { borderColor: '#f1f5f9' },
  };
});

// Export Excel
const exportExcel = () => {
  if (!report.value) return;
  const rows = report.value.daily_summary.map(d => ({
    'Tanggal': d.date,
    'pH': d.ph_avg,
    'TSS (mg/L)': d.tss_avg,
    'COD (mg/L)': d.cod_avg,
    'NH3-N (mg/L)': d.nh3n_avg,
    'Debit (L/min)': d.debit_avg,
    'Temperatur (°C)': d.temp_avg,
  }));
  const ws = XLSX.utils.json_to_sheet(rows);
  const wb = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(wb, ws, 'Data Harian');
  const filename = `laporan-${report.value.site.uid}-${report.value.period.from}.xlsx`;
  XLSX.writeFile(wb, filename);
  toast.success('File Excel berhasil diunduh');
};

// Export PDF using jsPDF
const exportPdf = async () => {
  if (!report.value || exportingPdf.value) return;
  exportingPdf.value = true;
  try {
    const pdf = new jsPDF({ orientation: 'portrait', unit: 'mm', format: 'a4' });
    const pageW = pdf.internal.pageSize.getWidth();
    let y = 20;

    // Header
    pdf.setFontSize(14);
    pdf.setFont(undefined, 'bold');
    pdf.text('LAPORAN PEMANTAUAN KUALITAS AIR LIMBAH', pageW / 2, y, { align: 'center' });
    y += 7;
    pdf.setFontSize(11);
    pdf.text(report.value.site.company_name, pageW / 2, y, { align: 'center' });
    y += 5;
    pdf.setFont(undefined, 'normal');
    pdf.setFontSize(9);
    pdf.text(`Lokasi: ${report.value.site.name}  |  Periode: ${report.value.period.label}`, pageW / 2, y, { align: 'center' });
    y += 5;
    pdf.text(`Dibuat: ${new Date(report.value.generated_at).toLocaleDateString('id-ID', { dateStyle: 'long' })}`, pageW / 2, y, { align: 'center' });
    y += 10;

    // Summary
    pdf.setFont(undefined, 'bold');
    pdf.setFontSize(11);
    pdf.text('Ringkasan Kepatuhan', 15, y);
    y += 6;
    pdf.setFont(undefined, 'normal');
    pdf.setFontSize(9);
    pdf.text(`Kepatuhan Keseluruhan: ${report.value.summary.compliance_overall}% (${statusLabel(report.value.summary.overall_status)})`, 15, y);
    y += 5;
    pdf.text(`Total Data: ${report.value.summary.total_records.toLocaleString('id-ID')} records  |  Pelanggaran: ${report.value.violations.length}`, 15, y);
    y += 10;

    // Parameters table
    pdf.setFont(undefined, 'bold');
    pdf.setFontSize(11);
    pdf.text('Tabel Hasil Pengukuran', 15, y);
    y += 6;
    pdf.setFontSize(8);
    const headers = ['Parameter', 'Baku Mutu', 'Min', 'Rata-Rata', 'Maks', 'Kepatuhan', 'Tren'];
    const colWidths = [28, 28, 20, 22, 20, 22, 18];
    let x = 15;
    pdf.setFont(undefined, 'bold');
    headers.forEach((h, i) => { pdf.text(h, x, y); x += colWidths[i]; });
    y += 5;
    pdf.setFont(undefined, 'normal');
    for (const p of report.value.parameters) {
      if (y > 260) { pdf.addPage(); y = 20; }
      x = 15;
      const bm = p.baku_mutu.max !== null ? `≤ ${p.baku_mutu.max}` : p.baku_mutu.min !== null ? `≥ ${p.baku_mutu.min}` : '—';
      const row = [
        `${p.label} (${p.baku_mutu.unit})`,
        bm,
        p.stats.min !== null ? p.stats.min.toFixed(2) : '—',
        p.stats.avg !== null ? p.stats.avg.toFixed(2) : '—',
        p.stats.max !== null ? p.stats.max.toFixed(2) : '—',
        `${p.compliance_pct}%`,
        trendLabel(p.trend),
      ];
      row.forEach((v, i) => { pdf.text(String(v), x, y); x += colWidths[i]; });
      y += 5;
    }

    // Save
    const filename = `laporan-${report.value.site.uid}-${report.value.period.from}.pdf`;
    pdf.save(filename);
    toast.success('PDF berhasil diunduh');
  } catch (e) {
    toast.error('Gagal membuat PDF');
  } finally {
    exportingPdf.value = false;
  }
};

// Load sites on mount
onMounted(async () => {
  try {
    const res = await getSites({ per_page: 100 });
    const list = Array.isArray(res) ? res : (res?.items || res?.data || []);
    sites.value = filterSitesByUser(list);
    if (sites.value.length > 0) form.value.siteUid = sites.value[0].uid;
  } catch {
    sites.value = [];
  }
});
</script>
```

- [ ] **Step 2: Commit**

```bash
git add sparing_front/resources/js/Pages/Reports/Index.vue
git commit -m "feat: full Reports page with form, preview, PDF and Excel export"
```

---

## Post-Implementation Checklist

- [ ] Run migration on server (no new tables needed — no alembic upgrade required)
- [ ] `GET /reports/generate?site_uid=...&period_from=...&period_to=...` returns full JSON
- [ ] "Laporan" menu item appears in sidebar for all roles
- [ ] Form: select site + monthly period → Generate → preview appears
- [ ] Tabel Hasil Pengukuran shows all 6 parameters with stats
- [ ] Daftar Pelanggaran shows violation rows (or "tidak ada" message)
- [ ] Rekomendasi section shows auto-generated recommendations
- [ ] "Excel" button downloads .xlsx with daily_summary data
- [ ] "PDF" button downloads .pdf with report header + table
