# Logger Monitoring — Frontend Implementation Plan (Plan 3 of 3)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Surface logger health in the web app — a dedicated `/loggers` page (per-site status table + event timeline that answers "when did the logger die and why"), a logger-health chip on the Dashboard, a "Logger" category filter on the Alarm page, and a "Kalibrasi/Berhenti/Rusak" badge on History rows that carry an operational-status code.

**Architecture:** Presentation-layer work on top of the already-deployed backend (`GET /logger/status`, `GET /logger/events`, and `op_status` on `/data` rows). Reuses the shipped v2 components (`AppLayout`, `PageHeader`, badges, tables) and design tokens — no new visual language. The page renders live as soon as the first heartbeat arrives; until then it shows an empty/"belum ada data" state.

**Tech Stack:** Vue 3 `<script setup>`, vue-router, Tailwind, axios via `useApi()`. No JS test infra — the gate for every task is `npm run build` (from `sparing_front/`) succeeding.

**Reference spec:** `docs/superpowers/specs/2026-07-20-logger-monitoring-design.md` (Part 3).

**Backend contract (LIVE):**
- `GET /logger/status` → bare array of objects:
  `{site_id, site_uid, site_name, state ('alive'|'down'), state_since, last_heartbeat_at, minutes_since_heartbeat, logger_version, uptime_s, op_status, ph_ok, tss_ok, debit_ok, cod_ok, nh3n_ok, consec_fail, internet_ok, last_send_ok_mm, last_send_ok_klhk, buffer_depth, daily_sent, cpu_temp, cpu_pct, mem_pct, disk_pct}`. Viewer-scoped server-side.
- `GET /logger/events` → bare array when no `page`; `{items,total,page,per_page}` when `page` given. Item:
  `{id, site_id, site_uid, site_name, event_uid, type, ts, received_at, severity ('info'|'warning'), detail}`. Filters: `site_uid`, `type`, `severity`, `date_from`, `date_to`. Event types: `started, stopping, stopped, sensor_fail, sensor_recover, net_down, net_up, send_fail, opstatus_change, buffer_high, unknown`.
- `/data` rows now include `op_status` (`null`, or `-1`/`-2`/`-3`).
- Logger alarms arrive through the existing `/alerts` API with `category: "logger"`, `field` = `logger_down` or `sensor_<name>`.

**Conventions:** frontend commands from `c:\Users\nurch\OneDrive\Documents\project\sparingV1.1\sparing_front`; git from repo root. Design tokens: `primary` (#0E7C86 teal, +`primary-dark`/`primary-soft`), `ink` (#12333B), `danger` (#B03030), `warning` (#9A6B00), `success` (#1F7A4D); muted text `text-[#617377]`, borders `border-[#D7E0E1]`, page bg `#EEF2F3`, cards `bg-white`; `font-mono` for numeric/time values. WIB via `@/Utils/helpers` (`formatDate`, `formatTime`, `getRelativeTime`) — never `new Date()` on a raw UTC string. Use FontAwesome (`<i class="fas fa-...">`).

---

## File Structure

- Modify: `resources/js/Composables/useApi.js` — `getLoggerStatus`, `getLoggerEvents`
- Modify: `resources/js/app.js` — `/loggers` route
- Modify: `resources/js/Components/Sidebar.vue` — Logger nav item + down-count pill
- Create: `resources/js/Components/LoggerEventTimeline.vue` — the event log view
- Create: `resources/js/Pages/Loggers/Index.vue` — the page (KPIs + per-site table + timeline)
- Modify: `resources/js/Pages/Dashboard/Index.vue` — logger-health chip
- Modify: `resources/js/Pages/Alarms/Index.vue` — "Logger" category option + field wording
- Modify: `resources/js/Pages/History/Index.vue` — op_status badge

---

### Task 0: Baseline — build is green

- [ ] **Step 1: Confirm a clean build**

Run (from `sparing_front/`): `npm run build`
Expected: completes, prints the `dist/assets/index-*.js` bundle, exit 0. If it fails on a pre-existing error, stop and report.

---

### Task 1: API methods

**Files:** Modify `resources/js/Composables/useApi.js`

- [ ] **Step 1: Add the methods**

Read the file; add near the other GETs (before the `return {`):
```js
  // Logger monitoring
  const getLoggerStatus = () => request('GET', '/logger/status');
  const getLoggerEvents = (params = {}) => request('GET', '/logger/events', null, { params });
```
Add `getLoggerStatus, getLoggerEvents` to the returned object (a `// Logger` group).

- [ ] **Step 2: Build + commit**

Run: `npm run build` → succeeds.
```bash
git add sparing_front/resources/js/Composables/useApi.js
git commit -m "feat(fe): api methods for logger status + events"
```

---

### Task 2: `/loggers` route + sidebar nav with down-count pill

**Files:** Modify `resources/js/app.js`, `resources/js/Components/Sidebar.vue`

- [ ] **Step 1: Register the route + stub page**

In `app.js`: `import Loggers from './Pages/Loggers/Index.vue';` and add after the `/alarms` route:
```js
    {
      path: '/loggers',
      name: 'loggers',
      component: Loggers,
      meta: { requiresAuth: true },
    },
```
Create `resources/js/Pages/Loggers/Index.vue` as a minimal valid SFC so the build resolves (real content in Task 3):
```vue
<template>
  <AppLayout>
    <PageHeader :crumb="['Beranda', 'Logger']" title="Monitoring Logger" />
  </AppLayout>
</template>
<script setup>
import AppLayout from '@/Layouts/AppLayout.vue';
import PageHeader from '@/Components/PageHeader.vue';
</script>
```

- [ ] **Step 2: Add the sidebar nav item + pill**

Read `Sidebar.vue`. In the *Pemantauan* group (where Dashboard + Alarm live), add a "Logger" item linking to `/loggers` (icon e.g. `fas fa-microchip` or `fas fa-hard-drive`). Add a red pill showing the count of DOWN loggers, mirroring how the Alarm pill fetches its count: on mount and every 60s, call `getLoggerStatus()` and count `state === 'down'`; hide the pill when 0. Guard with try/catch so a failing call never breaks the sidebar. Do not disturb the existing alarm pill logic.

- [ ] **Step 3: Build + commit**

Run: `npm run build` → succeeds.
```bash
git add sparing_front/resources/js/app.js sparing_front/resources/js/Pages/Loggers/Index.vue sparing_front/resources/js/Components/Sidebar.vue
git commit -m "feat(fe): /loggers route + sidebar nav with down-logger pill"
```

---

### Task 3: Event timeline component

**Files:** Create `resources/js/Components/LoggerEventTimeline.vue`

- [ ] **Step 1: Implement**

Props: `events` (Array of event objects), `loading` (Boolean). Render a chronological vertical timeline (newest first — the API already returns `ts DESC`). Each row: a severity/type icon+color, a human label, the WIB time (`formatDate`+`formatTime` of `ts`), and `detail` when present. Map event types to Indonesian labels + icon/color:

```js
const EVENT_META = {
  started:        { label: 'Logger menyala',            icon: 'fa-play',            color: '#1F7A4D' },
  stopping:       { label: 'Logger berhenti (normal)',  icon: 'fa-stop',            color: '#617377' },
  stopped:        { label: 'Logger berhenti',           icon: 'fa-stop',            color: '#617377' },
  sensor_fail:    { label: 'Sensor gagal dibaca',       icon: 'fa-triangle-exclamation', color: '#9A6B00' },
  sensor_recover: { label: 'Sensor pulih',              icon: 'fa-circle-check',    color: '#1F7A4D' },
  net_down:       { label: 'Internet terputus',         icon: 'fa-wifi',            color: '#9A6B00' },
  net_up:         { label: 'Internet tersambung',       icon: 'fa-wifi',            color: '#1F7A4D' },
  send_fail:      { label: 'Gagal kirim data',          icon: 'fa-cloud-arrow-up',  color: '#9A6B00' },
  opstatus_change:{ label: 'Status operasional berubah',icon: 'fa-sliders',         color: '#0E7C86' },
  buffer_high:    { label: 'Antrean data menumpuk',     icon: 'fa-layer-group',     color: '#9A6B00' },
  unknown:        { label: 'Kejadian',                  icon: 'fa-circle-info',     color: '#617377' },
};
```
For a `started` event whose `detail` contains `previous_shutdown_clean=false`, render an emphasized sub-note like "Shutdown sebelumnya TIDAK bersih (crash/listrik padam)" in `text-[#B03030]` — this is the line that distinguishes a crash from a clean restart. Empty state ("Belum ada kejadian tercatat") and a loading spinner. Reuse card/border tokens.

- [ ] **Step 2: Build + commit** (component has no caller yet; build just checks syntax)

Run: `npm run build` → succeeds.
```bash
git add sparing_front/resources/js/Components/LoggerEventTimeline.vue
git commit -m "feat(fe): logger event timeline component"
```

---

### Task 4: Loggers page — KPIs + per-site status table + timeline

**Files:** Rewrite `resources/js/Pages/Loggers/Index.vue`

- [ ] **Step 1: Implement**

Structure (`<AppLayout>` + `<PageHeader :crumb="['Beranda','Logger']" title="Monitoring Logger" subtitle="Status perangkat logger di tiap lokasi — heartbeat, kesehatan sensor, dan riwayat kejadian." >` with a refresh button in `#actions`):

1. **KPI row (3 cards):** Logger hidup `X/Y` (count `state==='alive'` over total rows); Alarm logger aktif (from `getAlerts({ status:'active', category:'logger' })` — bare array, `.length`); Event 24 jam terakhir (from `getLoggerEvents({ date_from:<24h ISO> })` length).
2. **Per-site status table/cards** (one row per `getLoggerStatus()` item):
   - state chip: `alive`→success "Hidup", `down`→danger "Mati" + `getRelativeTime(state_since)`;
   - last heartbeat: `getRelativeTime(last_heartbeat_at)` (or "—");
   - uptime: format `uptime_s` to `Xh Ym` (small helper);
   - logger version;
   - operational-status chip from `op_status`: `0/null`→"Normal", `-1`→"Berhenti", `-2`→"Kalibrasi", `-3`→"Rusak";
   - **five sensor dots** (pH/TSS/debit/COD/NH₃-N): `true`→green, `false`→red, `null`→gray, with a tooltip;
   - internet chip (`internet_ok`);
   - buffer depth (mono), sent today (mono);
   - mini bars for `cpu_temp`/`cpu_pct`/`mem_pct`/`disk_pct` (a small `<div>` meter each, hide when null).
   - Clicking a row selects that site for the timeline below (set `selectedSiteUid`).
3. **Event timeline** below the table: `<LoggerEventTimeline :events="events" :loading="eventsLoading" />`, loaded via `getLoggerEvents({ site_uid: selectedSiteUid })` (all sites when none selected). A small type/severity filter (optional) + a "muat lebih" or pagination is nice-to-have; a flat recent list (limit default) is acceptable for v1.

Load status + KPIs on mount and on refresh; wrap every call in try/catch so one failing endpoint never blanks the page. Empty state when there are no logger rows yet ("Belum ada logger yang mengirim heartbeat").

- [ ] **Step 2: Build + commit**

Run: `npm run build` → succeeds.
```bash
git add sparing_front/resources/js/Pages/Loggers/Index.vue
git commit -m "feat(fe): Loggers page — KPIs, per-site status, event timeline"
```

---

### Task 5: Dashboard logger-health chip

**Files:** Modify `resources/js/Pages/Dashboard/Index.vue`

- [ ] **Step 1: Implement**

Read the current Dashboard. Add a compact logger-health chip near the KPI row (or in the header area) that calls `getLoggerStatus()` on mount/refresh (try/caught) and shows: all alive → green "Semua logger aktif"; any down → red "N logger mati" linking to `/loggers` (`<router-link to="/loggers">`). Keep it small; do not disturb existing dashboard data logic or the auto-refresh cycle (fold the call into the existing refresh if straightforward, else its own guarded call).

- [ ] **Step 2: Build + commit**

Run: `npm run build` → succeeds.
```bash
git add sparing_front/resources/js/Pages/Dashboard/Index.vue
git commit -m "feat(fe): dashboard logger-health chip"
```

---

### Task 6: Alarm page — "Logger" category + field wording

**Files:** Modify `resources/js/Pages/Alarms/Index.vue`

- [ ] **Step 1: Implement**

Read the Alarm page. In the Kategori filter `<select>`, add `<option value="logger">Logger</option>` alongside the existing compliance/data_quality options. Extend the event-label wording so logger alerts read well: `field === 'logger_down'` → "Logger tidak terjangkau"; `field` starting `sensor_` → "Sensor {NAMA} gagal dibaca" (map ph/tss/debit/cod/nh3n → labels). Give logger-category rows a suitable icon (e.g. `fa-microchip`) like the data_quality wrench. Do not change the follow-up workflow or pagination.

- [ ] **Step 2: Build + commit**

Run: `npm run build` → succeeds.
```bash
git add sparing_front/resources/js/Pages/Alarms/Index.vue
git commit -m "feat(fe): Logger alarm category filter + field wording"
```

---

### Task 7: History op_status badge

**Files:** Modify `resources/js/Pages/History/Index.vue`

- [ ] **Step 1: Implement**

Read the History page. In raw mode, where each row's values render, when `row.op_status` is non-null show a badge INSTEAD of (or alongside) the numeric cells: `-1`→"Berhenti", `-2`→"Kalibrasi", `-3`→"Rusak" (use the offline/teal-soft palette, not danger — these are intentional states, not failures). The parameter values on such rows are null, so display the badge in place of "—". A concise approach: a computed `opStatusLabel(row)` and, in the value columns or a dedicated first data column, render the badge when set. Keep the existing Validasi column and interval logic intact; op_status rows are already excluded from aggregation server-side.

- [ ] **Step 2: Build + commit**

Run: `npm run build` → succeeds.
```bash
git add sparing_front/resources/js/Pages/History/Index.vue
git commit -m "feat(fe): History badge for operational-status (Kalibrasi/Berhenti/Rusak) rows"
```

---

### Task 8: Final build, deploy, verify

- [ ] **Step 1: Clean production build**

Run (from `sparing_front/`): `npm run build` → succeeds; note the `dist/assets/index-*.js` hash.

- [ ] **Step 2: Merge to main + deploy**

From repo root:
```bash
git checkout main && git merge --no-ff <branch> -m "Merge logger-monitoring frontend"
git push origin main
ssh mitramutiara-prod "sudo bash /opt/sparing/repo/scripts/deploy.sh frontend"
```
Expected: deploy prints the new bundle and completes.

- [ ] **Step 3: Verify on prod**

Load `https://sparingapp.mitramutiara.co.id`, log in, and confirm: the `/loggers` page renders (empty "belum ada logger" state is correct until the logger app from Plan 2 is deployed and sends its first heartbeat); the sidebar Logger item appears; the Dashboard chip shows; the Alarm category filter has "Logger"; History still builds. Report anything broken.

---

## Self-Review Notes

- **Spec coverage (Part 3):** §3.1 `/loggers` page → Tasks 2,3,4 (KPIs, per-site table with sensor dots + resources, event timeline with crash-vs-clean distinction); §3.2 integration → Task 5 (dashboard chip), Task 6 (Alarm category), Task 7 (History badge). Sidebar pill → Task 2.
- **Backend contract:** `getLoggerStatus` bare array; `getLoggerEvents` bare array without `page`; logger alarms ride the existing `/alerts` (`category:'logger'`); `op_status` on `/data` rows. All viewer-scoped server-side already.
- **No test infra:** every task gates on `npm run build`; consistent with prior frontend work.
- **Resilience:** every logger call is try/caught so an endpoint hiccup never blanks a page; the page shows an honest empty state until the first heartbeat (Plan 2 deploy) lands.
- **Reuses v2 components/tokens** — no new visual language; op_status badge uses the intentional-state (teal/gray) palette, not the failure (danger) palette.
```
