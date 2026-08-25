import assert from 'node:assert/strict';
import test from 'node:test';
import {
  buildApexSeries,
  buildEventAnnotations,
  buildThresholdAnnotations,
  formatDashboardTimestamp,
  getDebitScale,
  getFieldSummary,
  getTssScale,
  normalizeTimeseriesPayload,
} from '../resources/js/Utils/dashboardTimeseries.js';

test('preserves zero and converts invalid chart values to null', () => {
  const snapshot = normalizeTimeseriesPayload({
    meta: { timezone: 'Asia/Jakarta', is_partial: false },
    series: {
      ph: { label: 'pH', unit: '', points: [{ ts: '2026-08-25T00:00:00Z', value: 0 }] },
      tss: { label: 'TSS', unit: 'mg/L', points: [{ ts: '2026-08-25T00:00:00Z', value: null }] },
      debit: { label: 'Debit', unit: 'L/min', points: [{ ts: '2026-08-25T00:00:00Z', value: Number.NaN }] },
    },
    statistics: {},
    thresholds: {},
    events: [],
    event_total: 0,
  });
  assert.equal(snapshot.series.ph.points[0].value, 0);
  assert.equal(snapshot.series.tss.points[0].value, null);
  assert.equal(snapshot.series.debit.points[0].value, null);
});

function makeSnapshotWithPhPoints(points) {
  return {
    meta: { timezone: 'Asia/Jakarta', is_partial: false },
    series: {
      ph: { label: 'pH', unit: '', points },
      tss: { label: 'TSS', unit: 'mg/L', points: [] },
      debit: { label: 'Debit', unit: 'L/min', points: [] },
    },
    statistics: {},
    thresholds: {},
    events: [],
    event_total: 0,
  };
}

test('sorts, deduplicates, and drops invalid timestamps defensively', () => {
  const payload = makeSnapshotWithPhPoints([
    { ts: 'invalid', value: 9 },
    { ts: '2026-08-25T00:02:00Z', value: 7.2 },
    { ts: '2026-08-25T00:00:00Z', value: 7.0 },
    { ts: '2026-08-25T00:02:00Z', value: 7.3 },
  ]);
  const points = normalizeTimeseriesPayload(payload).series.ph.points;
  assert.deepEqual(points.map((point) => point.value), [7.0, 7.3]);
});

test('formats Indonesian site time with colon separators', () => {
  assert.equal(
    formatDashboardTimestamp('2026-08-24T18:38:00Z', 'Asia/Jakarta'),
    '25 Agu 2026 • 01:38',
  );
});

function makeChartSnapshot() {
  return normalizeTimeseriesPayload({
    meta: {
      timezone: 'Asia/Jakarta',
      is_partial: true,
      partial_reasons: [{ code: 'sensor_late', message: 'Sensor terlambat' }],
    },
    series: {
      ph: {
        label: 'Potential of Hydrogen',
        unit: '',
        status_label: 'Normal dari backend',
        status_reason: 'Dalam rentang',
        status_severity: 'success',
        flagged_count: 2,
        points: [
          { ts: '2026-08-25T00:00:00Z', value: 7.1 },
          { ts: '2026-08-25T00:01:00Z', value: null },
        ],
      },
      tss: {
        label: 'Padatan',
        unit: 'mg/L',
        points: [{ ts: '2026-08-25T00:00:00Z', value: 22 }],
      },
      debit: {
        label: 'Aliran',
        unit: 'L/min',
        flow_state: 'steady',
        points: [{ ts: '2026-08-25T00:00:00Z', value: 0 }],
      },
    },
    statistics: {
      ph: { current: 7.2, avg: 7.1, status: 'normal' },
      tss: { current: 0, avg: 22, status_label: 'Sesuai backend', status_reason: 'Baku mutu aman', status_severity: 'success' },
      debit: { current: 0, avg: 0, status: 'no_data' },
    },
    thresholds: {
      ph: {
        warning_min: 6.5,
        warning_max: 8.5,
        danger_min: 6,
        danger_max: 9,
        source: 'site_alert_rule',
        regulation: 'Permen LHK 5/2014',
        label: 'pH air limbah',
        unit: '',
      },
      tss: {
        warning_min: null,
        warning_max: 50,
        danger_min: null,
        danger_max: 80,
        source: 'site_alert_rule',
        regulation: 'Permen LHK 5/2014',
        label: 'TSS',
        unit: 'mg/L',
      },
    },
    events: [
      { ts: '2026-08-25T00:00:00Z', type: 'threshold_warning', context: { current: 51 } },
      { ts: '2026-08-25T00:01:00Z', type: 'threshold_danger', context: { current: 61 } },
      { ts: '2026-08-25T00:02:00Z', type: 'rapid_change', context: { current: 7.9 } },
      { ts: '2026-08-25T00:03:00Z', type: 'sensor_anomaly', context: { current: 0 } },
      { ts: '2026-08-25T00:04:00Z', type: 'sensor_error', context: { current: 0 } },
      { ts: '2026-08-25T00:05:00Z', type: 'flow_drop', context: { debit: { value: 1, flow_state: 'low_flow' } } },
      { ts: '2026-08-25T00:06:00Z', type: 'no_flow', context: { debit: { value: 0, flow_state: 'no_flow' } } },
      { ts: '2026-08-25T00:07:00Z', type: 'flow_restored', context: { debit: { value: 3, flow_state: 'normal' } } },
      {
        ts: '2026-08-25T00:08:00Z',
        type: 'low_flow_tss_check',
        context: {
          current: 120,
          debit: { value: 0.5, flow_state: 'low_flow' },
          tss: { baseline: 10, current: 120, delta: 110, percent: 1100 },
          tss_event_id: 'event-tss-123',
        },
      },
      { ts: '2026-08-25T00:09:00Z', type: 'data_gap', context: { interval_seconds: 300 } },
      { ts: '2026-08-25T00:10:00Z', type: 'op_status', context: { current: -1 } },
      { ts: '2026-08-25T00:11:00Z', type: 'logger_offline', context: { interval_seconds: 60 } },
    ],
    event_total: 12,
  });
}

test('maps only requested field points into fixed Apex series with null gaps and zero values', () => {
  const series = buildApexSeries(makeChartSnapshot(), ['ph', 'tss', 'debit']);
  assert.deepEqual(series, [
    {
      name: 'pH',
      data: [
        { x: Date.parse('2026-08-25T00:00:00Z'), y: 7.1 },
        { x: Date.parse('2026-08-25T00:01:00Z'), y: null },
      ],
    },
    { name: 'TSS', data: [{ x: Date.parse('2026-08-25T00:00:00Z'), y: 22 }] },
    { name: 'Debit', data: [{ x: Date.parse('2026-08-25T00:00:00Z'), y: 0 }] },
  ]);
});

test('builds threshold annotations from flat backend values and metadata only', () => {
  const snapshot = makeChartSnapshot();
  const ph = buildThresholdAnnotations(snapshot, 'ph');
  const tss = buildThresholdAnnotations(snapshot, 'tss');
  assert.deepEqual(ph.map(({ y, label }) => [y, label.text]), [
    [6.5, 'Peringatan minimum · site_alert_rule · Permen LHK 5/2014'],
    [8.5, 'Peringatan maksimum · site_alert_rule · Permen LHK 5/2014'],
    [6, 'Bahaya minimum · site_alert_rule · Permen LHK 5/2014'],
    [9, 'Bahaya maksimum · site_alert_rule · Permen LHK 5/2014'],
  ]);
  assert.deepEqual(tss.map(({ y, label }) => [y, label.text]), [
    [50, 'Peringatan maksimum · site_alert_rule · Permen LHK 5/2014'],
    [80, 'Bahaya maksimum · site_alert_rule · Permen LHK 5/2014'],
  ]);
});

test('uses capped real machine events as deterministic event annotations with context values', () => {
  const annotations = buildEventAnnotations(makeChartSnapshot());
  assert.deepEqual(annotations.map(({ x, y, marker }) => [x, y, marker.shape]), [
    [Date.parse('2026-08-25T00:00:00Z'), 51, 'triangle'],
    [Date.parse('2026-08-25T00:01:00Z'), 61, 'triangle'],
    [Date.parse('2026-08-25T00:02:00Z'), 7.9, 'diamond'],
    [Date.parse('2026-08-25T00:03:00Z'), 0, 'circle'],
    [Date.parse('2026-08-25T00:04:00Z'), 0, 'circle'],
    [Date.parse('2026-08-25T00:05:00Z'), 1, 'square'],
    [Date.parse('2026-08-25T00:06:00Z'), 0, 'square'],
    [Date.parse('2026-08-25T00:07:00Z'), 3, 'square'],
    [Date.parse('2026-08-25T00:08:00Z'), 0.5, 'square'],
    [Date.parse('2026-08-25T00:09:00Z'), undefined, 'cross'],
    [Date.parse('2026-08-25T00:10:00Z'), -1, 'circle'],
    [Date.parse('2026-08-25T00:11:00Z'), undefined, 'cross'],
  ]);
});

test('uses backend summary and metadata without deriving it from display points', () => {
  const snapshot = makeChartSnapshot();
  assert.deepEqual(getFieldSummary(snapshot, 'tss'), {
    current: 0,
    avg: 22,
    status_label: 'Sesuai backend',
    status_reason: 'Baku mutu aman',
    status_severity: 'success',
  });
  assert.equal(snapshot.meta.partial_reasons[0].code, 'sensor_late');
  assert.equal(snapshot.series.ph.flagged_count, 2);
  assert.equal(snapshot.series.debit.flow_state, 'steady');
  assert.equal(snapshot.events[0].context.current, 51);
  assert.equal(snapshot.event_total, 12);
});

test('starts TSS scale at zero and leaves headroom for the configured threshold', () => {
  const scale = getTssScale(makeChartSnapshot());
  assert.equal(scale.min, 0);
  assert.ok(scale.max > 80);
});

test('uses Indonesian status fallbacks only when backend status metadata is absent', () => {
  const snapshot = normalizeTimeseriesPayload({
    meta: { timezone: 'Asia/Jakarta', is_partial: false },
    series: { ph: { points: [] }, tss: { points: [] }, debit: { points: [] } },
    statistics: {
      ph: { status: 'sensor_error' },
      tss: { status: 'no_flow' },
      debit: { status: 'normal', status_label: 'Label backend', status_reason: 'Alasan backend', status_severity: 'info' },
    },
    thresholds: {},
    events: [],
    event_total: 0,
  });
  assert.deepEqual(getFieldSummary(snapshot, 'ph'), {
    status: 'sensor_error',
    status_label: 'Kesalahan Sensor',
    status_reason: 'explicit_sensor_error',
    status_severity: 'critical',
  });
  assert.deepEqual(getFieldSummary(snapshot, 'tss'), {
    status: 'no_flow',
    status_label: 'Aliran Terhenti',
    status_reason: 'no_flow_threshold_violated',
    status_severity: 'warning',
  });
  assert.deepEqual(getFieldSummary(snapshot, 'debit'), {
    status: 'normal',
    status_label: 'Label backend',
    status_reason: 'Alasan backend',
    status_severity: 'info',
  });
});

function makeDebitSnapshot(values, current) {
  return normalizeTimeseriesPayload({
    meta: { timezone: 'Asia/Jakarta', is_partial: false },
    series: {
      ph: { points: [] },
      tss: { points: [] },
      debit: {
        points: values.map((value, index) => ({
          ts: `2026-08-25T00:${String(index).padStart(2, '0')}:00Z`,
          value,
        })),
      },
    },
    statistics: { debit: { current } },
    thresholds: {},
    events: [],
    event_total: 0,
  });
}

test('uses a zero-based robust Debit scale without hiding the backend current value', () => {
  const snapshot = makeDebitSnapshot([...Array.from({ length: 20 }, (_, index) => index), 1000], 40);
  const scale = getDebitScale(snapshot);
  assert.deepEqual(scale, { min: 0, max: 44, outlierCount: 1 });
});

test('uses the actual Debit maximum in full-scale mode', () => {
  const snapshot = makeDebitSnapshot([...Array.from({ length: 20 }, (_, index) => index), 1000], 40);
  assert.deepEqual(getDebitScale(snapshot, 'full'), { min: 0, max: 1100, outlierCount: 0 });
});

test('returns a finite positive Debit maximum when all readings are zero', () => {
  assert.deepEqual(getDebitScale(makeDebitSnapshot([0, 0, 0], 0)), {
    min: 0,
    max: 1.1,
    outlierCount: 0,
  });
});
