# UI v2 Upgrade — Frontend Implementation Plan (Plan 2 of 2)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restructure the whole Vue frontend to the v2 prototype — app shell (grouped sidebar + utility strip + breadcrumb/topbar + footer), two-panel Login, richer Dashboard (KPIs from real stats, parameter tiles with sparklines, status table, alarm feed), a dedicated Alarm page with the mandatory-note follow-up workflow, validation-aware History with interval aggregation, compliance analytics with a daily heatmap, and restyled Reports/Users/Settings.

**Architecture:** Presentation-layer rework on top of the already-deployed v2 backend (`/stats/*`, `/alerts` filters+pagination+followup, `/data?interval=`, `quality_flag`). Design tokens (teal/ink, Source Sans 3 / IBM Plex Mono) already shipped in `tailwind.config.js` + `resources/css/app.css`. Data/route logic is stable; this plan changes components and wiring. The prototype `sparing-ui-v2.html` (repo root) is the visual source of truth — port its markup, adapting content to this app's reality (multi-site Mitra Mutiara, WIB, real data, roles admin/operator/viewer, no NIK/forecast/KLHK-delivery/multi-channel-notif — those are backlog C).

**Tech Stack:** Vue 3 `<script setup>`, vue-router, Tailwind, ApexCharts (already a dep), axios via `useApi()`. No JS test infra — the gate for every task is `npm run build` (from `sparing_front/`) succeeding with no errors.

**Reference spec:** `docs/superpowers/specs/2026-07-18-ui-v2-upgrade-design.md` (Part 2). **Prototype:** `sparing-ui-v2.html`.

**Conventions:** frontend commands run from `c:\Users\nurch\OneDrive\Documents\project\sparingV1.1\sparing_front`; git from repo root. Windows; Git Bash available. Every page uses the existing `useApi()` composable — never call axios directly. Keep existing composables (`useAuth`, `useToast`, `useConfirm`) and their call sites working. WIB rendering uses the existing `helpers.js` (`parseUTC`, `formatDate`, `formatTime`) — do not reintroduce `new Date()` on raw UTC strings.

---

## File Structure

- Modify: `resources/js/Composables/useApi.js` (new endpoints; `resolveAlert(id, note)`)
- Modify: `resources/js/Layouts/AppLayout.vue`, `resources/js/Components/Sidebar.vue`, `resources/js/Components/Header.vue` (retired → utility strip), `resources/js/app.js` (add `/alarms` route)
- Create: `resources/js/Components/PageHeader.vue`, `resources/js/Components/UtilityStrip.vue`, `resources/js/Components/AlertFollowupModal.vue`, `resources/js/Components/Sparkline.vue`, `resources/js/Components/ComplianceHeatmap.vue`, `resources/js/Pages/Alarms/Index.vue`
- Modify pages: `Auth/Login.vue`, `Dashboard/Index.vue`, `History/Index.vue`, `Analytics/Index.vue`, `Reports/Index.vue`, `Users/Index.vue`, `Settings/Index.vue`
- Modify: `resources/js/Components/AlertDropdown.vue` (category filter aware; unchanged API shape)

---

### Task 0: Baseline — build is green

- [ ] **Step 1: Confirm a clean build**

Run (from `sparing_front/`):
```bash
npm run build
```
Expected: build completes, prints the `dist/assets/index-*.js` bundle name, exit 0. If it fails on a pre-existing error, stop and report before changing anything.

---

### Task 1: API layer — new endpoints + note-aware resolve

**Files:** Modify `resources/js/Composables/useApi.js`

- [ ] **Step 1: Add the new methods**

In `useApi.js`, replace the two lines:
```js
  const acknowledgeAlert = (alertId) => request('PATCH', `/alerts/${alertId}/acknowledge`);
  const resolveAlert = (alertId) => request('PATCH', `/alerts/${alertId}/resolve`);
```
with:
```js
  const acknowledgeAlert = (alertId) => request('PATCH', `/alerts/${alertId}/acknowledge`);
  const followupAlert = (alertId, note) => request('PATCH', `/alerts/${alertId}/followup`, { note: note ?? null });
  const resolveAlert = (alertId, note) => request('PATCH', `/alerts/${alertId}/resolve`, { note });
```

Add stats methods just before the `return {` block:
```js
  // Stats (v2 dashboard/analytics)
  const getCompliance = (days = 30) => request('GET', '/stats/compliance', null, { params: { days } });
  const getCompleteness = (hours = 24) => request('GET', '/stats/completeness', null, { params: { hours } });
  const getComplianceDaily = (month) => request('GET', '/stats/compliance-daily', null, { params: { month } });
```

Add all four names to the returned object (in the Alerts group add `followupAlert`; add a `// Stats` group with `getCompliance, getCompleteness, getComplianceDaily`). `getData` already forwards `params`, so `interval` needs no change.

- [ ] **Step 2: Build**

Run: `npm run build` → Expected: succeeds. (No usages yet; this only adds methods.)

- [ ] **Step 3: Commit**

```bash
git add sparing_front/resources/js/Composables/useApi.js
git commit -m "feat(fe): api methods for stats + alert followup/resolve-with-note"
```

---

### Task 2: App shell v2 (sidebar, utility strip, page header, footer)

**Files:** Create `PageHeader.vue`, `UtilityStrip.vue`; modify `Sidebar.vue`, `AppLayout.vue`; `Header.vue` becomes unused (leave file, stop importing it).

- [ ] **Step 1: Create `resources/js/Components/PageHeader.vue`**

A reusable breadcrumb + title + actions row (prototype `.crumb` + `.topbar`). Props: `crumb` (array of strings, last is bold current), `title` (string), `subtitle` (string). Slot `actions` renders right-aligned buttons. Use existing tokens (`text-ink`, `text-muted`, etc. — mirror the prototype's `.crumb`/`.topbar`/`.topbar h2`/`.topbar p`). Include a mobile menu button that `emit('toggle-sidebar')`.

```vue
<template>
  <div>
    <nav class="text-xs text-muted mb-3">
      <template v-for="(c, i) in crumb" :key="i">
        <span v-if="i < crumb.length - 1">{{ c }} / </span>
        <b v-else class="text-ink font-semibold">{{ c }}</b>
      </template>
    </nav>
    <div class="flex items-end justify-between gap-4 flex-wrap mb-5">
      <div class="flex items-center gap-3">
        <button class="md:hidden btn-ghost px-3 py-2 rounded-md border" @click="$emit('toggle-sidebar')" aria-label="Menu">☰</button>
        <div>
          <h2 class="text-[19px] font-bold text-ink">{{ title }}</h2>
          <p v-if="subtitle" class="text-muted text-[12.5px] mt-0.5">{{ subtitle }}</p>
        </div>
      </div>
      <div class="flex gap-2 items-center"><slot name="actions" /></div>
    </div>
  </div>
</template>
<script setup>
defineProps({ crumb: { type: Array, default: () => [] }, title: String, subtitle: String });
defineEmits(['toggle-sidebar']);
</script>
```

- [ ] **Step 2: Create `resources/js/Components/UtilityStrip.vue`**

Top strip (prototype `.util`): server status dot (poll `healthCheck()` every 60s → green/red), "Sinkronisasi terakhir" (accept a `lastSync` prop, formatted via `formatTime`), a live WIB clock (reuse the prototype clock logic but label **WIB** and compute UTC+7), and — on the right — a slot for the alert bell. Mount `AlertDropdown` via the slot from AppLayout so its existing logic is untouched.

```vue
<template>
  <div class="bg-white border-b border-line px-6 py-1.5 flex gap-4 items-center text-[11.5px] text-muted">
    <span><span class="inline-block w-[7px] h-[7px] rounded-full mr-1.5" :class="serverOk ? 'bg-ok' : 'bg-bad'"></span>Server: {{ serverOk ? 'normal' : 'gangguan' }}</span>
    <span class="text-line-2">|</span>
    <span v-if="lastSync">Sinkronisasi terakhir: <span class="font-mono">{{ lastSync }}</span></span>
    <span class="ml-auto flex items-center gap-3">
      <span class="font-mono text-[11px]">{{ clock }}</span>
      <slot name="bell" />
    </span>
  </div>
</template>
<script setup>
import { ref, onMounted, onUnmounted } from 'vue';
import { useApi } from '@/Composables/useApi';
defineProps({ lastSync: { type: String, default: '' } });
const { healthCheck } = useApi();
const serverOk = ref(true);
const clock = ref('');
let clockTimer, healthTimer;
const hari = ['Min','Sen','Sel','Rab','Kam','Jum','Sab'];
const bulan = ['Jan','Feb','Mar','Apr','Mei','Jun','Jul','Agu','Sep','Okt','Nov','Des'];
function tick() {
  const now = new Date(Date.now() + (7 * 60 + new Date().getTimezoneOffset()) * 60000); // UTC+7
  const p = (n) => String(n).padStart(2, '0');
  clock.value = `${hari[now.getDay()]}, ${now.getDate()} ${bulan[now.getMonth()]} ${now.getFullYear()} · ${p(now.getHours())}:${p(now.getMinutes())}:${p(now.getSeconds())} WIB`;
}
async function checkHealth() { try { await healthCheck(); serverOk.value = true; } catch { serverOk.value = false; } }
onMounted(() => { tick(); clockTimer = setInterval(tick, 1000); checkHealth(); healthTimer = setInterval(checkHealth, 60000); });
onUnmounted(() => { clearInterval(clockTimer); clearInterval(healthTimer); });
</script>
```

- [ ] **Step 3: Rewrite `resources/js/Components/Sidebar.vue`**

Port the prototype `.sidebar`: ink background, logo head, grouped nav with uppercase labels — **Pemantauan** (Dashboard → `/dashboard`; Alarm → `/alarms`, with a red pill showing active alert count from `getAlertCount('active')`, polled every 60s), **Data** (Riwayat → `/history`, Analisis → `/analytics`, Laporan → `/reports`), **Administrasi** (Lokasi → `/sites`, Perangkat → `/devices` [hide for viewer], Pengguna → `/users` [admin only], Pengaturan → `/settings`). Active item = solid white bg + ink text (`router-link-active`). Sidebar foot: avatar initials + name + role + **Keluar** button calling the existing logout flow (reuse whatever `Header.vue`/`useAuth` does today — read `useAuth.js` and replicate). Role gating: read role via `useAuth` (`isAdmin`, and a viewer check). Keep the existing mobile slide behavior (`is-open` prop, `@close` emit) that AppLayout already passes.

Preserve the exact nav-item markup/classes from the prototype (`.nav-item`, `.nav-label`, `.pill`, `.sb-foot`, `.avatar`, `.btn-logout`) translated to Tailwind or a scoped `<style>` copied from the prototype.

- [ ] **Step 4: Rewrite `resources/js/Layouts/AppLayout.vue`**

Compose: `<Sidebar>` (unchanged props), then a right column containing `<UtilityStrip :last-sync="lastSync"><template #bell><AlertDropdown/></template></UtilityStrip>`, then `<main><slot/></main>`, then the prototype `.app-foot` footer (version, "Sesi berakhir otomatis…", helpdesk, "Zona waktu tampilan: WIB (UTC+7)"). Drop the `<Header>` import. Keep `sidebarOpen`/`isMobile`/`checkScreen`/`toggleSidebar`. Provide `toggle-sidebar` down to `PageHeader` via the router-view slot is not available — instead expose a simple approach: keep the mobile menu button inside `UtilityStrip` OR `PageHeader` and have it emit up; simplest is the menu button living in `PageHeader` and each page binding `@toggle-sidebar` — but AppLayout owns `sidebarOpen`. Resolve by having AppLayout provide a toggle via Vue `provide('toggleSidebar', toggleSidebar)`, and `PageHeader` `inject('toggleSidebar', () => {})` to call on its menu button (replace the emit in Step 1 with the injected call). Update PageHeader Step 1 accordingly if you choose provide/inject.

`lastSync`: AppLayout may leave it blank initially (dashboard sets its own). Acceptable to pass `''`.

- [ ] **Step 5: Build**

Run: `npm run build` → Expected: succeeds, no unresolved imports (Header no longer imported).

- [ ] **Step 6: Commit**

```bash
git add sparing_front/resources/js/Components/PageHeader.vue sparing_front/resources/js/Components/UtilityStrip.vue sparing_front/resources/js/Components/Sidebar.vue sparing_front/resources/js/Layouts/AppLayout.vue
git commit -m "feat(fe): v2 app shell — grouped sidebar, utility strip, page header, footer"
```

---

### Task 3: Add the `/alarms` route

**Files:** Modify `resources/js/app.js`

- [ ] **Step 1: Register the route**

In `app.js`, add the import `import Alarms from './Pages/Alarms/Index.vue';` and, after the `dashboard` route object, insert:
```js
    {
      path: '/alarms',
      name: 'alarms',
      component: Alarms,
      meta: { requiresAuth: true },
    },
```

- [ ] **Step 2: Create a stub page so the build resolves**

Create `resources/js/Pages/Alarms/Index.vue` with a minimal valid SFC (real content in Task 5):
```vue
<template><AppLayout><PageHeader :crumb="['Beranda','Alarm']" title="Alarm" /></AppLayout></template>
<script setup>
import AppLayout from '@/Layouts/AppLayout.vue';
import PageHeader from '@/Components/PageHeader.vue';
</script>
```

- [ ] **Step 3: Build + commit**

Run: `npm run build` → succeeds.
```bash
git add sparing_front/resources/js/app.js sparing_front/resources/js/Pages/Alarms/Index.vue
git commit -m "feat(fe): register /alarms route with stub page"
```

---

### Task 4: Alarm page + follow-up modal

**Files:** Create `resources/js/Components/AlertFollowupModal.vue`; rewrite `resources/js/Pages/Alarms/Index.vue`

- [ ] **Step 1: Create `AlertFollowupModal.vue`**

Modal with two modes via a `mode` prop: `'followup'` (note optional) and `'resolve'` (note **required** — submit disabled while the trimmed note is empty). Props: `open` (bool), `mode` (string), `alert` (object|null). Emits `close` and `submit` (payload: `{ note }`). Render the alert summary (site, field label, value) read-only, a `<textarea>` for the note, and buttons. For `resolve`, show the footnote "Catatan wajib diisi sebelum alarm ditutup." Reuse toast on the parent, not here.

```vue
<template>
  <div v-if="open" class="fixed inset-0 z-50 flex items-center justify-center bg-ink/40 p-4" @click.self="$emit('close')">
    <div class="bg-white rounded-lg border border-line w-full max-w-md p-5">
      <h3 class="text-[15px] font-bold text-ink mb-1">{{ mode === 'resolve' ? 'Selesaikan alarm' : 'Tindak lanjut alarm' }}</h3>
      <p v-if="alert" class="text-[12.5px] text-muted mb-3">{{ alert.site_name }} · {{ alert.field }} = {{ alert.value }}</p>
      <label class="block text-[12.5px] font-semibold text-ink mb-1">
        Catatan tindak lanjut <span v-if="mode==='resolve'" class="text-bad">*</span>
      </label>
      <textarea v-model="note" rows="4" class="w-full border border-line-2 rounded-md p-2 text-sm" :placeholder="mode==='resolve' ? 'Wajib diisi…' : 'Opsional…'"></textarea>
      <p v-if="mode==='resolve'" class="text-[11.5px] text-muted mt-1">Catatan wajib diisi sebelum alarm dapat ditutup (SOP-ENV).</p>
      <div class="flex justify-end gap-2 mt-4">
        <button class="btn-ghost px-3 py-2 rounded-md border text-sm" @click="$emit('close')">Batal</button>
        <button class="btn-primary px-3 py-2 rounded-md text-sm text-white bg-teal disabled:opacity-50"
                :disabled="mode==='resolve' && !note.trim()"
                @click="$emit('submit', { note: note.trim() })">
          {{ mode === 'resolve' ? 'Tutup alarm' : 'Simpan' }}
        </button>
      </div>
    </div>
  </div>
</template>
<script setup>
import { ref, watch } from 'vue';
const props = defineProps({ open: Boolean, mode: { type: String, default: 'followup' }, alert: Object });
defineEmits(['close', 'submit']);
const note = ref('');
watch(() => props.open, (v) => { if (v) note.value = ''; });
</script>
```

- [ ] **Step 2: Rewrite `resources/js/Pages/Alarms/Index.vue`**

Port the prototype Alarm section (`#sec-alarm`): `PageHeader` (crumb `['Beranda','Alarm']`, title "Alarm & Riwayat Kejadian", subtitle about mandatory notes), filterbar (Tingkat = threshold_type semua/danger/warning; Kategori = category compliance/data_quality; Lokasi = site select from `getSites()`; Status = active/acknowledged/resolved/all; Terapkan button), a table (No, Waktu via `formatDate`+`formatTime`, Lokasi = site_name, Kejadian = reuse AlertDropdown's field/anomaly wording — extract a small helper or inline map, Nilai mono, Durasi = triggered→(resolved_at||now), PIC = `followup_by_name || '—'`, Status badge, action). Load via `getAlerts({ page, per_page: 20, status, category, threshold_type, site_uid })` (pagination wrapper mode). Actions per row by status: `active` → **Tindak lanjut** (opens modal mode `followup`) + **Selesaikan** (modal `resolve`); `acknowledged` → **Selesaikan**; `resolved` → **Catatan** (read-only view of `followup_note`). On modal submit call `followupAlert(id, note)` or `resolveAlert(id, note)`, toast success/error, reload the page list. Pagination controls (prototype `.pager`) using `total`/`page`/`per_page`. Gate the action buttons to admin/operator via `useAuth` (viewers see status only — backend also enforces 403).

Use the existing `useToast` for feedback and `useApi` for all calls. Keep it a single `<script setup>`; reuse the prototype's badge classes (`b-bad/b-warn/b-off/b-teal`) already in the design system.

- [ ] **Step 3: Build**

Run: `npm run build` → succeeds.

- [ ] **Step 4: Commit**

```bash
git add sparing_front/resources/js/Components/AlertFollowupModal.vue sparing_front/resources/js/Pages/Alarms/Index.vue
git commit -m "feat(fe): Alarm page with mandatory-note follow-up workflow"
```

---

### Task 5: Sparkline component + Dashboard v2

**Files:** Create `resources/js/Components/Sparkline.vue`; rewrite `resources/js/Pages/Dashboard/Index.vue`

- [ ] **Step 1: Create `resources/js/Components/Sparkline.vue`**

Pure inline-SVG sparkline (no chart lib — matches the prototype `.ptile svg`). Props: `points` (array of numbers), `threshold` (number|null), `color` (string, default teal). Compute a `path` `d` scaling points into a 120×34 viewBox; draw a dashed red threshold line if `threshold` is set and within range.

```vue
<template>
  <svg viewBox="0 0 120 34" preserveAspectRatio="none" class="w-full h-[34px] mt-1.5">
    <line v-if="threshLine !== null" :x1="0" :y1="threshLine" :x2="120" :y2="threshLine"
          stroke="#B03030" stroke-width="1" stroke-dasharray="3 3" opacity="0.6" />
    <path v-if="d" :d="d" fill="none" :stroke="color" stroke-width="1.8" />
  </svg>
</template>
<script setup>
import { computed } from 'vue';
const props = defineProps({ points: { type: Array, default: () => [] }, threshold: { type: Number, default: null }, color: { type: String, default: '#0E7C86' } });
const bounds = computed(() => {
  const vals = props.points.filter((v) => v != null);
  const extra = props.threshold != null ? [props.threshold] : [];
  const all = [...vals, ...extra];
  if (!all.length) return null;
  const min = Math.min(...all), max = Math.max(...all);
  return { min, max, span: (max - min) || 1 };
});
const y = (v, b) => 30 - ((v - b.min) / b.span) * 26 + 2; // 2..30 padded
const d = computed(() => {
  const b = bounds.value; if (!b || props.points.length < 2) return '';
  const n = props.points.length;
  return props.points.map((v, i) => `${i === 0 ? 'M' : 'L'}${(i / (n - 1)) * 120},${y(v ?? b.min, b)}`).join(' ');
});
const threshLine = computed(() => (props.threshold != null && bounds.value ? y(props.threshold, bounds.value) : null));
</script>
```

- [ ] **Step 2: Rewrite `resources/js/Pages/Dashboard/Index.vue`**

Port the prototype Dashboard (`#sec-dashboard`) on top of the existing dashboard's data loading (read the current file first; keep its site-selection, `getSites`, latest-data, sensor-health, auto-refresh, and the dual-axis chart already shipped). Add:
- **KPI row (4 cards):** Perangkat online `X/Y` (from existing device status logic already in the page); Kepatuhan 30 hari from `getCompliance(30)` → `compliance_pct` + delta note (`delta_pct` sign → `n-ok`/`n-bad`); Alarm aktif from `getAlertCount('active')` + worst-alert note (optional, from `getAlerts({status:'active'})[0]`); Kelengkapan hari ini from `getCompleteness(24)` → `pct`.
- **Param strip:** one `.ptile` per in-scope parameter for the selected site — value (mono), unified status badge (reuse the existing `SensorCard`/`cardStatus` logic or `getSensorStatus` from helpers), baku-mutu line from the site's AlertRules (`getAlertRules(siteUid)`), and `<Sparkline :points="last2h[field]" :threshold="dangerMax[field]" />` where `last2h` comes from a `getData({ site_uid, interval:'raw', date_from: <2h ago ISO>, fields:<field> })` call (or reuse latest metrics already loaded). Left border color by status.
- **Status table + Alarm feed + Kelengkapan card** per prototype right column: status table over sites (site, company, update via `formatTime`, pH, TSS, unified badge); alarm feed = top 3 of `getAlerts({status:'active'})` with sevbar colors + link to `/alarms`; completeness meter bar.

Set `lastSync` for the shell from the newest loaded timestamp if AppLayout is refactored to accept it; otherwise leave the strip's default. Keep all WIB formatting via `helpers.js`. Do NOT reintroduce any `Math.random` placeholder.

- [ ] **Step 3: Build + commit**

Run: `npm run build` → succeeds.
```bash
git add sparing_front/resources/js/Components/Sparkline.vue sparing_front/resources/js/Pages/Dashboard/Index.vue
git commit -m "feat(fe): Dashboard v2 — real KPI stats, parameter tiles with sparklines, status table + alarm feed"
```

---

### Task 6: History v2 — interval select + validation column

**Files:** Modify `resources/js/Pages/History/Index.vue`

- [ ] **Step 1: Implement**

Read the current History page first. Add to the filterbar an **Interval** `<select>` (Data mentah `raw` / Rerata per jam `hourly` / Rerata harian `daily`) bound to a `interval` ref, passed to `getData({ ..., interval })`. When `interval==='raw'`: render a **Validasi** column — badge Valid (`quality_flag == null`) / Anomali (`quality_flag === 'anomaly'`, use `b-warn`), and a footnote explaining anomalies are excluded from averages but retained for audit. When aggregated: hide raw-only columns' per-row semantics and show a **Jumlah data** column from the bucket `count`; the row `ts` is the bucket start (format via `helpers.js`). Keep existing export (CSV/PDF/Excel) working — for raw export include `quality_flag`. Preserve the existing date range + site + parameter filters and pagination (the aggregated response is the same `{total,page,per_page,items}` shape).

- [ ] **Step 2: Build + commit**

Run: `npm run build` → succeeds.
```bash
git add sparing_front/resources/js/Pages/History/Index.vue
git commit -m "feat(fe): History v2 — interval aggregation + validation column"
```

---

### Task 7: Compliance heatmap + Analytics v2

**Files:** Create `resources/js/Components/ComplianceHeatmap.vue`; modify `resources/js/Pages/Analytics/Index.vue`

- [ ] **Step 1: Create `ComplianceHeatmap.vue`**

Port the prototype `.heat` calendar grid. Prop: `days` (array of `{date, status}` from `getComplianceDaily`). Render one cell per day, colored by status (`ok`→bg-ok, `warning`→bg-warn, `violation`→bg-bad, `none`→bg-off/`#DCE4E5`), `title` tooltip with the date + status label. Include the legend row (Patuh/Peringatan/Pelampauan/Belum berjalan) from the prototype.

```vue
<template>
  <div>
    <div class="grid gap-[3px]" :style="{ gridTemplateColumns: 'repeat(31, 1fr)' }">
      <i v-for="d in days" :key="d.date" :title="`${d.date} — ${label(d.status)}`"
         class="aspect-square rounded-[2px]" :class="cls(d.status)"></i>
    </div>
    <div class="flex gap-3.5 text-[11.5px] text-muted mt-2.5">
      <span><i class="inline-block w-2.5 h-2.5 rounded-[2px] bg-ok mr-1.5 align-[-1px]"></i>Patuh penuh</span>
      <span><i class="inline-block w-2.5 h-2.5 rounded-[2px] bg-warn mr-1.5 align-[-1px]"></i>Ada peringatan</span>
      <span><i class="inline-block w-2.5 h-2.5 rounded-[2px] bg-bad mr-1.5 align-[-1px]"></i>Ada pelampauan</span>
      <span><i class="inline-block w-2.5 h-2.5 rounded-[2px] mr-1.5 align-[-1px]" style="background:#DCE4E5"></i>Belum berjalan</span>
    </div>
  </div>
</template>
<script setup>
defineProps({ days: { type: Array, default: () => [] } });
const cls = (s) => ({ ok: 'bg-ok', warning: 'bg-warn', violation: 'bg-bad' }[s] || '');
const styleNone = '';
const label = (s) => ({ ok: 'patuh', warning: 'peringatan', violation: 'pelampauan', none: 'belum berjalan' }[s] || s);
</script>
<style scoped>i { opacity: .85 } i:empty { }</style>
```
(For `none`, `cls` returns '' — add an inline fallback bg via a `:style` on the cell when status is `none`, or a `.bg-off` utility. Keep it simple: bind `:style="d.status==='none' ? 'background:#DCE4E5' : ''"`.)

- [ ] **Step 2: Modify `resources/js/Pages/Analytics/Index.vue`**

Read the current Analytics page first. Restyle into the prototype grid (`#sec-analisis`): keep the existing trend chart + `analysis.js` stats; add the right-column **Statistik** card (rerata/min/max/p95/simpangan + kelengkapan from `getCompleteness` + "data dikecualikan" = count of anomaly rows if available) and **Catatan sistem** card fed by the existing `generateRecommendations()`/`analyzeParameter()` output rendered as sevbar items. Add a full-width **Rekap kepatuhan harian** card containing `<ComplianceHeatmap :days="daily" />` where `daily = (await getComplianceDaily(month)).days` for the selected month (default current `YYYY-MM`). **No forecast / prediction line** (backlog C) — omit any dashed prediction path from the prototype.

- [ ] **Step 3: Build + commit**

Run: `npm run build` → succeeds.
```bash
git add sparing_front/resources/js/Components/ComplianceHeatmap.vue sparing_front/resources/js/Pages/Analytics/Index.vue
git commit -m "feat(fe): Analytics v2 — stats panel, system notes, daily compliance heatmap"
```

---

### Task 8: Restyle Login, Reports, Users, Settings

**Files:** Modify `Auth/Login.vue`, `Reports/Index.vue`, `Users/Index.vue`, `Settings/Index.vue`

- [ ] **Step 1: Login v2** (`Auth/Login.vue`)

Port the prototype two-panel login (`#login`): left white card with the existing email+password auth (keep the current `useAuth`/`login` logic and error handling — **no NIK**, no "remember device" backend), show/hide password, note box, footer (version + supported browsers). Right ink panel: tagline + lead copy + **static** facts (parameters monitored, 2-minute interval) — no live numbers (unauthenticated). Right panel hidden on mobile (`md:hidden`). Read the current Login first and preserve its submit/redirect behavior.

- [ ] **Step 2: Reports v2** (`Reports/Index.vue`)

Light restyle to the prototype archive/KPI pattern; keep the existing generate + PDF/Excel flows intact. Add a KPI card for month completeness via `getCompleteness(720)`. Use `PageHeader`.

- [ ] **Step 3: Users v2** (`Users/Index.vue`)

Keep existing CRUD + site-assignment. Add role chips (admin=teal, operator=amber, viewer=gray), a search + role/status filter bar, and a static **Matriks hak akses** card reflecting real capabilities (admin/operator/viewer rows: view dashboard, export riwayat, tindak lanjut alarm, konfigurasi site, susun laporan, kelola user). Use `PageHeader`.

- [ ] **Step 4: Settings v2** (`Settings/Index.vue`)

Restyle profile + change-password into the prototype setrow pattern. Add an **Ambang peringatan dini** section that reuses the existing AlertRule editor/API (`getAlertRules`/`updateAlertRule`) per selected site. **Kanal notifikasi**: Email row shown active (informational); WhatsApp/Telegram/SMS rows rendered disabled with a "Segera" badge (backlog C — not wired). Use `PageHeader`.

- [ ] **Step 5: Build after each page, then commit**

Run `npm run build` after each file (catch errors early). Once all four build clean:
```bash
git add sparing_front/resources/js/Pages/Auth/Login.vue sparing_front/resources/js/Pages/Reports/Index.vue sparing_front/resources/js/Pages/Users/Index.vue sparing_front/resources/js/Pages/Settings/Index.vue
git commit -m "feat(fe): v2 restyle — Login two-panel, Reports/Users/Settings"
```

---

### Task 9: Final build, deploy frontend, verify

- [ ] **Step 1: Clean production build**

Run (from `sparing_front/`): `npm run build` → succeeds; note the `dist/assets/index-*.js` hash.

- [ ] **Step 2: Merge to main + deploy**

From repo root:
```bash
git checkout main && git merge --no-ff <branch> -m "Merge UI v2 frontend"
git push origin main
ssh mitramutiara-prod "sudo bash /opt/sparing/repo/scripts/deploy.sh frontend"
```
Expected: deploy prints the new `bundle: index-*.js` and completes.

- [ ] **Step 3: Verify on prod**

Load `https://sparing.mitramutiara.co.id` (or the configured web root URL) in a browser and confirm: shell renders (grouped sidebar, utility strip, WIB clock), login two-panel, Dashboard KPIs show real numbers, `/alarms` lists alerts and the resolve modal enforces a note, History interval + Validasi column work, Analytics heatmap renders. Report anything broken.

---

## Self-Review Notes

- **Spec coverage (Part 2):** §2.1 shell → Task 2; §2.2 Login → Task 8.1; §2.3 Dashboard → Task 5; §2.4 Alarm page → Tasks 3–4; §2.5 History → Task 6; §2.6 Analytics → Task 7; §2.7 Reports → Task 8.2; §2.8 Users → Task 8.3; §2.9 Settings → Task 8.4. API layer → Task 1.
- **Backend contracts used:** `resolveAlert(id, note)` sends `{note}` (400 if empty — modal prevents that); `getAlerts({page,...})` uses the wrapper shape; bare-list still used by `AlertDropdown` (untouched); `getData({interval})`; `/stats/*` viewer-scoped server-side.
- **No test infra:** every task gates on `npm run build`; there is no JS unit runner in this repo (consistent with prior frontend work).
- **Backlog C honored:** no NIK, no forecast line, no KLHK-delivery panels, notification channels shown disabled "Segera".
- **Prototype is markup source:** `sparing-ui-v2.html` — port sections, adapt content to real multi-site WIB data.
