import assert from 'node:assert/strict';
import test from 'node:test';
import {
  STALE_AFTER_MS, bandState, joinLabels, limitPosition, localDateISO, monthCompliance,
} from '../resources/js/Utils/dashboardStatus.js';

const NOW = Date.parse('2026-10-27T07:05:00Z'); // 14:05 WIB
const minutesAgo = (minutes) => new Date(NOW - minutes * 60 * 1000).toISOString();
const RULES = {
  ph: { field: 'ph', danger_min: 6, danger_max: 9, is_active: true },
  tss: { field: 'tss', danger_min: null, danger_max: 200, is_active: true },
  cod: { field: 'cod', danger_min: null, danger_max: 300, is_active: true },
};
const reading = (values = {}) => ({
  ts: minutesAgo(20), ph: 7.4, tss: 46, cod: 118, quality_flag: null, op_status: null, ...values,
});
const band = (overrides = {}) => bandState({
  rules: RULES, latest: reading(), todayStatus: 'ok', activeAlerts: [], now: NOW, ...overrides,
});

test('a site without active limits cannot be judged', () => {
  assert.equal(band({ rules: {} }).state, 'no_rules');
  assert.equal(band({ rules: [{ field: 'tss', danger_max: 200, is_active: false }] }).state, 'no_rules');
});

test('no reading, or one older than two hours, is stale data — not a compliance verdict', () => {
  assert.deepEqual(band({ latest: null }), { state: 'stale', lastTs: null, breachedToday: false });
  const old = band({
    latest: reading({ ts: new Date(NOW - STALE_AFTER_MS - 1000).toISOString() }),
    todayStatus: 'violation',
  });
  assert.equal(old.state, 'stale');
  assert.equal(old.breachedToday, true);
  assert.equal(band({ latest: reading({ ts: new Date(NOW - STALE_AFTER_MS).toISOString() }) }).state, 'compliant');
});

test('a reading beyond its danger limit is a breach now, dated by its compliance alert', () => {
  const result = band({
    latest: reading({ tss: 212 }),
    activeAlerts: [
      { id: 3, field: 'tss', category: 'data_quality', triggered_at: minutesAgo(90) },
      { id: 7, field: 'tss', category: 'compliance', triggered_at: minutesAgo(25) },
    ],
  });
  assert.equal(result.state, 'breach_now');
  assert.equal(result.title, 'TSS melewati baku mutu');
  assert.deepEqual(result.breaches, [{ field: 'tss', value: 212, min: null, max: 200 }]);
  assert.equal(result.alertId, 7);
  assert.equal(result.since, minutesAgo(25));
});

test('pH breaches on either side and several parameters are named together', () => {
  assert.equal(band({ latest: reading({ ph: 5.8 }) }).title, 'pH melewati baku mutu');
  assert.equal(band({ latest: reading({ ph: 9.2 }) }).state, 'breach_now');
  const many = band({ latest: reading({ tss: 250, cod: 320 }) });
  assert.equal(many.title, 'TSS dan COD melewati baku mutu');
  assert.equal(many.alertId, null);
  assert.equal(joinLabels(['ph', 'tss', 'nh3n']), 'pH, TSS dan NH₃-N');
});

test('flagged or operational-status rows are not judged against the limit', () => {
  assert.equal(band({ latest: reading({ tss: 999, quality_flag: 'anomaly' }) }).state, 'compliant');
  assert.equal(band({ latest: reading({ tss: 999, op_status: -2 }) }).state, 'compliant');
});

test('a violation earlier today, now back within limits, is "sempat melewati"', () => {
  assert.deepEqual(band({ todayStatus: 'violation' }), { state: 'breached_today' });
});

test('compliant days note readings near the limit', () => {
  assert.deepEqual(band(), { state: 'compliant', nearLimit: false });
  assert.deepEqual(band({ todayStatus: 'warning' }), { state: 'compliant', nearLimit: true });
});

test('month compliance counts ok and warning days, skips empty and future days', () => {
  const days = [
    { date: '2026-10-01', status: 'ok' },
    { date: '2026-10-02', status: 'warning' },
    { date: '2026-10-03', status: 'violation' },
    { date: '2026-10-04', status: 'none' },
    { date: '2026-10-28', status: 'ok' },
  ];
  const month = monthCompliance(days, '2026-10-27');
  assert.deepEqual(month.cells.map((cell) => cell.status), ['ok', 'ok', 'violation', 'empty', 'future']);
  assert.equal(month.compliant, 2);
  assert.equal(month.judged, 3);
  assert.equal(month.pct, 66.7);
  assert.equal(monthCompliance([{ date: '2026-10-01', status: 'none' }], '2026-10-27').pct, null);
});

test('limit position: share of a maximum, or a segment from the lower limit on a range track', () => {
  assert.deepEqual(limitPosition(46, RULES.tss), { kind: 'max', start: 0, end: 23, breach: false });
  assert.deepEqual(limitPosition(212, RULES.tss), { kind: 'max', start: 0, end: 100, breach: true });
  const ph = limitPosition(7.5, RULES.ph); // track runs 4.5 … 10.5
  assert.equal(ph.kind, 'range');
  assert.equal(ph.minAt, 25);
  assert.equal(ph.maxAt, 75);
  assert.equal(ph.start, 25);
  assert.equal(ph.end, 50);
  assert.equal(ph.breach, false);
  const low = limitPosition(5.25, RULES.ph);
  assert.equal(low.start, 12.5);
  assert.equal(low.end, 25);
  assert.equal(low.breach, true);
  assert.deepEqual(limitPosition(12.6, null), { kind: 'none' });
  assert.deepEqual(limitPosition(null, RULES.tss), { kind: 'none' });
});

test('the local date follows the site timezone, not UTC', () => {
  const lateEvening = new Date('2026-10-26T18:30:00Z'); // 01:30 WIB on the 27th
  assert.equal(localDateISO('Asia/Jakarta', lateEvening), '2026-10-27');
  assert.equal(localDateISO('UTC', lateEvening), '2026-10-26');
});
