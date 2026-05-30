# SPARING Feature Roadmap — Design Spec
**Date:** 2026-05-30  
**Status:** Approved  
**Approach:** One complete feature per sprint, in priority order

---

## Context

SPARING (Sistem Pemantauan Air Lingkungan Industri) is a real-time industrial wastewater monitoring dashboard. Primary users are **operators** (monitor sensors daily in the field) and **managers** (need compliance reports for KLHK submission).

**Tech stack:** Vue 3 + Vite + TailwindCSS (frontend) · FastAPI + SQLAlchemy + MySQL (backend)

**Current gaps identified:**
- No alerting when parameters exceed baku mutu — operators only notice after opening dashboard
- Baku mutu thresholds hardcoded in `helpers.js` — cannot vary per site's IPLC permit
- `ApiKey` model exists in backend but no UI — new device onboarding requires server access
- IoT device secret is a single global hardcoded string `"sparing"` — cannot revoke per site
- No maintenance/calibration log for sensor devices
- No formatted regulatory report — only raw PDF export from Analytics page

---

## Feature 1 — Alert & Notification System

**Priority:** 1 (highest risk if absent — compliance violations/fines)

### Backend

**New model: `AlertRule`**
```
id, site_id (FK sites), field (str), warning_value (float),
danger_value (float), is_active (bool, default=True),
created_at, updated_at
```
Constraints: unique on `(site_id, field)`. One rule per parameter per site.

When a new site is created, the system automatically seeds default `AlertRule` entries for all 8 parameters using the system defaults from `helpers.js` (e.g., pH warning: 6.5–8.5, danger: 6.0–9.0). Admin can then override per site.

**New model: `Alert`**
```
id, site_id (FK sites), device_uid (str, nullable),
field (str), value (float), threshold_type (warning|danger),
status (active|acknowledged|resolved),
triggered_at, acknowledged_at (nullable), acknowledged_by_user_id (FK users, nullable)
```
Index on `(site_id, status, triggered_at DESC)`.

**New router: `/alerts`**
```
GET    /alerts                          → list alerts (filter: site_uid, status, field)
GET    /alerts/count?status=active      → returns { count: N } for badge
PATCH  /alerts/{id}/acknowledge         → set status=acknowledged
PATCH  /alerts/{id}/resolve             → set status=resolved
```

**New router: `/alert-rules`**
```
GET    /alert-rules?site_uid=...        → list rules for a site
POST   /alert-rules                     → create rule
PATCH  /alert-rules/{id}               → update thresholds or toggle is_active
DELETE /alert-rules/{id}               → delete rule
```

**Alert trigger logic** — injected into `POST /api/post-data` after data is saved:
1. Load active `AlertRule` records for the site
2. For each rule, compare incoming value against `danger_value` then `warning_value`
3. Before creating an alert, check: no existing `active` alert for the same `(site_id, field)` within the last 30 minutes (deduplication)
4. If threshold breached and no recent duplicate: insert `Alert(status=active)` + queue email task

**Device offline alert** — background task runs every 5 minutes:
- For each active site, check latest `SensorData.ts`
- If last data > 60 minutes ago → create `Alert(field="device_offline", threshold_type="danger")` if no active offline alert exists

**Email notification:**
- Triggered async after alert insert (non-blocking)
- Recipients: all users assigned to the site (admin + operators with site access)
- Template fields: site name, parameter, current value, baku mutu limit, timestamp
- SMTP config read from env vars: `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASS`, `SMTP_FROM`
- Settings page exposes these fields for admin to configure

### Frontend

**Header — Bell icon:**
- Polls `GET /alerts/count?status=active` every 30 seconds
- Red badge shows count when > 0
- Click opens alert dropdown panel (max 10 most recent active alerts)
- Each item: colored left border (red=danger, amber=warning) + site name + parameter + value + time ago + "Acknowledge" button

**Sites page — "Baku Mutu" tab inside the site edit modal:**
- New tab added to the existing site edit modal (alongside the current Info tab)
- Shows current `AlertRule` list for that site: parameter | warning threshold | danger threshold | toggle active
- "Tambah Aturan" button → inline form: select field, input warning value, danger value
- Available to admin and operator roles only (viewers see read-only)

**Dashboard SensorCard:** No change needed — threshold colors already implemented.

---

## Feature 2 — API Key Management (Per-Site Device Secret)

**Priority:** 2 (unblocks onboarding new sensor devices without server access)

### Backend

**Migration:** Add `device_secret` column to `sites` table:
```
device_secret: str (64 chars), nullable, unique
```
Auto-generated (UUID4 without hyphens) when a site is created. Backfilled for existing sites via migration.

**Modified endpoint: `GET /api/get-key`**
```
# With uid param → return site-specific secret (new devices)
GET /api/get-key?uid=SITE_UID  →  returns site's device_secret (plain text)

# Without uid param → return global secret (backward compat for existing devices)
GET /api/get-key               →  returns GETDATA_SECRET env var (was hardcoded "sparing")
```

**Modified endpoint: `POST /api/post-data`**
- Decode JWT using site-specific `device_secret` (looked up by `uid` in JWT payload)
- Fall back to global `GETDATA_SECRET` if site has no `device_secret` (transition period)
- Update `Site.last_ingest_at` (new nullable column) on each successful post

**New endpoint:**
```
POST /sites/{uid}/rotate-secret   → generate new UUID4 secret, save to site (admin only)
                                    returns { device_secret: "new_secret" }
```

**`GETDATA_SECRET`** promoted from hardcoded string to env var (default: `"sparing"` for backward compat).

### Frontend

**Sites page — "Device Key" panel per site card:**
- Shows masked secret: `spg_a1b2c3••••••••` with [Tampilkan] / [Sembunyikan] toggle
- [Copy] button copies full secret to clipboard
- [Regenerate] button → confirmation dialog: _"Perangkat yang menggunakan secret lama akan berhenti mengirim data sampai diperbarui."_ → calls `/rotate-secret`
- Shows: last data received (from `last_ingest_at`), total records today (from IngestLog count)
- Available to admin role only

**IoT device firmware change (new devices only):**
```
# Old (still works)
GET /api/get-key

# New
GET /api/get-key?uid=SITE_UID
```
JWT payload format and `POST /api/post-data` format are unchanged.

---

## Feature 3 — Device Health & Maintenance Log

**Priority:** 3 (daily operational value for operators)

### Backend

**New model: `MaintenanceLog`**
```
id, device_id (FK sensor_devices), type (calibration|repair|inspection|note),
notes (text), performed_by_user_id (FK users, nullable),
performed_at (datetime), next_due_at (datetime, nullable),
created_at
```

**New endpoints:**
```
GET    /devices/{id}/health         → { last_seen, status, data_count_24h, data_count_7d }
GET    /devices/{id}/maintenance    → list maintenance logs (ordered by performed_at DESC)
POST   /devices/{id}/maintenance    → add log entry
DELETE /devices/{id}/maintenance/{log_id}  → delete entry (admin/operator only)
```

**Health status logic:**
- `online`: last data < 15 minutes ago
- `warning`: 15–60 minutes ago
- `offline`: > 60 minutes ago
- `unknown`: no data ever received

**Device offline → Alert integration:**
Uses the same `Alert` model from Feature 1 with `field="device_offline"`.

### Frontend

**Devices page — enhanced device cards:**
```
┌─────────────────────────────────────┐
│ ● DEVICE-001                        │
│ Model: XYZ-200 | SN: ABC123         │
│                                     │
│ Status: ● Online                    │
│ Terakhir data: 3 menit lalu         │
│ Data hari ini: 144 records          │
│                                     │
│ Kalibrasi terakhir: 12 Jan 2025     │
│ Kalibrasi berikutnya: ⚠ 12 Jul 2025 │
│                                     │
│ [Detail & Log Perawatan]            │
└─────────────────────────────────────┘
```

Status indicator color: emerald (online) · amber (warning) · red (offline) · slate (unknown)

`next_due_at` warning: amber if within 30 days, red if overdue.

**Modal "Detail & Log Perawatan" — two tabs:**

Tab 1 — Info (existing edit form, unchanged)

Tab 2 — Log Perawatan:
- Timeline list: date · type badge · notes · performed by
- "Tambah Catatan" button → inline form:
  - Tipe: dropdown (Kalibrasi / Perbaikan / Inspeksi / Catatan)
  - Tanggal pelaksanaan: date picker
  - Catatan: textarea
  - Jadwal berikutnya: date picker (optional, shown only for Kalibrasi)

Available to operator and admin roles.

---

## Feature 4 — Regulatory Report Generator

**Priority:** 4 (high value for managers, but no immediate compliance risk)

### Backend

**New endpoint:**
```
GET /reports/generate?site_uid=...&period_from=YYYY-MM-DD&period_to=YYYY-MM-DD
```

Response structure:
```json
{
  "site": { "uid": "...", "name": "...", "company_name": "..." },
  "period": { "from": "2025-01-01", "to": "2025-01-31", "label": "Januari 2025" },
  "generated_at": "2025-02-01T08:00:00Z",
  "summary": {
    "total_records": 744,
    "compliance_overall": 94,
    "overall_status": "good"
  },
  "parameters": [
    {
      "field": "ph",
      "label": "pH",
      "baku_mutu": { "min": 6.0, "max": 9.0, "unit": "" },
      "stats": { "avg": 7.2, "min": 6.1, "max": 8.8, "std_dev": 0.4, "count": 744 },
      "compliance_pct": 97,
      "violation_count": 12,
      "trend": "stable"
    }
  ],
  "daily_summary": [
    { "date": "2025-01-01", "ph_avg": 7.1, "tss_avg": 45.2, ... }
  ],
  "violations": [
    { "ts": "2025-01-03T14:22:00Z", "field": "tss", "value": 142.5, "limit": 100 }
  ]
}
```

All aggregation done in SQL (not in Python loops) for performance. Baku mutu values sourced from `AlertRule` table for the site (Feature 1) with fallback to system defaults.

**Note:** No PDF generation in backend — frontend handles PDF rendering using the existing library.

### Frontend

**New page: `/reports` — added to sidebar between Analytics and History**

Sidebar icon: `fa-file-alt`  
Access: all roles (viewers see their assigned sites only)

**Step 1 — Report form:**
```
Lokasi:    [Site A ▼]
Periode:   [Bulanan ▼]   Bulan: [Januari ▼]  Tahun: [2025 ▼]
           atau [Custom]  Dari: [___]  Sampai: [___]
[Generate Laporan]
```

**Step 2 — Report preview (same page, below form):**

Header block:
```
LAPORAN PEMANTAUAN KUALITAS AIR LIMBAH
PT. Nama Perusahaan — Nama Lokasi
Periode: Januari 2025 | Dibuat: 1 Feb 2025
```

Sections rendered as Vue components (printable):
1. **Ringkasan Kepatuhan** — overall % + status badge + data point count
2. **Tabel Hasil Pengukuran** — per parameter: baku mutu | min | rata-rata | maks | kepatuhan %
3. **Grafik Tren** — line chart per parameter (reuse ApexCharts from Analytics)
4. **Daftar Pelanggaran** — table of violation events (ts · parameter · nilai · batas)
5. **Rekomendasi** — auto-generated text (reuse `generateRecommendations` from `analysis.js`)

**Export buttons:**
- "Export PDF" — uses existing PDF library, prints report sections
- "Export Excel" — downloads daily_summary as XLSX (use `xlsx` npm package)

---

## Implementation Order

| Sprint | Feature | Key Deliverables |
|--------|---------|-----------------|
| 1 | Alert & Notification | AlertRule + Alert models, trigger logic, email, bell UI, baku mutu config in Sites |
| 2 | API Key Management | device_secret migration, modified get-key endpoint, Sites "Device Key" panel |
| 3 | Device Health & Maintenance | MaintenanceLog model, health endpoints, enhanced device cards, maintenance log modal |
| 4 | Regulatory Reports | /reports/generate endpoint, Reports page, PDF/Excel export |

Each sprint: backend models + migrations first, then API endpoints, then frontend.

---

## Shared Infrastructure Notes

- **Alembic migrations** required for each sprint (new models)
- **Email sending** (Feature 1): use `fastapi-mail` or `aiosmtplib` — async, non-blocking
- **Excel export** (Feature 4): add `openpyxl` or `xlsx` to frontend dependencies
- **Role guards** consistent across all new pages: admin/operator can write, viewer reads only
- All new API endpoints follow existing pattern in `useApi.js` composable
