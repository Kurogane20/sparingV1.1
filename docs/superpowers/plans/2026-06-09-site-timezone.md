# Site-Specific Timezone Display — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Display all timestamps in the timezone of the site whose data is being shown (WIB/WITA/WIT), instead of hardcoded `Asia/Jakarta`.

**Architecture:** Add a `timezone` VARCHAR column to the `sites` table (default `Asia/Jakarta`). Expose it through all Site API responses. In the frontend, parameterize `formatDate`/`formatTime` helpers with a `tz` argument, then pass `site.timezone` everywhere timestamps are rendered — table cells, cards, and ApexCharts x-axis labels and tooltips.

**Tech Stack:** FastAPI + SQLAlchemy + Alembic (backend); Vue 3 Composition API + TailwindCSS + ApexCharts (frontend)

---

## File Map

**Create:**
- `sparing_api/alembic/versions/0005_add_site_timezone.py`

**Modify:**
- `sparing_api/app/models/models.py` — add `timezone` column to `Site`
- `sparing_api/app/schemas/site.py` — add `timezone` to `SiteCreate`, `SiteUpdate`, `SiteOut`
- `sparing_api/app/api/routers/sites.py` — pass `timezone` in all `SiteOut(...)` constructors
- `sparing_api/app/api/routers/reports.py` — add `timezone` to the `site` dict in `ReportOut`
- `sparing_front/resources/js/Utils/helpers.js` — parameterize `formatDate`, add exported `formatTime`
- `sparing_front/resources/js/Pages/Sites/Index.vue` — timezone dropdown in form
- `sparing_front/resources/js/Pages/Dashboard/Index.vue` — site timezone in charts + dates
- `sparing_front/resources/js/Pages/Analytics/Index.vue` — site timezone in charts + CSV
- `sparing_front/resources/js/Pages/History/Index.vue` — site timezone in date/time columns
- `sparing_front/resources/js/Pages/Reports/Index.vue` — site timezone in violation timestamps
- `sparing_front/resources/js/Pages/Devices/Index.vue` — site timezone in calibration/maintenance dates

---

## Task 1: Backend — Migration + Model + Schema

**Files:**
- Create: `sparing_api/alembic/versions/0005_add_site_timezone.py`
- Modify: `sparing_api/app/models/models.py`
- Modify: `sparing_api/app/schemas/site.py`

- [ ] **Step 1: Add `timezone` column to `Site` model**

In `sparing_api/app/models/models.py`, add one line after `lon`:

```python
class Site(Base):
    __tablename__ = "sites"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    uid: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    company_name: Mapped[str] = mapped_column(String(255))
    lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    lon: Mapped[float | None] = mapped_column(Float, nullable=True)
    timezone: Mapped[str] = mapped_column(String(64), default='Asia/Jakarta', server_default='Asia/Jakarta')
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    device_secret: Mapped[str | None] = mapped_column(String(64), nullable=True, unique=True)
    last_ingest_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    devices: Mapped[list["SensorDevice"]] = relationship(back_populates="site")
```

- [ ] **Step 2: Update schemas**

Replace the entire `sparing_api/app/schemas/site.py`:

```python
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

VALID_TIMEZONES = ['Asia/Jakarta', 'Asia/Makassar', 'Asia/Jayapura']

class SiteCreate(BaseModel):
    uid: str
    name: str
    company_name: str
    lat: float | None = None
    lon: float | None = None
    is_active: bool = True
    timezone: str = 'Asia/Jakarta'

class SiteUpdate(BaseModel):
    name: str | None = None
    company_name: str | None = None
    lat: float | None = None
    lon: float | None = None
    is_active: bool | None = None
    timezone: str | None = None

class SiteOut(BaseModel):
    id: int
    uid: str
    name: str
    company_name: str
    lat: float | None = None
    lon: float | None = None
    is_active: bool
    timezone: str = 'Asia/Jakarta'

class SiteDeviceKeyOut(BaseModel):
    uid: str
    name: str
    device_secret: str
    last_ingest_at: datetime | None = None

    model_config = {"from_attributes": True}
```

- [ ] **Step 3: Create Alembic migration**

Create `sparing_api/alembic/versions/0005_add_site_timezone.py`:

```python
from alembic import op
import sqlalchemy as sa

revision = '0005_add_site_timezone'
down_revision = '0004_add_maintenance_log'
branch_labels = None
depends_on = None

def upgrade():
    op.add_column('sites',
        sa.Column('timezone', sa.String(64), nullable=False, server_default='Asia/Jakarta')
    )

def downgrade():
    op.drop_column('sites', 'timezone')
```

- [ ] **Step 4: Commit**

```bash
git add sparing_api/app/models/models.py sparing_api/app/schemas/site.py sparing_api/alembic/versions/0005_add_site_timezone.py
git commit -m "feat: add timezone field to Site model and schema"
```

---

## Task 2: Backend — Update Site and Reports Routers

**Files:**
- Modify: `sparing_api/app/api/routers/sites.py`
- Modify: `sparing_api/app/api/routers/reports.py`

- [ ] **Step 1: Update `list_sites` and `get_site` in sites.py**

The two `SiteOut(...)` constructors currently omit `timezone`. Update both:

```python
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

@router.get("/{id}", response_model=SiteOut)
async def get_site(id: int, db: AsyncSession = Depends(get_db), viewer_uids: list[str] = Depends(get_viewer_site_uids)):
    res = await db.execute(select(Site).where(Site.id==id))
    s = res.scalar_one_or_none()
    if not s:
        raise HTTPException(404, "Not found")
    if viewer_uids and s.uid not in viewer_uids:
        raise HTTPException(403, "Forbidden")
    return SiteOut(id=s.id, uid=s.uid, name=s.name, company_name=s.company_name,
                   lat=s.lat, lon=s.lon, is_active=s.is_active, timezone=s.timezone or 'Asia/Jakarta')
```

- [ ] **Step 2: Update reports router to include timezone in site dict**

In `sparing_api/app/api/routers/reports.py`, find the line:

```python
site={"uid": site.uid, "name": site.name, "company_name": site.company_name},
```

Replace with:

```python
site={"uid": site.uid, "name": site.name, "company_name": site.company_name, "timezone": site.timezone or 'Asia/Jakarta'},
```

- [ ] **Step 3: Commit**

```bash
git add sparing_api/app/api/routers/sites.py sparing_api/app/api/routers/reports.py
git commit -m "feat: include timezone in SiteOut and reports site dict"
```

---

## Task 3: Frontend — Parameterize `helpers.js`

**Files:**
- Modify: `sparing_front/resources/js/Utils/helpers.js`

The current `formatDate` has `timeZone: 'Asia/Jakarta'` hardcoded. Add a `tz` parameter with that as default. Add a new exported `formatTime` function for time-only display (currently defined locally in History/Index.vue).

- [ ] **Step 1: Update `formatDate` and add `formatTime` export**

Replace the existing `formatDate` function and add `formatTime` after it:

```js
/**
 * Format date to Indonesian locale in the given IANA timezone.
 * @param {string|Date} date
 * @param {boolean} includeTime
 * @param {string} tz  IANA timezone string, e.g. 'Asia/Jakarta'
 * @returns {string}
 */
export function formatDate(date, includeTime = false, tz = 'Asia/Jakarta') {
  if (!date) return '-';
  const d = parseUTC(date);
  if (isNaN(d)) return '-';
  try {
    const options = {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      timeZone: tz,
    };
    if (includeTime) {
      options.hour = '2-digit';
      options.minute = '2-digit';
    }
    return d.toLocaleDateString('id-ID', options);
  } catch {
    return d.toLocaleDateString('id-ID', { year: 'numeric', month: 'short', day: 'numeric', timeZone: 'Asia/Jakarta' });
  }
}

/**
 * Format time only (HH:mm:ss) in the given IANA timezone.
 * @param {string|Date} date
 * @param {string} tz  IANA timezone string
 * @returns {string}
 */
export function formatTime(date, tz = 'Asia/Jakarta') {
  if (!date) return '-';
  const d = parseUTC(date);
  if (isNaN(d)) return '-';
  try {
    return d.toLocaleTimeString('id-ID', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      timeZone: tz,
    });
  } catch {
    return d.toLocaleTimeString('id-ID', { hour: '2-digit', minute: '2-digit', second: '2-digit', timeZone: 'Asia/Jakarta' });
  }
}
```

- [ ] **Step 2: Commit**

```bash
git add sparing_front/resources/js/Utils/helpers.js
git commit -m "feat: parameterize formatDate(tz) and export formatTime(tz)"
```

---

## Task 4: Frontend — Sites Form Timezone Dropdown

**Files:**
- Modify: `sparing_front/resources/js/Pages/Sites/Index.vue`

- [ ] **Step 1: Add `timezone` to `siteForm`**

Find the `siteForm` ref definition (around line 393):

```js
const siteForm = ref({
  uid: '',
  name: '',
  company_name: '',
  lat: 0,
  lon: 0,
  is_active: true,
});
```

Replace with:

```js
const siteForm = ref({
  uid: '',
  name: '',
  company_name: '',
  lat: 0,
  lon: 0,
  is_active: true,
  timezone: 'Asia/Jakarta',
});
```

- [ ] **Step 2: Add timezone dropdown to the Info tab form**

In the template, find the block that contains the `is_active` checkbox (around line 172). Add the timezone dropdown immediately **before** the `is_active` row:

```html
<!-- Timezone -->
<div>
  <label class="block text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1.5">Zona Waktu</label>
  <select v-model="siteForm.timezone" class="form-input text-sm">
    <option value="Asia/Jakarta">WIB – Waktu Indonesia Barat (UTC+7)</option>
    <option value="Asia/Makassar">WITA – Waktu Indonesia Tengah (UTC+8)</option>
    <option value="Asia/Jayapura">WIT – Waktu Indonesia Timur (UTC+9)</option>
  </select>
</div>
```

- [ ] **Step 3: Commit**

```bash
git add sparing_front/resources/js/Pages/Sites/Index.vue
git commit -m "feat: add timezone dropdown to Sites form"
```

---

## Task 5: Frontend — Dashboard Timezone

**Files:**
- Modify: `sparing_front/resources/js/Pages/Dashboard/Index.vue`

The Dashboard already has `currentSite` ref and `selectedSiteUid`. Add a `siteTz` computed and use it in chart options (replacing `format: 'dd MMM HH:mm'` with a custom formatter) and in any `formatDate` calls.

- [ ] **Step 1: Add `siteTz` computed**

Dashboard only uses chart formatters for timezone — no direct `formatDate` calls needed, so no import change required. Add `siteTz` computed right after the `overallCompliance` computed (around line 444):

```js
const siteTz = computed(() => currentSite.value?.timezone || 'Asia/Jakarta');
```

- [ ] **Step 2: Update `chartOptions` to use timezone formatter**

Find the `chartOptions` computed. Replace the `xaxis` and `tooltip` sections:

```js
const chartOptions = computed(() => ({
  chart: {
    type: 'area',
    toolbar: { show: false },
    zoom: { enabled: false },
    animations: { enabled: true, easing: 'easeinout', speed: 800 },
    fontFamily: 'Inter, sans-serif',
  },
  colors: [colors.ph, colors.tss, colors.cod, colors.nh3n],
  dataLabels: { enabled: false },
  stroke: { curve: 'smooth', width: 2 },
  fill: {
    type: 'gradient',
    gradient: { shadeIntensity: 1, opacityFrom: 0.35, opacityTo: 0.05, stops: [0, 90, 100] },
  },
  xaxis: {
    type: 'datetime',
    labels: {
      style: { colors: '#94a3b8', fontSize: '10px' },
      formatter: (val) => new Date(val).toLocaleTimeString('id-ID', { timeZone: siteTz.value, hour: '2-digit', minute: '2-digit' }),
    },
    axisBorder: { show: false },
    axisTicks: { show: false },
  },
  yaxis: { labels: { style: { colors: '#94a3b8', fontSize: '10px' } } },
  tooltip: {
    x: {
      formatter: (val) => new Date(val).toLocaleString('id-ID', { timeZone: siteTz.value, day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' }),
    },
    theme: 'light',
  },
  legend: { position: 'top', horizontalAlign: 'left', fontSize: '11px', markers: { radius: 12 } },
  grid: { borderColor: '#f1f5f9', strokeDashArray: 4 },
}));
```

- [ ] **Step 3: Update `electricalOptions` and `debitTempOptions`**

Find `electricalOptions` computed. Replace `tooltip: { x: { format: 'dd MMM HH:mm' }, theme: 'light' }` with:

```js
tooltip: {
  x: {
    formatter: (val) => new Date(val).toLocaleString('id-ID', { timeZone: siteTz.value, day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' }),
  },
  theme: 'light',
},
```

Also update `xaxis` labels in `electricalOptions` to use formatter:
```js
xaxis: {
  type: 'datetime',
  labels: {
    style: { colors: '#94a3b8', fontSize: '10px' },
    formatter: (val) => new Date(val).toLocaleTimeString('id-ID', { timeZone: siteTz.value, hour: '2-digit', minute: '2-digit' }),
  },
  axisBorder: { show: false },
  axisTicks: { show: false },
},
```

Find `debitTempOptions` computed. Apply the same pattern — replace `tooltip: { x: { format: 'dd MMM HH:mm' }, theme: 'light' }` with:

```js
tooltip: {
  x: {
    formatter: (val) => new Date(val).toLocaleString('id-ID', { timeZone: siteTz.value, day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' }),
  },
  theme: 'light',
},
```

And `xaxis` labels:
```js
xaxis: {
  type: 'datetime',
  labels: {
    style: { colors: '#94a3b8', fontSize: '10px' },
    formatter: (val) => new Date(val).toLocaleTimeString('id-ID', { timeZone: siteTz.value, hour: '2-digit', minute: '2-digit' }),
  },
  axisBorder: { show: false },
  axisTicks: { show: false },
},
```

- [ ] **Step 4: Commit**

```bash
git add sparing_front/resources/js/Pages/Dashboard/Index.vue
git commit -m "feat: use site timezone in Dashboard charts and date display"
```

---

## Task 6: Frontend — Analytics Timezone

**Files:**
- Modify: `sparing_front/resources/js/Pages/Analytics/Index.vue`

Analytics has `filters.siteUid` and `sites` ref.

- [ ] **Step 1: Import `formatDate` and add `siteTz` computed**

Find the imports line (around line 181):
```js
import { formatNumber, parseUTC } from '@/Utils/helpers';
```

Replace with:
```js
import { formatNumber, parseUTC, formatDate } from '@/Utils/helpers';
```

Add `siteTz` computed after the `complianceParams` computed (after line 314):

```js
const siteTz = computed(() => {
  const site = sites.value.find(s => s.uid === filters.value.siteUid);
  return site?.timezone || 'Asia/Jakarta';
});
```

- [ ] **Step 2: Update `trendOptions` chart options**

Find the `trendOptions` computed. Replace the `xaxis` and `tooltip` sections:

```js
const trendOptions = computed(() => ({
  chart: {
    type: 'area',
    toolbar: { show: false },
    zoom: { enabled: false },
    animations: { enabled: true, speed: 800 },
    fontFamily: 'Inter, sans-serif',
  },
  colors: [colors.ph, colors.tss, colors.cod, colors.nh3n],
  dataLabels: { enabled: false },
  stroke: { curve: 'smooth', width: 2 },
  fill: {
    type: 'gradient',
    gradient: { shadeIntensity: 1, opacityFrom: 0.4, opacityTo: 0.1 },
  },
  xaxis: {
    type: 'datetime',
    labels: {
      style: { colors: '#64748b', fontSize: '10px' },
      formatter: (val) => new Date(val).toLocaleTimeString('id-ID', { timeZone: siteTz.value, hour: '2-digit', minute: '2-digit' }),
    },
  },
  yaxis: { labels: { style: { colors: '#64748b' } } },
  legend: { position: 'top', fontSize: '11px' },
  tooltip: {
    x: {
      formatter: (val) => new Date(val).toLocaleString('id-ID', { timeZone: siteTz.value, day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' }),
    },
  },
  grid: { borderColor: '#e2e8f0', strokeDashArray: 4 },
  responsive: [{ breakpoint: 768, options: { legend: { fontSize: '10px' } } }],
}));
```

- [ ] **Step 3: Update CSV export timestamp**

Find the CSV export line (around line 393):

```js
if (k === 'ts') return `"${parseUTC(row[k]).toLocaleString('id-ID', { timeZone: 'Asia/Jakarta' })}"`;
```

Replace with:

```js
if (k === 'ts') return `"${parseUTC(row[k]).toLocaleString('id-ID', { timeZone: siteTz.value, day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit', second: '2-digit' })}"`;
```

- [ ] **Step 4: Commit**

```bash
git add sparing_front/resources/js/Pages/Analytics/Index.vue
git commit -m "feat: use site timezone in Analytics charts and CSV export"
```

---

## Task 7: Frontend — History Timezone

**Files:**
- Modify: `sparing_front/resources/js/Pages/History/Index.vue`

History has `filters.siteUid` and `sites` ref. It imports `formatDate` from helpers already, and has a local `formatTime` function. Replace the local `formatTime` with the exported one from helpers, and add `siteTz` computed.

- [ ] **Step 1: Update helpers import and add `formatTime` import**

Find:
```js
import {
  formatDate,
  formatNumber,
  getSensorName,
  getSensorUnit,
  getThresholdStatus,
  downloadCSV,
  parseUTC,
} from '@/Utils/helpers';
```

Replace with:
```js
import {
  formatDate,
  formatTime,
  formatNumber,
  getSensorName,
  getSensorUnit,
  getThresholdStatus,
  downloadCSV,
  parseUTC,
} from '@/Utils/helpers';
```

- [ ] **Step 2: Add `siteTz` computed and remove local `formatTime`**

Add `siteTz` computed after `selectedSiteName` computed (around line 218):

```js
const siteTz = computed(() => {
  const site = sites.value.find(s => s.uid === filters.value.siteUid);
  return site?.timezone || 'Asia/Jakarta';
});
```

Then find and **delete** the local `formatTime` function (around line 262):

```js
// Format time only (WIB)
const formatTime = (date) => {
  if (!date) return '-';
  return parseUTC(date).toLocaleTimeString('id-ID', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    timeZone: 'Asia/Jakarta',
  });
};
```

- [ ] **Step 3: Update template `formatDate` and `formatTime` calls to pass `siteTz`**

In the template, the `ts` cell (around line 138) uses:
```html
<div>{{ formatDate(value, false) }}</div>
<div class="text-xs text-slate-400 font-mono">{{ formatTime(value) }}</div>
```

Replace with:
```html
<div>{{ formatDate(value, false, siteTz) }}</div>
<div class="text-xs text-slate-400 font-mono">{{ formatTime(value, siteTz) }}</div>
```

- [ ] **Step 4: Update CSV export**

Find the CSV export line (around line 395):
```js
'Waktu': formatDate(row.ts, true),
```

Replace with:
```js
'Waktu': formatDate(row.ts, true, siteTz.value),
```

- [ ] **Step 5: Commit**

```bash
git add sparing_front/resources/js/Pages/History/Index.vue
git commit -m "feat: use site timezone in History timestamp columns and CSV export"
```

---

## Task 8: Frontend — Reports Timezone

**Files:**
- Modify: `sparing_front/resources/js/Pages/Reports/Index.vue`

`report.value.site.timezone` is available once the report is generated (Task 2 adds it to the reports API response). Use it for all timestamp displays.

- [ ] **Step 1: Import `formatDate` from helpers**

Find the imports block:
```js
import { generateRecommendations } from '@/Utils/analysis';
import { parseUTC } from '@/Utils/helpers';
```

Replace with:
```js
import { generateRecommendations } from '@/Utils/analysis';
import { parseUTC, formatDate } from '@/Utils/helpers';
```

- [ ] **Step 2: Add `reportTz` computed**

Add after the `report` ref definition (around line 249):

```js
const reportTz = computed(() => report.value?.site?.timezone || 'Asia/Jakarta');
```

- [ ] **Step 3: Update timestamp displays in template**

Find the "Dibuat" line:
```html
<span>Dibuat: {{ parseUTC(report.generated_at).toLocaleDateString('id-ID', { day: '2-digit', month: 'long', year: 'numeric', timeZone: 'Asia/Jakarta' }) }}</span>
```

Replace with:
```html
<span>Dibuat: {{ formatDate(report.generated_at, false, reportTz) }}</span>
```

Find the violation table timestamp cell:
```html
<td class="px-4 py-2 font-mono text-xs text-slate-500">{{ parseUTC(v.ts).toLocaleString('id-ID', { dateStyle: 'short', timeStyle: 'short', timeZone: 'Asia/Jakarta' }) }}</td>
```

Replace with:
```html
<td class="px-4 py-2 font-mono text-xs text-slate-500">{{ formatDate(v.ts, true, reportTz) }}</td>
```

- [ ] **Step 4: Update PDF export timestamp**

Find:
```js
pdf.text(`Dibuat: ${parseUTC(report.value.generated_at).toLocaleDateString('id-ID', { dateStyle: 'long', timeZone: 'Asia/Jakarta' })}`, pageW / 2, y, { align: 'center' });
```

Replace with:
```js
pdf.text(`Dibuat: ${parseUTC(report.value.generated_at).toLocaleDateString('id-ID', { dateStyle: 'long', timeZone: reportTz.value })}`, pageW / 2, y, { align: 'center' });
```

- [ ] **Step 5: Commit**

```bash
git add sparing_front/resources/js/Pages/Reports/Index.vue
git commit -m "feat: use site timezone in Reports violation timestamps and PDF export"
```

---

## Task 9: Frontend — Devices Timezone

**Files:**
- Modify: `sparing_front/resources/js/Pages/Devices/Index.vue`

Devices has `selectedSiteUid` and `sites` ref. All calibration/maintenance date displays use `formatDate(...)`. Add `siteTz` computed and pass it through.

- [ ] **Step 1: Add `siteTz` computed**

The Devices page already imports `formatDate` and `parseUTC` from helpers (added in the UTC timezone fix). Add `siteTz` computed after the `canManageDevices` computed (around line 534):

```js
const siteTz = computed(() => {
  const site = sites.value.find(s => s.uid === selectedSiteUid.value);
  return site?.timezone || 'Asia/Jakarta';
});
```

- [ ] **Step 2: Update calibration date displays in template**

Find the calibration date display (around line 121):
```html
<span>Kalibrasi: {{ formatDate(deviceHealth[device.id].last_calibration_at) }}</span>
```

Replace with:
```html
<span>Kalibrasi: {{ formatDate(deviceHealth[device.id].last_calibration_at, false, siteTz) }}</span>
```

Find the next calibration date display (around line 128):
```html
<span>Berikutnya: {{ formatDate(deviceHealth[device.id].next_calibration_at) }}</span>
```

Replace with:
```html
<span>Berikutnya: {{ formatDate(deviceHealth[device.id].next_calibration_at, false, siteTz) }}</span>
```

- [ ] **Step 3: Update maintenance log date displays in template**

Find the maintenance log date display (around line 400):
```html
<div class="text-xs text-slate-500 font-mono">{{ formatDate(log.performed_at) }}</div>
```

Replace with:
```html
<div class="text-xs text-slate-500 font-mono">{{ formatDate(log.performed_at, false, siteTz) }}</div>
```

Find the next due date display (around line 404):
```html
Berikutnya: {{ formatDate(log.next_due_at) }}
```

Replace with:
```html
Berikutnya: {{ formatDate(log.next_due_at, false, siteTz) }}
```

- [ ] **Step 4: Commit**

```bash
git add sparing_front/resources/js/Pages/Devices/Index.vue
git commit -m "feat: use site timezone in Devices calibration and maintenance dates"
```

---

## Task 10: Build, Migrate, and Deploy

- [ ] **Step 1: Build frontend**

```bash
cd sparing_front
npm run build
```

Expected: `✓ built in X.XXs` with no errors.

- [ ] **Step 2: Run migration on production**

```bash
ssh mitramutiara@103.94.238.65 "cd /opt/sparing/api && source .venv/bin/activate && alembic upgrade head"
```

Expected output ends with: `Running upgrade 0004_add_maintenance_log -> 0005_add_site_timezone`.

- [ ] **Step 3: Restart API service**

```bash
ssh mitramutiara@103.94.238.65 "sudo systemctl restart sparing-api"
```

- [ ] **Step 4: Pull and rebuild on production**

```bash
ssh mitramutiara@103.94.238.65 "sudo git -C /opt/sparing/repo pull origin main && cd /opt/sparing/repo/sparing_front && sudo npm run build"
```

Expected: `✓ built in X.XXs`

- [ ] **Step 5: Final commit (if any uncommitted changes)**

```bash
git add -A
git status  # verify nothing unexpected
git push origin main
```

- [ ] **Step 6: Smoke test**

1. Open the app in browser
2. Go to Sites → edit a site → verify Zona Waktu dropdown appears with WIB/WITA/WIT options
3. Change a site to WITA → save
4. Open Dashboard for that site → verify chart x-axis labels show WITA times (UTC+8, one hour ahead of WIB)
5. Open History for that site → verify `ts` column shows WITA time
