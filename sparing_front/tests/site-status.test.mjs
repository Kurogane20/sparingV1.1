import assert from 'node:assert/strict';
import test from 'node:test';
import { SITE_STALE_MS, buildSiteChips, rowStatusFromLatest, siteChipStatus } from '../resources/js/Utils/siteStatus.js';

const NOW = Date.parse('2026-10-13T01:00:00Z');
const fresh = (fields) => ({ ts: '2026-10-13T00:30:00Z', ...fields });

test('siteChipStatus: a dead logger wins over fresh data', () => {
  assert.equal(siteChipStatus({ latest: fresh({ ph: 7 }), loggerState: 'down', now: NOW }), 'offline');
});

test('siteChipStatus: missing or stale readings are nodata', () => {
  assert.equal(siteChipStatus({ latest: null, now: NOW }), 'nodata');
  assert.equal(siteChipStatus({ latest: { ph: 7 }, now: NOW }), 'nodata');
  const old = { ts: new Date(NOW - SITE_STALE_MS - 1000).toISOString(), ph: 7 };
  assert.equal(siteChipStatus({ latest: old, loggerState: 'alive', now: NOW }), 'nodata');
});

test('siteChipStatus: naive API timestamps are read as UTC', () => {
  assert.equal(siteChipStatus({ latest: { ts: '2026-10-13T00:30:00', ph: 7 }, now: NOW }), 'normal');
});

test('siteChipStatus: fresh readings follow baku mutu thresholds', () => {
  assert.equal(siteChipStatus({ latest: fresh({ ph: 7, tss: 250 }), now: NOW }), 'danger');
  assert.equal(siteChipStatus({ latest: fresh({ tss: 160 }), now: NOW }), 'warning');
  assert.equal(siteChipStatus({ latest: fresh({ ph: 7, tss: 20 }), now: NOW }), 'normal');
  assert.equal(siteChipStatus({ latest: fresh({ debit: 1 }), now: NOW }), 'nodata');
});

test('rowStatusFromLatest ignores absent fields', () => {
  assert.equal(rowStatusFromLatest({ ph: 7, cod: null }), 'normal');
  assert.equal(rowStatusFromLatest(null), 'nodata');
});

test('buildSiteChips puts problem sites first, then sorts by name', () => {
  const site = (uid, name) => ({ uid, name });
  const chips = buildSiteChips([
    { site: site('a', 'Zeta'), latest: fresh({ ph: 7 }) },
    { site: site('b', 'Alpha'), latest: fresh({ ph: 7 }) },
    { site: site('c', 'Mati'), latest: fresh({ ph: 7 }) },
    { site: site('d', 'Bahaya'), latest: fresh({ tss: 300 }) },
    { site: site('e', 'Lama'), latest: null },
    { site: site('f', 'Waspada'), latest: fresh({ tss: 160 }) },
  ], { c: 'down' }, NOW);
  assert.deepEqual(chips.map((chip) => [chip.uid, chip.name, chip.status]), [
    ['d', 'Bahaya', 'danger'], ['f', 'Waspada', 'warning'], ['c', 'Mati', 'offline'],
    ['e', 'Lama', 'nodata'], ['b', 'Alpha', 'normal'], ['a', 'Zeta', 'normal'],
  ]);
});
