import assert from 'node:assert/strict';
import test from 'node:test';
import axios from 'axios';
import { effectScope, ref } from 'vue';
import {
  buildRequestParams,
  useDashboardTimeseries,
} from '../resources/js/Composables/useDashboardTimeseries.js';
import {
  buildApexSeries,
  buildDangerBands,
  buildEventAnnotations,
  buildThresholdAnnotations,
  eventLegendItems,
  formatDashboardTimestamp,
  formatDecimal,
  formatMeasurement,
  getDebitScale,
  getFieldSummary,
  getPhScale,
  getTssScale,
  niceScale,
  normalizeTimeseriesPayload,
  timeAxisRange,
} from '../resources/js/Utils/dashboardTimeseries.js';

function deferred() {
  let resolve;
  let reject;
  const promise = new Promise((resolvePromise, rejectPromise) => {
    resolve = resolvePromise;
    reject = rejectPromise;
  });
  return { promise, resolve, reject };
}

function makeTimeseriesPayload(value, { partial = false } = {}) {
  return {
    meta: { timezone: 'Asia/Jakarta', is_partial: partial },
    series: {
      ph: { points: [{ ts: '2026-08-25T00:00:00Z', value }] },
      tss: { points: [] },
      debit: { points: [] },
    },
    statistics: {},
    thresholds: {},
    events: [],
    event_total: 0,
  };
}

test('builds mutually exclusive preset and custom request parameter shapes', () => {
  assert.deepEqual(buildRequestParams('today'), {
    preset: 'today',
    fields: 'ph,tss,debit',
  });
  assert.deepEqual(buildRequestParams('custom', {
    dateFrom: '2026-08-25T00:00:00.000Z',
    dateTo: '2026-08-25T01:00:00.000Z',
  }), {
    date_from: '2026-08-25T00:00:00.000Z',
    date_to: '2026-08-25T01:00:00.000Z',
    fields: 'ph,tss,debit',
  });
});

test('keeps the second selection response when an earlier request resolves late', async () => {
  const requests = [];
  const controller = useDashboardTimeseries({
    siteUid: 'site-1',
    fetchTimeseries: (siteUid, params, signal) => {
      const next = deferred();
      requests.push({ siteUid, params, signal, ...next });
      return next.promise;
    },
  });

  const first = controller.load();
  const second = controller.setPreset('24h');
  assert.equal(controller.state.value, 'loading');
  assert.equal(requests[0].signal.aborted, true);
  assert.deepEqual(requests[1].params, { preset: '24h', fields: 'ph,tss,debit' });

  requests[1].resolve(makeTimeseriesPayload(24));
  await second;
  requests[0].resolve(makeTimeseriesPayload(1));
  await first;

  assert.equal(controller.snapshot.value.series.ph.points[0].value, 24);
  assert.equal(controller.state.value, 'ready');
});

async function assertIncompleteCustomSelectionCancels(invokeSelection) {
  const request = deferred();
  const controller = useDashboardTimeseries({
    siteUid: 'site-1',
    fetchTimeseries: (siteUid, params, signal) => {
      request.signal = signal;
      return request.promise;
    },
  });

  const loading = controller.load();
  await invokeSelection(controller);

  assert.equal(request.signal.aborted, true);
  assert.equal(controller.snapshot.value, null);
  assert.equal(controller.state.value, 'idle');
  request.resolve(makeTimeseriesPayload(99));
  await loading;
  assert.equal(controller.snapshot.value, null);
  assert.equal(controller.state.value, 'idle');
}

test('cancels an active request when selecting custom before both dates are available', async () => {
  await assertIncompleteCustomSelectionCancels((controller) => controller.setPreset('custom'));
});

test('cancels an active request when editing an incomplete custom range', async () => {
  await assertIncompleteCustomSelectionCancels((controller) => controller.setCustomRange({
    dateFrom: '2026-08-25T00:00:00.000Z',
  }));
});

test('forwards the dashboard timeseries request through the axios adapter', async () => {
  const originalAdapter = axios.defaults.adapter;
  const storageDescriptor = Object.getOwnPropertyDescriptor(globalThis, 'localStorage');
  let requestConfig;
  axios.defaults.adapter = async (config) => {
    requestConfig = config;
    return {
      data: { ok: true },
      status: 200,
      statusText: 'OK',
      headers: {},
      config,
    };
  };
  Object.defineProperty(globalThis, 'localStorage', {
    configurable: true,
    value: { getItem: () => null },
  });

  try {
    const moduleUrl = new URL('../resources/js/Composables/useApi.js', import.meta.url);
    const { useApi } = await import(`${moduleUrl.href}?adapter-spy=${Date.now()}`);
    const signal = new AbortController().signal;
    const result = await useApi().getDashboardTimeseries('site-1', { preset: '6h' }, signal);

    assert.deepEqual(result, { ok: true });
    assert.equal(requestConfig.method, 'get');
    assert.equal(requestConfig.url, '/analytics/timeseries');
    assert.deepEqual(requestConfig.params, { site_uid: 'site-1', preset: '6h' });
    assert.equal(requestConfig.signal, signal);
  } finally {
    axios.defaults.adapter = originalAdapter;
    if (storageDescriptor) Object.defineProperty(globalThis, 'localStorage', storageDescriptor);
    else delete globalThis.localStorage;
  }
});

test('shows an actionable initial error without exposing an internal exception', async () => {
  const controller = useDashboardTimeseries({
    siteUid: 'site-1',
    fetchTimeseries: () => Promise.reject({ response: { data: { detail: 'Rentang waktu tidak valid' } } }),
  });

  await controller.load();

  assert.equal(controller.snapshot.value, null);
  assert.equal(controller.state.value, 'error');
  assert.equal(controller.errorMessage.value, 'Rentang waktu tidak valid');
});

test('preserves the last successful snapshot as stale when a refresh fails', async () => {
  let attempt = 0;
  const controller = useDashboardTimeseries({
    siteUid: 'site-1',
    fetchTimeseries: () => {
      attempt += 1;
      return attempt === 1
        ? Promise.resolve(makeTimeseriesPayload(7))
        : Promise.reject(new Error('connection reset by peer'));
    },
  });

  await controller.load();
  await controller.retry();

  assert.equal(controller.snapshot.value.series.ph.points[0].value, 7);
  assert.equal(controller.state.value, 'stale');
  assert.equal(controller.errorMessage.value, 'Unable to refresh monitoring data. Please try again.');
});

test('clears a successful snapshot when a changed preset request fails', async () => {
  let attempt = 0;
  const requests = [];
  const controller = useDashboardTimeseries({
    siteUid: 'site-1',
    fetchTimeseries: (siteUid, params) => {
      requests.push({ siteUid, params });
      attempt += 1;
      return attempt === 1
        ? Promise.resolve(makeTimeseriesPayload(7))
        : Promise.reject(new Error('upstream timeout'));
    },
  });

  await controller.load();
  await controller.setPreset('7d');

  assert.deepEqual(requests.map(({ params }) => params), [
    { preset: 'today', fields: 'ph,tss,debit' },
    { preset: '7d', fields: 'ph,tss,debit' },
  ]);
  assert.equal(controller.preset.value, '7d');
  assert.equal(controller.snapshot.value, null);
  assert.equal(controller.state.value, 'error');
  assert.equal(controller.errorMessage.value, 'Unable to load monitoring data. Please try again.');
});

test('clears a successful custom snapshot when custom boundaries change and fail', async () => {
  let attempt = 0;
  const requests = [];
  const controller = useDashboardTimeseries({
    siteUid: 'site-1',
    fetchTimeseries: (siteUid, params) => {
      requests.push({ siteUid, params });
      attempt += 1;
      return attempt === 1
        ? Promise.resolve(makeTimeseriesPayload(8))
        : Promise.reject(new Error('upstream timeout'));
    },
  });

  await controller.setCustomRange({
    dateFrom: '2026-08-25T00:00',
    dateTo: '2026-08-25T01:00',
  });
  await controller.setCustomRange({
    dateFrom: '2026-08-26T00:00',
    dateTo: '2026-08-26T01:00',
  });

  assert.deepEqual(requests.map(({ params }) => params), [
    { date_from: '2026-08-25T00:00', date_to: '2026-08-25T01:00', fields: 'ph,tss,debit' },
    { date_from: '2026-08-26T00:00', date_to: '2026-08-26T01:00', fields: 'ph,tss,debit' },
  ]);
  assert.equal(controller.snapshot.value, null);
  assert.equal(controller.state.value, 'error');
  assert.equal(controller.errorMessage.value, 'Unable to load monitoring data. Please try again.');
});

test('keeps abort failures silent', async () => {
  const controller = useDashboardTimeseries({
    siteUid: 'site-1',
    fetchTimeseries: () => Promise.reject(Object.assign(new Error('aborted'), { name: 'AbortError' })),
  });

  await controller.load();

  assert.equal(controller.state.value, 'idle');
  assert.equal(controller.errorMessage.value, '');
});

test('distinguishes empty data from a payload containing a finite zero', async () => {
  const payloads = [makeTimeseriesPayload(null), makeTimeseriesPayload(0)];
  const controller = useDashboardTimeseries({
    siteUid: 'site-1',
    fetchTimeseries: () => Promise.resolve(payloads.shift()),
  });

  await controller.load();
  assert.equal(controller.state.value, 'empty');
  await controller.retry();
  assert.equal(controller.state.value, 'ready');
  assert.equal(controller.snapshot.value.series.ph.points[0].value, 0);
});

test('uses the partial state and normalizes a successful payload once at the request boundary', async () => {
  const controller = useDashboardTimeseries({
    siteUid: 'site-1',
    fetchTimeseries: () => Promise.resolve({
      ...makeTimeseriesPayload(8, { partial: true }),
      series: {
        ph: {
          points: [
            { ts: '2026-08-25T00:02:00Z', value: 8 },
            { ts: '2026-08-25T00:00:00Z', value: 7 },
          ],
        },
        tss: { points: [] },
        debit: { points: [] },
      },
    }),
  });

  await controller.load();

  assert.equal(controller.state.value, 'partial');
  assert.deepEqual(
    controller.snapshot.value.series.ph.points.map((point) => point.value),
    [7, 8],
  );
});

test('uses the current value from a site ref for a subsequent load', async () => {
  const siteUid = ref('site-1');
  const receivedSites = [];
  const controller = useDashboardTimeseries({
    siteUid,
    fetchTimeseries: (currentSite) => {
      receivedSites.push(currentSite);
      return Promise.resolve(makeTimeseriesPayload(1));
    },
  });

  await controller.load();
  siteUid.value = 'site-2';
  await controller.load();

  assert.deepEqual(receivedSites, ['site-1', 'site-2']);
});

test('does not overlap polling requests and stop aborts the active request and clears its interval', async () => {
  const originalSetInterval = globalThis.setInterval;
  const originalClearInterval = globalThis.clearInterval;
  const intervals = new Map();
  let nextIntervalId = 1;
  globalThis.setInterval = (callback) => {
    const id = nextIntervalId++;
    intervals.set(id, callback);
    return id;
  };
  globalThis.clearInterval = (id) => intervals.delete(id);

  try {
    const requests = [];
    const controller = useDashboardTimeseries({
      siteUid: 'site-1',
      pollMs: 50,
      fetchTimeseries: (siteUid, params, signal) => {
        const next = deferred();
        requests.push({ siteUid, params, signal, ...next });
        return next.promise;
      },
    });
    const scope = effectScope();
    scope.run(() => controller.startPolling());
    controller.startPolling();
    assert.equal(intervals.size, 1);

    const initial = controller.load();
    await intervals.values().next().value();
    assert.equal(requests.length, 1);

    requests[0].resolve(makeTimeseriesPayload(3));
    await initial;
    await intervals.values().next().value();
    assert.equal(requests.length, 2);

    controller.stopPolling();
    assert.equal(intervals.size, 0);
    assert.equal(requests[1].signal.aborted, true);
    requests[1].resolve(makeTimeseriesPayload(99));
    await Promise.resolve();
    assert.equal(controller.snapshot.value.series.ph.points[0].value, 3);
    scope.stop();
  } finally {
    globalThis.setInterval = originalSetInterval;
    globalThis.clearInterval = originalClearInterval;
  }
});

test('disposal clears polling and aborts an in-flight request without accepting its response', async () => {
  const originalSetInterval = globalThis.setInterval;
  const originalClearInterval = globalThis.clearInterval;
  const intervals = new Map();
  globalThis.setInterval = (callback) => {
    const id = Symbol('interval');
    intervals.set(id, callback);
    return id;
  };
  globalThis.clearInterval = (id) => intervals.delete(id);

  try {
    const request = deferred();
    const scope = effectScope();
    const controller = scope.run(() => useDashboardTimeseries({
      siteUid: 'site-1',
      fetchTimeseries: (siteUid, params, signal) => {
        request.signal = signal;
        return request.promise;
      },
    }));
    controller.startPolling();
    const loading = controller.load();
    scope.stop();

    assert.equal(intervals.size, 0);
    assert.equal(request.signal.aborted, true);
    request.resolve(makeTimeseriesPayload(99));
    await loading;
    assert.equal(controller.snapshot.value, null);
    assert.equal(controller.state.value, 'idle');
  } finally {
    globalThis.setInterval = originalSetInterval;
    globalThis.clearInterval = originalClearInterval;
  }
});

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
    [6.5, 'Peringatan minimum · Permen LHK 5/2014'],
    [8.5, 'Peringatan maksimum · Permen LHK 5/2014'],
    [6, 'Bahaya minimum · Permen LHK 5/2014'],
    [9, 'Bahaya maksimum · Permen LHK 5/2014'],
  ]);
  assert.deepEqual(tss.map(({ y, label }) => [y, label.text]), [
    [50, 'Peringatan maksimum · Permen LHK 5/2014'],
    [80, 'Bahaya maksimum · Permen LHK 5/2014'],
  ]);
});

test('threshold labels never show the backend provenance code', () => {
  // `source` is a machine code (site_alert_rule / unconfigured); it was shown raw on the chart.
  const snapshot = { thresholds: { ph: { warning_max: 8.5, source: 'site_alert_rule', regulation: null } } };
  assert.deepEqual(buildThresholdAnnotations(snapshot, 'ph').map(({ label }) => label.text), ['Peringatan maksimum']);
  const human = { thresholds: { ph: { warning_max: 8.5, source: 'Baku mutu daerah' } } };
  assert.deepEqual(buildThresholdAnnotations(human, 'ph').map(({ label }) => label.text), ['Peringatan maksimum · Baku mutu daerah']);
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
  // Round ticks: the old pH-aligned axis printed 15.71, 31.43, 47.14…
  assert.deepEqual(scale, { min: 0, max: 100, tickAmount: 5, decimals: 0 });
});

test('niceScale rounds axes to 1/2/2.5/5 steps with matching decimals', () => {
  assert.deepEqual(niceScale(0, 0.055), { min: 0, max: 0.06, tickAmount: 6, decimals: 2 });
  assert.deepEqual(niceScale(0, 176.9), { min: 0, max: 200, tickAmount: 4, decimals: 0 });
  assert.deepEqual(niceScale(5.5, 9.5), { min: 5, max: 10, tickAmount: 5, decimals: 0 });
  assert.deepEqual(niceScale(0, 1.05), { min: 0, max: 1.2, tickAmount: 6, decimals: 1 });
  assert.deepEqual(niceScale(0, 0), { min: 0, max: 1, tickAmount: 5, decimals: 1 });
});

test('pH scale wraps readings and limits instead of the full 0–14 range', () => {
  const snapshot = normalizeTimeseriesPayload({
    meta: { timezone: 'Asia/Jakarta' },
    series: { ph: { points: [{ ts: '2026-08-25T00:00:00Z', value: 8.1 }, { ts: '2026-08-25T00:02:00Z', value: 8.4 }] } },
    statistics: { ph: { current: 8.4 } },
    thresholds: { ph: { danger_min: 6, danger_max: 9 } },
  });
  assert.deepEqual(getPhScale(snapshot), { min: 5, max: 10, tickAmount: 5, decimals: 0 });
  assert.deepEqual(getPhScale(normalizeTimeseriesPayload({})), { min: 0, max: 14, tickAmount: 7, decimals: 0 });
});

test('formatDecimal uses Indonesian separators', () => {
  assert.equal(formatDecimal(8.07, 2), '8,07');
  assert.equal(formatDecimal(1234.5, 1), '1.234,5');
  assert.equal(formatDecimal(null, 2), null);
});

test('formatMeasurement keeps significant decimals only, in Indonesian format', () => {
  assert.equal(formatMeasurement(7.1), '7,1');
  assert.equal(formatMeasurement(-6), '-6');
  assert.equal(formatMeasurement(0.02512), '0,025');
  assert.equal(formatMeasurement(undefined), null);
});

test('time axis ticks land on round local times for every period', () => {
  const HOUR = 3600 * 1000;
  const cases = [
    // [date_from, date_to, timezone, expected step]
    ['2026-10-16T17:00:00Z', '2026-10-17T04:33:00Z', 'Asia/Jakarta', 2 * HOUR], // "Hari ini" 00:00–11:33 WIB
    ['2026-10-16T04:33:00Z', '2026-10-17T04:33:00Z', 'Asia/Jakarta', 3 * HOUR], // 24 jam
    ['2026-10-17T03:33:00Z', '2026-10-17T04:33:00Z', 'Asia/Jakarta', 10 * 60 * 1000], // 1 jam
    ['2026-10-10T04:33:00Z', '2026-10-17T04:33:00Z', 'Asia/Makassar', 24 * HOUR], // 7 hari, WITA
  ];
  for (const [from, to, timeZone, step] of cases) {
    const axis = timeAxisRange(from, to, timeZone);
    assert.equal((axis.max - axis.min) / axis.tickAmount, step, `${from} → ${to}`);
    assert.ok(axis.min <= Date.parse(from) && axis.max >= Date.parse(to));
    assert.ok(axis.tickAmount <= 10);
    const local = new Intl.DateTimeFormat('en-GB', { timeZone, hour: '2-digit', minute: '2-digit', hourCycle: 'h23' });
    const firstTick = local.format(axis.min);
    assert.ok(step >= HOUR ? firstTick.endsWith(':00') : /:[0-5]0$/.test(firstTick), firstTick);
    if (step === 24 * HOUR) assert.equal(firstTick, '00:00');
  }
  assert.equal(timeAxisRange('bad', null, 'Asia/Jakarta'), null);
  assert.ok(timeAxisRange('2026-10-16T17:00:00Z', '2026-10-17T04:33:00Z', 'Asia/Jakarta', 4).tickAmount <= 4);
});

test('event legend lists only the marker kinds present on a chart', () => {
  assert.deepEqual(eventLegendItems([], false), []);
  assert.deepEqual(
    eventLegendItems([{ severity: 'warning' }, { severity: 'critical' }, { severity: 'warning' }], true)
      .map(({ key }) => key),
    ['critical', 'warning', 'line'],
  );
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
  assert.deepEqual(scale, { min: 0, max: 50, tickAmount: 5, decimals: 0, outlierCount: 1 });
});

test('uses the actual Debit maximum in full-scale mode', () => {
  const snapshot = makeDebitSnapshot([...Array.from({ length: 20 }, (_, index) => index), 1000], 40);
  assert.deepEqual(getDebitScale(snapshot, 'full'), { min: 0, max: 1200, tickAmount: 6, decimals: 0, outlierCount: 0 });
});

test('returns a finite positive Debit maximum when all readings are zero', () => {
  assert.deepEqual(getDebitScale(makeDebitSnapshot([0, 0, 0], 0)), {
    min: 0,
    max: 1.2,
    tickAmount: 6,
    decimals: 1,
    outlierCount: 0,
  });
});

test('small Debit values get evenly spaced ticks instead of rounded duplicates', () => {
  // 0.02–0.05 L/min used to show 0.00/0.01/0.02/0.03/… at uneven heights.
  const scale = getDebitScale(makeDebitSnapshot([0.02, 0.05, 0.03, 0.04], 0.02));
  assert.deepEqual([scale.max, scale.tickAmount, scale.decimals], [0.06, 6, 2]);
});

test('buildDangerBands shades only beyond danger limits inside the scale', () => {
  const scale = { min: 0, max: 25 };
  const edges = (bands) => bands.map(({ y, y2 }) => [y, y2]);
  assert.deepEqual(buildDangerBands({ thresholds: { tss: { warning_max: 15 } } }, 'tss', scale), []);
  assert.deepEqual(buildDangerBands({ thresholds: {} }, 'tss', scale), []);
  assert.deepEqual(edges(buildDangerBands({ thresholds: { tss: { danger_max: 18 } } }, 'tss', scale)), [[18, 25]]);
  assert.deepEqual(buildDangerBands({ thresholds: { tss: { danger_max: 30 } } }, 'tss', scale), []);
  assert.deepEqual(edges(buildDangerBands({ thresholds: { tss: { danger_min: 5, danger_max: 18 } } }, 'tss', scale)), [[18, 25], [0, 5]]);
  assert.deepEqual(edges(buildDangerBands({ thresholds: { ph: { lower: { value: 6 }, upper: { value: 9 } } } }, 'ph', { min: 5, max: 10 })), [[9, 10], [5, 6]]);
  assert.deepEqual(edges(buildDangerBands({ thresholds: { ph: { danger_max: 9 } } }, 'ph', { min: 5, max: 10 })), [[9, 10]]);
});
