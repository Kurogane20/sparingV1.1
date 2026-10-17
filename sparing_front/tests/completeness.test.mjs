import assert from 'node:assert/strict';
import test from 'node:test';
import { completenessSegments } from '../resources/js/Utils/completeness.js';
import { localMidnightISO } from '../resources/js/Utils/dashboardTimeseries.js';

test('day bar splits the whole day into received, missing and not yet due', () => {
  const bar = completenessSegments({ actual: 496, expected: 513, expected_total: 720 });

  assert.deepEqual([bar.received, bar.missing, bar.notYet], [496, 17, 207]);
  assert.deepEqual([bar.receivedPct, bar.missingPct, bar.notYetPct], [68.9, 2.4, 28.7]);
  assert.equal(Math.round((bar.receivedPct + bar.missingPct + bar.notYetPct) * 10), 1000, 'widths fill the bar exactly');
});

test('more readings than due never shows a negative gap', () => {
  const bar = completenessSegments({ actual: 520, expected: 513, expected_total: 720 });

  assert.equal(bar.missing, 0);
  assert.equal(bar.received, 520);
  assert.equal(bar.notYet, 200);
});

test('older API responses without a day target still render', () => {
  const bar = completenessSegments({ actual: 307, expected: 327 });

  assert.deepEqual([bar.received, bar.missing, bar.notYet], [307, 20, 0]);
  assert.equal(completenessSegments(null), null);
});

test('"hari ini" starts at the site\'s local midnight', () => {
  const at = new Date('2026-10-17T10:04:00Z'); // 17:04 WIB, 18:04 WITA
  assert.equal(localMidnightISO('Asia/Jakarta', at), '2026-10-16T17:00:00.000Z');
  assert.equal(localMidnightISO('Asia/Makassar', at), '2026-10-16T16:00:00.000Z');
  // 00:30 WIB already belongs to the new day.
  assert.equal(localMidnightISO('Asia/Jakarta', new Date('2026-10-16T17:30:00Z')), '2026-10-16T17:00:00.000Z');
});
