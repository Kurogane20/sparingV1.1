import assert from 'node:assert/strict';
import test from 'node:test';
import { comparisonChart, loggerLabel } from '../resources/js/Utils/overview.js';

const SITES = [
  { name: 'PTPN IV regional V Parindu', compliance_pct: null, completeness_pct: 0 },
  { name: 'FSK LOG', compliance_pct: 100, completeness_pct: 94.2 },
];

test('logger state reads in Indonesian', () => {
  assert.equal(loggerLabel('alive'), 'Logger hidup');
  assert.equal(loggerLabel('down'), 'Logger mati');
  assert.equal(loggerLabel(null), 'Logger belum terpantau');
});

test('site comparison uses horizontal bars so long site names stay readable', () => {
  const { options, series, height } = comparisonChart(SITES);

  assert.equal(options.plotOptions.bar.horizontal, true);
  assert.deepEqual(options.xaxis.categories, SITES.map((site) => site.name));
  assert.equal(options.xaxis.max, 100);
  assert.deepEqual(series.map((entry) => entry.name), ['Kepatuhan 24 jam', 'Kelengkapan hari ini']);
  // A site without compliance data shows no bar rather than a misleading 0%.
  assert.deepEqual(series[0].data, [null, 100]);
  assert.ok(height >= 160 && height > 2 * 40, 'grows with the number of sites');
});
