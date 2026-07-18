# SPARING UI v2 Upgrade — Design

**Status:** Approved (brainstorming complete)
**Date:** 2026-07-18
**Reference prototype:** `sparing-ui-v2.html` (Berau mockup) — adopted for structure,
layout patterns, and workflows. Content adapts to this app's reality: multi-site
Mitra Mutiara, WIB, existing auth (email, roles admin/operator/viewer), real data.

## Goal

Upgrade the whole frontend to the v2 structure of the prototype (app shell,
dedicated Alarm page with follow-up workflow, richer Dashboard, validation-aware
History, compliance analytics) plus the small backend additions those screens
need. Scope is **A + B** as decided:

- **A** — UI restructure of every page on top of existing data.
- **B** — small backend additions: alert follow-up workflow, compliance/completeness
  stats, history aggregation, per-row validation flag.

## Out of scope (backlog "C" — separate projects, NOT in this upgrade)

Forecasting/prediction models; KLHK/PUSDATIN delivery tracking; WhatsApp/Telegram/
SMS notification channels; audit log; Super Admin role; NIK login; password expiry
policy; maintenance-banner scheduling. Where the prototype shows these, the v2 UI
either omits them or shows an honest disabled "Segera" state (notification
channels only).

---

## Part 1 — Backend

### 1.1 Alert follow-up workflow (migration `0007_alert_followup`)

New columns on `alerts` (all additive, nullable):
| Column | Type | Purpose |
|---|---|---|
| `followup_note` | TEXT NULL | operator's follow-up / closing note |
| `followup_by_user_id` | INT FK users.id (SET NULL) | who acted |
| `followup_at` | DATETIME(tz) NULL | when follow-up started |
| `resolved_at` | DATETIME(tz) NULL | when closed |

Status reuses the existing column values — UI labels only:
`active` = "Aktif", `acknowledged` = "Dalam tindak lanjut", `resolved` = "Selesai".

Endpoints:
- `PATCH /alerts/{id}/followup` body `{note?: str}` → sets status `acknowledged`,
  stores note (optional at this stage), `followup_by_user_id`, `followup_at`.
- `PATCH /alerts/{id}/resolve` body `{note: str}` → **400 if note empty/missing**
  ("Catatan tindak lanjut wajib diisi"). Sets status `resolved`, `resolved_at`,
  stores note + user. (Existing resolve endpoint is modified to enforce this.)
- **Auto-resolve exemption:** the alert-engine recovery path (compliance value
  back within limits) resolves directly in the engine with
  `followup_note = "Pulih otomatis — nilai kembali normal"` and `resolved_at`
  set; it does not go through the endpoint and is not blocked by the note rule.
- `GET /alerts` gains query params: `category`, `threshold_type`, `site_uid`
  (exists), `status` (exists; also accept `all`), `date_from`, `date_to`,
  `page`/`per_page` with a `total` in the response. Response stays
  backward-compatible: still a list under the existing shape used by
  AlertDropdown, extended via a wrapper `{items, total, page, per_page}` ONLY on
  a new paginated call style — concretely: keep `GET /alerts` returning the
  existing bare list when `page` is absent (dropdown unchanged), return the
  wrapper `{items,total,page,per_page}` when `page` is provided (Alarm page).
  AlertOut gains `followup_note`, `followup_by_name`, `followup_at`,
  `resolved_at` fields.

### 1.2 Stats endpoints (new router `app/api/routers/stats.py`, prefix `/stats`)

All three respect viewer site-scoping (same `get_viewer_site_uids` pattern) and
use the existing TTLCache (5-min TTL) since they scan `sensor_data`.

- `GET /stats/compliance?days=30` →
  `{compliance_pct, prev_pct, delta_pct, checked, violations, days}`.
  Definition: over the window, for every reading × active AlertRule of its site,
  a check fails if the value breaches the rule's danger bounds
  (`_is_violated(value, rule, "danger")`). `compliance_pct = 100 * (1 - failures/checks)`.
  Readings with `quality_flag='anomaly'` are excluded from checks.
  `prev_pct` = same metric for the preceding window of equal length.
- `GET /stats/compliance-daily?month=YYYY-MM` → list of
  `{date, status}` where status ∈ `ok | warning | violation | none`:
  `violation` if any danger breach that day, else `warning` if any
  warning-band breach, else `ok` if data exists, `none` if no data.
- `GET /stats/completeness?hours=24` →
  `{actual, expected, pct}` where `expected = active_sites × 30 × hours`
  (devices deliver ~30 readings per site per hour) and `actual` = sensor_data
  rows in the window. `pct` capped at 100.

### 1.3 History aggregation

`GET /data` gains `interval=raw|hourly|daily` (default `raw`, unchanged
behavior). For `hourly`/`daily`: SQL GROUP BY the truncated `ts` bucket,
AVG of each requested field, plus `count` per bucket. Rows with
`quality_flag='anomaly'` are **excluded from the averages** (prototype
behavior: anomalies excluded from rerata, retained for audit). Pagination
applies to buckets.

### 1.4 Per-row validation flag (migration `0008_sensor_data_quality_flag`)

- New column `sensor_data.quality_flag VARCHAR(16) NULL` (`NULL` = valid,
  `'anomaly'` = flagged), indexed with site_id+ts already covered by existing ts
  index — no new index needed beyond the column.
- `detect_realtime` (anomaly engine) already evaluates every reading in a burst
  via `scan_batch`; for each hit `(ts, value, result)` with anomaly_type
  `implausible` or `spike`, it now also
  `UPDATE sensor_data SET quality_flag='anomaly' WHERE site_id=? AND ts=?`
  (same session/commit as alert+health writes; failure remains contained by the
  engine's try/except — never breaks ingest). Flatline/drift do NOT flag rows
  (they describe windows, not single readings).
- `DataOut` gains `quality_flag`; History UI renders badge
  Valid (`NULL`) / Anomali (`'anomaly'`).

---

## Part 2 — Frontend restructure

Design language: the teal/ink tokens already shipped (Source Sans 3 +
IBM Plex Mono, formal status colors). This upgrade is about structure.

### 2.1 App shell v2 (`AppLayout.vue` rework; `Header.vue` retired)

- **Sidebar (ink)**: logo head; grouped nav with uppercase labels —
  *Pemantauan*: Dashboard, Alarm (red pill = active alert count, polled);
  *Data*: Riwayat Data, Analisis, Laporan;
  *Administrasi*: Lokasi, Perangkat (admin/operator), Pengguna (admin),
  Pengaturan. Active item = solid white. **Sidebar foot**: avatar initials,
  name, role, and Keluar button (moved from header dropdown).
- **Utility strip** (top, replaces Header): server status dot (`/healthz`
  polled), "Sinkronisasi terakhir" (newest `sensor_data.created_at` via
  existing site stats or completeness payload), live WIB clock, and the
  **AlertDropdown bell kept here** (right side) as quick access.
- **Per-page pattern**: breadcrumb line (`Beranda / <section> / <page>`), topbar
  (title, subtitle, right-side action buttons) — implemented as a small
  `PageHeader.vue` component used by every page.
- **App footer**: version, session note, helpdesk, "Zona waktu tampilan: WIB".
- Mobile: sidebar slides (existing behavior preserved); menu button in topbar.

### 2.2 Login v2 (`Login.vue`)

Two-panel: left white card — email + password (existing auth; **no NIK**),
show/hide password, error state, note box ("hubungi administrator"), footer
(version, supported browsers). Right ink panel — tagline SPARING, lead copy,
**static** facts only (parameters monitored, 2-minute interval) — no live
numbers on an unauthenticated page. Decorative concentric-circle accents per
prototype. Mobile: right panel hidden (as prototype).

### 2.3 Dashboard v2 (`Pages/Dashboard/Index.vue`)

- **KPI row (4)**: Perangkat online `X/Y` (existing device status); Kepatuhan
  baku mutu 30 hari `%` + delta note (`/stats/compliance`); Alarm aktif count +
  worst-alert note (existing alerts); Kelengkapan data hari ini `%`
  (`/stats/completeness`).
- **Param strip**: one tile per in-scope parameter (ph, tss, cod, nh3n, debit,
  temp when present): mono value, unified status badge (existing `cardStatus`
  logic: Cek Sensor > Bahaya > Waspada > Baik), baku-mutu line (from site's
  AlertRules), **inline SVG sparkline** of the last ~2h readings with a dashed
  red threshold line; left border 3px colored by status.
- **Status table**: per site (and its device): site, lokasi/company, update
  terakhir (relative), pH, TSS (mono, right-aligned), unified status badge.
- **Right column**: Alarm aktif feed (top 3 by severity, sevbar colors, link to
  /alarms) + Kelengkapan card (meter bars: today's actual/expected, antrean =
  none → show plain completeness only).
- Site selector, refresh, auto-refresh, chart & compliance panel behaviors are
  preserved (chart stays dual-axis as shipped); layout re-arranged to the
  prototype grid.

### 2.4 Alarm page (new `Pages/Alarms/Index.vue`, route `/alarms`)

- Filterbar: Tingkat (semua/bahaya/waspada), Kategori (baku mutu/kualitas data/
  perangkat), Lokasi (site select), Status (Aktif/Dalam tindak lanjut/Selesai/
  Semua), Terapkan.
- Table: No, Waktu (mono), Lokasi, Kejadian (label field + anomaly type wording
  reused from AlertDropdown), Nilai (mono), Durasi (triggered→resolved or →now),
  PIC (`followup_by_name`), Status badge, action button.
- Actions: **Tindak lanjut** (modal: optional note → PATCH followup) on active;
  **Selesaikan** (modal: required note; disabled submit while empty → PATCH
  resolve) on active/acknowledged; **Catatan** (read-only view) on resolved.
- Pagination via the new `{items,total,page,per_page}` mode. Footnote: catatan
  wajib sebelum alarm ditutup.
- Sidebar pill + AlertDropdown counts stay in sync (same count endpoint).

### 2.5 Riwayat v2 (`Pages/History/Index.vue`)

- Filterbar gains **Interval** select: Data mentah (2 menit) / Rerata per jam /
  Rerata harian → passes `interval` to `/data`.
- New **Validasi** column: badge Valid / Anomali from `quality_flag` (raw mode
  only; aggregated modes show bucket `count` instead). Footnote explains that
  anomalous values are excluded from averages but retained for audit.
- Export unchanged (CSV keeps working; includes quality_flag column in raw mode).

### 2.6 Analisis v2 (`Pages/Analytics/Index.vue`)

- Keep existing trend chart + stats (analysis.js) restyled into the prototype
  grid: big chart left; right column = Statistik card (rerata/min/max/p95/
  simpangan/kelengkapan/data dikecualikan — the last two from completeness +
  quality_flag counts) + "Catatan sistem" card fed by existing
  `generateRecommendations()` output rendered as sevbar items.
- **No forecast** (backlog C) — no dashed prediction line.
- New full-width card: **Rekap kepatuhan harian** heatmap for the selected month
  (`/stats/compliance-daily`), with legend (Patuh/Peringatan/Pelampauan/Belum
  berjalan) and per-day tooltip.

### 2.7 Laporan (`Pages/Reports/Index.vue`) — light restyle

KPI row (kelengkapan bulan berjalan from `/stats/completeness?hours=720`,
laporan dibuat count if available client-side) + existing generator/PDF/Excel
flows presented in the archive-table style. No new backend.

### 2.8 Pengguna v2 (`Pages/Users/Index.vue`)

Existing CRUD + site-assignment kept; presentation upgraded: role chips
(admin=teal, operator=amber, viewer=gray), search + role/status filter bar,
last-login column omitted (not tracked — out of scope), plus a static
**Matriks hak akses** card reflecting real capabilities of admin/operator/viewer
(view dashboard, export riwayat, tindak lanjut alarm, konfigurasi site/kalibrasi,
susun laporan, kelola user).

### 2.9 Pengaturan v2 (`Pages/Settings/Index.vue`)

- Profil + ubah password (existing) restyled to setrow pattern.
- **Ambang peringatan dini**: per-site AlertRule editor embedded here (reuses
  the existing `/alert-rules` API and the editor currently living in Sites
  page — Sites keeps its copy; Settings gets the same component extracted as
  `AlertRuleEditor.vue` to avoid duplication).
- **Kanal notifikasi**: Email row shown active (informational — reflects SMTP
  reality); WhatsApp/Telegram/SMS rows rendered disabled with "Segera" badge.

---

## Part 3 — Testing, migrations, rollout

### Testing (TDD on the existing async harness)

- **Alerts workflow** (`test_alerts_api.py`): resolve without note → 400; with
  note → stored (note/user/timestamps); followup sets acknowledged; auto-resolve
  path writes system note and bypasses endpoint guard; filters + pagination
  wrapper mode vs bare-list mode.
- **Stats** (`test_stats_api.py`): compliance math on seeded readings + rules
  (all-compliant, with violations, no rules → checked=0 handled); daily statuses;
  completeness actual/expected.
- **Aggregation** (`test_data_api.py`): hourly/daily averages correct; anomaly
  rows excluded; raw unchanged; bucket pagination.
- **Quality flag** (unit + api): scan_batch hits mark exactly the hit rows;
  clean readings untouched.
- Frontend: `npm run build` gate (no JS test infra — consistent with repo).

### Migrations

`0007_alert_followup`, `0008_sensor_data_quality_flag` — additive, nullable,
safe on existing rows; applied by the deploy script (`alembic upgrade head`).

### Compatibility

All API changes additive. `/alerts` keeps bare-list response when `page` absent
so the already-deployed AlertDropdown keeps working during staged rollout.
Backend deploys first; frontend follows.

### Rollout order

1. Backend: migrations + endpoints → deploy → verify on prod (curl checks).
2. Frontend in commit waves: shell v2 → Dashboard v2 → Alarm page → Riwayat +
   Analisis → Login + Laporan/Pengguna/Pengaturan → deploy.
3. End-to-end verification on prod: KPIs show real numbers, follow-up flow
   enforces notes, heatmap renders, history intervals + validation badges work.

### Risks & mitigations

- Big simultaneous UI change → data/query logic untouched (presentation-layer
  rework), granular commits per page for easy rollback.
- Alert lifecycle interplay with auto-resolve → explicit system-note design
  (§1.1), covered by tests.
- Stats scans on sensor_data → TTL cache, windowed queries on indexed `ts`.
