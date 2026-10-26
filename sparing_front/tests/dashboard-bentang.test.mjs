import assert from 'node:assert/strict';
import test from 'node:test';
import { fileURLToPath } from 'node:url';
import { resolve } from 'node:path';
import { createSSRApp, h } from 'vue';
import { renderToString } from '@vue/server-renderer';
import { bandState, monthCompliance } from '../resources/js/Utils/dashboardStatus.js';

process.env.BROWSERSLIST_IGNORE_OLD_DATA = 'true';
process.env.VITE_DEBUG = 'false';

const projectRoot = fileURLToPath(new URL('..', import.meta.url));
let vite;

test.before(async () => {
  const [{ default: vue }, { createServer }] = await Promise.all([import('@vitejs/plugin-vue'), import('vite')]);
  vite = await createServer({
    appType: 'custom',
    configFile: false,
    logLevel: 'silent',
    plugins: [vue()],
    resolve: { alias: { '@': resolve(projectRoot, 'resources/js') } },
    root: projectRoot,
    server: { middlewareMode: true },
  });
});

test.after(async () => { await vite?.close(); });

const load = async (name) => (await vite.ssrLoadModule(`/resources/js/Components/Dashboard/${name}.vue`)).default;

async function render(component, props = {}, slots = {}) {
  const app = createSSRApp({ render: () => h(component, props, slots) });
  app.component('router-link', { setup(_props, { slots: inner }) { return () => h('a', inner.default?.()); } });
  return renderToString(app);
}

const text = (html) => html.replace(/<!--[\s\S]*?-->|<[^>]+>/g, ' ').replace(/\s+/g, ' ');

const NOW = Date.parse('2026-10-27T07:05:00Z');
const RULES = { tss: { field: 'tss', danger_min: null, danger_max: 200, is_active: true } };
const OCTOBER = Array.from({ length: 31 }, (_, index) => ({
  date: `2026-10-${String(index + 1).padStart(2, '0')}`,
  status: index === 17 ? 'violation' : 'ok',
}));
const bandFor = (latest, extra = {}) => bandState({ rules: RULES, latest, todayStatus: 'ok', now: NOW, ...extra });

test('StatusBand says "Patuh hari ini" with the month and today\'s completeness', async () => {
  const StatusBand = await load('StatusBand');
  const html = await render(StatusBand, {
    band: bandFor({ ts: '2026-10-27T06:50:00Z', tss: 46 }),
    month: monthCompliance(OCTOBER, '2026-10-27'),
    completenessPct: 96.7,
    completenessAsOf: '14:00',
    completenessSegments: { received: 417, missing: 18, notYet: 285, total: 720, receivedPct: 57.9, missingPct: 2.5, notYetPct: 39.6 },
    siteLabel: 'IPAL Utama · PT Tirta',
    dateLabel: 'Senin, 27 Okt',
  });
  assert.match(html, /aria-label="Status kepatuhan"/);
  assert.match(html, /Patuh hari ini/);
  assert.match(html, /Kepatuhan Oktober/);
  assert.match(html, /96,3%/);
  assert.match(text(html), /26 dari 27 hari patuh/);
  assert.equal(html.match(/<li\b/g)?.length, 31);
  assert.match(html, /96,7%/);
  assert.match(html, /s\.d\. 14:00/);
  assert.match(text(html), /417 masuk · 18 hilang · 285 belum waktunya/);
  assert.doesNotMatch(html, /Catat tindak lanjut/);
});

test('StatusBand turns to a breach with the reading, its limit and a follow-up for operators', async () => {
  const StatusBand = await load('StatusBand');
  const band = bandFor({ ts: '2026-10-27T06:50:00Z', tss: 212 }, {
    activeAlerts: [{ id: 7, field: 'tss', category: 'compliance', triggered_at: '2026-10-27T02:20:00Z' }],
  });
  const operator = await render(StatusBand, { band, canFollowup: true, timezone: 'Asia/Jakarta' });
  assert.match(operator, /TSS melewati baku mutu/);
  assert.match(text(operator), /TSS 212 mg\/L \(batas 200\) · sejak 09:20/);
  assert.match(operator, /Catat tindak lanjut/);
  const viewer = await render(StatusBand, { band, canFollowup: false });
  assert.doesNotMatch(viewer, /Catat tindak lanjut/);
});

test('StatusBand names stale data, a breach earlier today and a site without limits', async () => {
  const StatusBand = await load('StatusBand');
  const stale = await render(StatusBand, { band: bandFor({ ts: '2026-10-27T01:00:00Z', tss: 46 }) });
  assert.match(stale, /Data terhenti sejak/);
  const none = await render(StatusBand, { band: bandFor(null) });
  assert.match(none, /Belum ada data/);
  const earlier = await render(StatusBand, { band: bandFor({ ts: '2026-10-27T06:50:00Z', tss: 46 }, { todayStatus: 'violation' }) });
  assert.match(earlier, /Sempat melewati baku mutu hari ini/);
  const unjudged = await render(StatusBand, { band: bandFor({ ts: '2026-10-27T06:50:00Z', tss: 46 }, { todayStatus: null }) });
  assert.match(unjudged, /Bacaan terakhir dalam baku mutu/);
  assert.doesNotMatch(unjudged, /Patuh hari ini/);
  const noRules = await render(StatusBand, { band: bandState({ rules: {}, latest: null }) });
  assert.match(noRules, /Baku mutu belum diatur/);
  assert.match(noRules, /Kepatuhan bulan ini/);
  assert.match(noRules, /Belum ada hari yang dinilai/);
});
