import assert from 'node:assert/strict';
import test from 'node:test';
import { createSSRApp, h } from 'vue';
import { renderToString } from '@vue/server-renderer';
import { fileURLToPath } from 'node:url';
import { resolve } from 'node:path';
import {
  dayStrip, durationText, loggerAlertTitle, recoveryText, summaryText,
} from '../resources/js/Utils/loggerDiagnosis.js';
import { zoneAbbr } from '../resources/js/Utils/helpers.js';

const NOW = Date.parse('2026-11-04T03:00:00Z'); // 10:00 WIB

test('summary counts states in a fixed order and skips zeros', () => {
  const rows = ['normal', 'down', 'normal', 'attention', 'down', 'normal', 'problem', 'down'].map((state) => ({ state }));
  assert.equal(summaryText(rows), '3 normal · 1 perhatian · 1 bermasalah · 3 mati');
  assert.equal(summaryText([]), 'Belum ada logger');
});

test('durations read like the backend', () => {
  assert.equal(durationText(161), '2 jam 41 menit');
  assert.equal(durationText(1500), '1 hari 1 jam');
  assert.equal(durationText(120), '2 jam');
  assert.equal(durationText(0.4), 'kurang dari 1 menit');
});

test('recovery text names the readings lost by an ended down incident only', () => {
  const base = { kind: 'down', ended_at: '2026-10-29T09:43:00Z', data_expected: 81 };
  assert.equal(recoveryText({ ...base, data_recovered: 79 }), '2 bacaan hilang');
  assert.equal(recoveryText({ ...base, data_recovered: 81 }), '');
  assert.equal(recoveryText({ ...base, data_recovered: 0 }), '81 bacaan hilang');
  assert.equal(recoveryText({ ...base, ended_at: null, data_recovered: 0 }), '');
  assert.equal(recoveryText({ ...base, kind: 'rejected', data_recovered: 0 }), '');
});

test('the 30-day strip sums down minutes per local day', () => {
  const cells = dayStrip([
    { kind: 'down', started_at: '2026-10-29T07:02:00Z', ended_at: '2026-10-29T09:43:00Z' }, // 14:02–16:43 WIB
    { kind: 'down', started_at: '2026-11-01T16:00:00Z', ended_at: '2026-11-01T18:00:00Z' }, // 23:00–01:00 WIB
    { kind: 'down', started_at: '2026-11-02T17:00:00', ended_at: null },                    // naive UTC: 3 Nov 00:00 WIB, still open
    { kind: 'rejected', started_at: '2026-10-29T17:00:00Z', ended_at: '2026-10-30T17:00:00Z' },
  ], { timeZone: 'Asia/Jakarta', now: NOW });
  assert.equal(cells.length, 30);
  assert.equal(cells.at(-1).date, '2026-11-04');
  const day = Object.fromEntries(cells.map((cell) => [cell.date, cell]));
  assert.equal(day['2026-10-29'].minutes, 161);
  assert.equal(day['2026-10-29'].level, 'long');
  assert.equal(day['2026-10-29'].text, '29 Okt: gangguan 2 jam 41 menit');
  assert.equal(day['2026-10-30'].level, 'none');
  assert.equal(day['2026-10-30'].text, '30 Okt: tanpa gangguan');
  assert.equal(day['2026-11-01'].minutes, 60);
  assert.equal(day['2026-11-02'].minutes, 60);
  assert.equal(day['2026-11-03'].level, 'full');
  assert.equal(day['2026-11-04'].minutes, 600);
  assert.equal(day['2026-11-04'].level, 'full'); // the whole day so far
});

test('overlapping down incidents count once in the strip', () => {
  const cells = dayStrip([
    { kind: 'down', started_at: '2026-10-29T07:02:00Z', ended_at: '2026-10-29T09:43:00Z' },
    { kind: 'down', started_at: '2026-10-29T08:00:00Z', ended_at: '2026-10-29T10:00:00Z' },
  ], { timeZone: 'Asia/Jakarta', now: NOW });
  const day = cells.find((cell) => cell.date === '2026-10-29');
  assert.equal(day.minutes, 178); // 07:02–10:00 UTC, not 161 + 120
});

test('logger alarm titles cover the new fields and sensors', () => {
  assert.equal(loggerAlertTitle({ field: 'logger_down' }), 'Logger tidak terjangkau');
  assert.equal(loggerAlertTitle({ field: 'rejected_partial' }), 'Sebagian kiriman ditolak server');
  assert.equal(loggerAlertTitle({ field: 'send_fail_klhk' }), 'Kirim ke KLHK gagal');
  assert.equal(loggerAlertTitle({ field: 'sensor_cod' }), 'Sensor COD gagal dibaca');
  assert.equal(loggerAlertTitle({ field: 'something_new' }), 'Kejadian logger');
});

process.env.BROWSERSLIST_IGNORE_OLD_DATA = 'true';
process.env.VITE_DEBUG = 'false';
const projectRoot = fileURLToPath(new URL('..', import.meta.url));
let vite;

test.before(async () => {
  const [{ default: vue }, { createServer }] = await Promise.all([import('@vitejs/plugin-vue'), import('vite')]);
  vite = await createServer({
    appType: 'custom', configFile: false, logLevel: 'silent', plugins: [vue()],
    resolve: { alias: { '@': resolve(projectRoot, 'resources/js') } },
    root: projectRoot, server: { middlewareMode: true },
  });
});
test.after(async () => { await vite?.close(); });

const load = async (name) => (await vite.ssrLoadModule(`/resources/js/Components/Loggers/${name}.vue`)).default;
function render(component, props = {}) {
  const app = createSSRApp({ render: () => h(component, props) });
  app.component('router-link', { setup(_props, { slots }) { return () => h('a', slots.default?.()); } });
  return renderToString(app);
}
const text = (html) => html.replace(/<!--[\s\S]*?-->|<[^>]+>/g, ' ').replace(/\s+/g, ' ');

const FINDING = {
  code: 'down', kind: 'down', severity: 'danger', since: '2026-11-01T03:12:00+00:00',
  title: 'Tidak melapor sejak 1 Nov 10:12. Internet sudah bermasalah sebelum logger hilang.',
  action: 'Cek di lokasi: logger menyala, lampu modem/internet, lalu restart logger.',
  tech: 'heartbeat terakhir 2026-11-01T03:12:00+00:00 · data terakhir —',
};
const ADMIN_ROW = {
  site_uid: 'WMP09-LOG', site_name: 'WMP 09', timezone: 'Asia/Jakarta', state: 'down',
  headline: FINDING.title, since: FINDING.since, last_heartbeat_at: FINDING.since, last_data_at: null,
  findings: [FINDING, { code: 'send_fail_klhk', kind: 'send_fail_klhk', severity: 'warning', since: null,
    title: 'Kiriman ke KLHK gagal sejak 1 Nov 09:00.', action: 'Tim MM: periksa uid KLHK (uid_2) di konfigurasi logger.', tech: 'last_send_ok_klhk=false' }],
  device: { last_heartbeat_at: FINDING.since, internet_ok: false, buffer_depth: 27, daily_sent: 600,
    last_send_ok_mm: true, last_send_ok_klhk: false, op_status: 0,
    sensors: { ph: true, tss: false, debit: null, cod: null, nh3n: null } },
  tech: { uid: 'WMP09-LOG', logger_version: null, uptime_s: 1205647, consec_fail: 0, cpu_temp: 56.2,
    cpu_pct: 18, mem_pct: 41, disk_pct: 6.5,
    rejections: [{ source: 'post-data', reason: 'bad_signature', count: 3, first_at: FINDING.since, last_at: FINDING.since, last_detail: 'n=30' }] },
};
const VIEWER_ROW = {
  ...ADMIN_ROW,
  findings: ADMIN_ROW.findings.map(({ action, tech, ...rest }) => rest),
  device: undefined, tech: undefined,
};
const INCIDENTS = [{
  id: 7, site_uid: 'WMP09-LOG', kind: 'down', started_at: '2026-10-29T07:02:00+00:00',
  ended_at: '2026-10-29T09:43:00+00:00', duration_min: 161, cause: 'internet',
  cause_detail: 'Internet lokasi putus 2 jam 41 menit; data menyusul 98%.', data_expected: 81, data_recovered: 79,
}];

test('DayStrip speaks every day to screen readers', async () => {
  const DayStrip = await load('DayStrip');
  const html = await render(DayStrip, { cells: dayStrip(INCIDENTS, { now: NOW }) });
  assert.equal((html.match(/<li/g) ?? []).length, 30);
  assert.match(text(html), /29 Okt: gangguan 2 jam 41 menit/);
  assert.match(html, /aria-label="Gangguan 30 hari terakhir"/);
});

test('a closed row shows status, headline, action and the strip', async () => {
  const LoggerRow = await load('LoggerRow');
  const html = await render(LoggerRow, { row: ADMIN_ROW, incidents: INCIDENTS, now: NOW });
  const content = text(html);
  assert.match(content, /WMP 09/);
  assert.match(content, /Mati/);
  assert.match(content, /Tidak melapor sejak 1 Nov 10:12\. Internet sudah bermasalah/);
  assert.match(content, /Langkah: Cek di lokasi/);
  assert.match(html, /aria-expanded="false"/);
  assert.doesNotMatch(content, /Riwayat gangguan/);
});

test('an expanded admin row shows other findings, history, device and tech', async () => {
  const LoggerRow = await load('LoggerRow');
  const html = await render(LoggerRow, { row: ADMIN_ROW, incidents: INCIDENTS, expanded: true, now: NOW });
  const content = text(html);
  assert.match(html, /aria-expanded="true"/);
  assert.match(content, /Temuan lain/);
  assert.match(content, /Kiriman ke KLHK gagal sejak 1 Nov 09:00\./);
  assert.match(content, /Riwayat gangguan \(30 hari\)/);
  assert.match(content, /Internet lokasi putus 2 jam 41 menit; data menyusul 98%\. 2 bacaan hilang/);
  assert.match(content, /29 Okt 2026 • 14:02 – 29 Okt 2026 • 16:43 WIB · 2 jam 41 menit/);
  assert.match(content, /Kondisi perangkat/);
  assert.match(content, /Internet putus/);
  assert.match(content, /Antrean belum terkirim 27/);
  assert.match(content, /Kirim ke KLHK gagal/);
  assert.match(content, /pH OK · TSS gagal/);
  assert.match(content, /Teknis/);
  assert.match(content, /WMP09-LOG/);
  assert.match(content, /post-data · bad_signature · 3×/);
});

test('a viewer row never shows actions, device or tech, even expanded', async () => {
  const LoggerRow = await load('LoggerRow');
  const content = text(await render(LoggerRow, { row: VIEWER_ROW, incidents: INCIDENTS, expanded: true, now: NOW }));
  assert.match(content, /Tidak melapor sejak/);
  assert.match(content, /Riwayat gangguan/);
  assert.doesNotMatch(content, /Langkah/);
  assert.doesNotMatch(content, /Kondisi perangkat/);
  assert.doesNotMatch(content, /Teknis/);
});

test('unknown loggers list the uid, path, reason and count', async () => {
  const UnknownLoggers = await load('UnknownLoggers');
  const content = text(await render(UnknownLoggers, { rejections: [
    { uid: 'admin-LOG', site_uid: null, source: 'get-key', reason: 'unknown_uid', count: 12,
      first_at: '2026-11-03T01:00:00+00:00', last_at: '2026-11-04T02:00:00+00:00', last_detail: null },
  ] }));
  assert.match(content, /Logger tak dikenal/);
  assert.match(content, /admin-LOG · get-key · uid belum terdaftar · 12×/);
  const empty = text(await render(UnknownLoggers, { rejections: [] }));
  assert.match(empty, /Tidak ada kiriman dari logger tak dikenal dalam 7 hari terakhir\./);
});

test('a row survives odd data: spaced uid, open incident without a duration, missing findings', async () => {
  const LoggerRow = await load('LoggerRow');
  const row = { ...VIEWER_ROW, site_uid: 'PKN 2/LOG', findings: undefined };
  const incidents = [{ ...INCIDENTS[0], id: 8, ended_at: null, duration_min: null, cause_detail: null }];
  const html = await render(LoggerRow, { row, incidents, expanded: true, now: NOW });
  assert.match(html, /aria-controls="logger-detail-PKN_2_LOG"/);
  assert.match(html, /id="logger-detail-PKN_2_LOG"/);
  const content = text(html);
  assert.match(content, /sekarang · — /);
  assert.match(content, /Masih berlangsung\./);
  assert.doesNotMatch(content, /undefined|kurang dari 1 menit/);
  assert.doesNotMatch(content, /Antrean|bad_signature|heartbeat terakhir|Langkah|Teknis/);
});

test('the strip names its site for screen readers and does not repeat each day', async () => {
  const DayStrip = await load('DayStrip');
  const html = await render(DayStrip, { cells: dayStrip(INCIDENTS, { now: NOW }), label: 'Gangguan 30 hari terakhir — WMP 09' });
  assert.match(html, /aria-label="Gangguan 30 hari terakhir — WMP 09"/);
  assert.equal((html.match(/29 Okt: gangguan 2 jam 41 menit/g) ?? []).length, 2); // title (aria-hidden) + sr-only
  assert.match(html, /aria-hidden="true"/);
});

test('down history reads "tidak terjangkau", one stray reading is not "lost", and device shows op status and sends', async () => {
  assert.equal(recoveryText({ kind: 'down', ended_at: 'x', data_expected: 81, data_recovered: 80 }), '');
  const LoggerRow = await load('LoggerRow');
  const content = text(await render(LoggerRow, { row: ADMIN_ROW, incidents: INCIDENTS, expanded: true, now: NOW }));
  assert.match(content, /Logger tidak terjangkau/);
  assert.doesNotMatch(content, /Logger mati/);
  assert.match(content, /Status operasional Normal/);
  assert.match(content, /Terkirim hari ini 600/);
});

test('every time names the site zone; the event list uses it too; lost readings keep their space', async () => {
  assert.equal(zoneAbbr('Asia/Jakarta'), 'WIB');
  assert.equal(zoneAbbr('Asia/Pontianak'), 'WIB');
  assert.equal(zoneAbbr('Asia/Makassar'), 'WITA');
  assert.equal(zoneAbbr('Asia/Jayapura'), 'WIT');
  assert.equal(zoneAbbr('Asia/Kolkata'), 'UTC+5:30');
  assert.equal(zoneAbbr('Not/AZone'), '');
  const LoggerRow = await load('LoggerRow');
  const row = { ...ADMIN_ROW, timezone: 'Asia/Makassar' };
  const events = [{ id: 1, type: 'send_fail', ts: '2026-11-15T22:59:18', site_name: 'WMP04', detail: 'gagal kirim: KLHK' }];
  const html = await render(LoggerRow, { row, incidents: INCIDENTS, events, expanded: true, now: NOW });
  const content = text(html);
  assert.match(content, /sejak 01 Nov 2026 • 11:12 WITA/);
  assert.match(content, /29 Okt 2026 • 15:02 – 29 Okt 2026 • 17:43 WITA · 2 jam 41 menit/);
  assert.match(content, /Heartbeat terakhir 01 Nov 2026 • 11:12 WITA/);
  assert.match(content, /terakhir 01 Nov 2026 • 11:12 WITA · n=30/);
  assert.match(content, /16 Nov 2026 06\.59\.18 WITA/);           // naive UTC, shown on the site clock
  assert.doesNotMatch(content, /WIB/);
  // The raw HTML, not the normalised text: a browser shows exactly this.
  assert.match(html, /data menyusul 98%\. 2 bacaan hilang/);
  const open = text(await render(LoggerRow, { row, incidents: [{ ...INCIDENTS[0], ended_at: null, duration_min: null }], expanded: true, now: NOW }));
  assert.match(open, /29 Okt 2026 • 15:02 WITA – sekarang · —/);
});
