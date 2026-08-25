import assert from 'node:assert/strict';
import test from 'node:test';
import { fileURLToPath } from 'node:url';
import { resolve } from 'node:path';
import { readFile } from 'node:fs/promises';
import { createRenderer, createSSRApp, h, nextTick } from 'vue';
import * as VueRuntime from 'vue';
import { renderToString } from '@vue/server-renderer';
import { parse, compileScript } from '@vue/compiler-sfc';
import { formatDashboardTimestamp } from '../resources/js/Utils/dashboardTimeseries.js';

process.env.BROWSERSLIST_IGNORE_OLD_DATA = 'true';

const projectRoot = fileURLToPath(new URL('..', import.meta.url));
let vite;
let ChartState;
let ChartSummary;
let PeriodFilter;
let MonitoringEventList;
let DebitTrendChart;
let ChartStateClient;
let PeriodFilterClient;
let MonitoringEventListClient;

test.before(async () => {
  const [{ default: vue }, { createServer }] = await Promise.all([
    import('@vitejs/plugin-vue'),
    import('vite'),
  ]);

  vite = await createServer({
    appType: 'custom',
    configFile: false,
    logLevel: 'silent',
    plugins: [{
      name: 'debit-apex-ssr-stub',
      enforce: 'pre',
      resolveId(id) { return id === 'vue3-apexcharts' ? '\0component-test:apexchart' : null; },
      load(id) { return id === '\0component-test:apexchart' ? "import { h } from 'vue'; export default { setup(_props, { attrs }) { return () => h('div', attrs); } };" : null; },
    }, vue()],
    resolve: { alias: { '@': resolve(projectRoot, 'resources/js') } },
    root: projectRoot,
    ssr: { noExternal: ['vue3-apexcharts'] },
    server: { middlewareMode: true },
  });

  ([
    { default: ChartState },
    { default: ChartSummary },
    { default: PeriodFilter },
    { default: MonitoringEventList },
    { default: DebitTrendChart },
  ] = await Promise.all([
    vite.ssrLoadModule('/resources/js/Components/Dashboard/ChartState.vue'),
    vite.ssrLoadModule('/resources/js/Components/Dashboard/ChartSummary.vue'),
    vite.ssrLoadModule('/resources/js/Components/Dashboard/PeriodFilter.vue'),
    vite.ssrLoadModule('/resources/js/Components/Dashboard/MonitoringEventList.vue'),
    vite.ssrLoadModule('/resources/js/Components/Dashboard/DebitTrendChart.vue'),
  ]));

  [ChartStateClient, PeriodFilterClient, MonitoringEventListClient] = await Promise.all([
    compileClientComponent('ChartState.vue'),
    compileClientComponent('PeriodFilter.vue'),
    compileClientComponent('MonitoringEventList.vue'),
  ]);
});

test.after(async () => vite?.close());

async function render(component, props = {}, slots = {}) {
  return renderToString(createSSRApp({ render: () => h(component, props, slots) }));
}

function importBindings(spec) {
  return spec.split(',').map((entry) => {
    const [name, alias] = entry.trim().split(/\s+as\s+/);
    return alias ? `${name}: ${alias}` : name;
  }).join(', ');
}

async function compileClientComponent(name) {
  const source = await readFile(resolve(projectRoot, 'resources/js/Components/Dashboard', name), 'utf8');
  const { descriptor } = parse(source, { filename: name });
  let code = compileScript(descriptor, { id: `component-test-${name}`, inlineTemplate: true }).content;
  code = code.replace(/import \{([^}]+)\} from ['"]vue['"];?/g, (_match, bindings) => `const { ${importBindings(bindings)} } = VueRuntime;`);
  code = code.replace(/import \{([^}]+)\} from ['"]@\/Utils\/dashboardTimeseries\.js['"];?/g, (_match, bindings) => `const { ${importBindings(bindings)} } = dashboardTimeseries;`);
  code = code.replace('export default', 'return');
  return new Function('VueRuntime', 'dashboardTimeseries', code)(VueRuntime, { formatDashboardTimestamp });
}

function makeNode(type, props = {}, children = []) {
  return { type, props: { ...props }, children: Array.isArray(children) ? children : [children], parent: null };
}

const testRenderer = createRenderer({
  patchProp(node, key, _previous, value) { node.props[key] = value; },
  insert(child, parent, anchor) {
    child.parent = parent;
    const index = anchor ? parent.children.indexOf(anchor) : -1;
    if (index >= 0) parent.children.splice(index, 0, child);
    else parent.children.push(child);
  },
  remove(child) { child.parent?.children.splice(child.parent.children.indexOf(child), 1); },
  createElement(type) { return makeNode(type); },
  createText(text) { return makeNode('#text', { text }); },
  createComment(text) { return makeNode('#comment', { text }); },
  setText(node, text) { node.props.text = text; },
  setElementText(node, text) { node.children = [makeNode('#text', { text })]; },
  parentNode(node) { return node.parent; },
  nextSibling(node) { const siblings = node.parent?.children ?? []; return siblings[siblings.indexOf(node) + 1] ?? null; },
  querySelector() { return null; },
  setScopeId() {},
  cloneNode(node) { return makeNode(node.type, node.props, node.children); },
  insertStaticContent(content, parent) { const node = makeNode('#static', { content }); node.parent = parent; parent.children.push(node); return [node, node]; },
});

function allNodes(node, predicate, found = []) {
  if (predicate(node)) found.push(node);
  node.children?.forEach((child) => allNodes(child, predicate, found));
  return found;
}

async function mount(component, props = {}) {
  const root = makeNode('root');
  const emitted = [];
  const app = testRenderer.createApp({
    render: () => h(component, {
      ...props,
      'onUpdate:modelValue': (value) => emitted.push(['update:modelValue', value]),
      'onUpdate:customRange': (value) => emitted.push(['update:customRange', value]),
      'onApply-custom': () => emitted.push(['apply-custom']),
      'onFocus-event': (value) => emitted.push(['focus-event', value]),
      onRetry: () => emitted.push(['retry']),
    }),
  });
  app.mount(root);
  await nextTick();
  return { root, emitted, unmount: () => app.unmount() };
}

test('ChartState renders a stable busy loading shell', async () => {
  const html = await render(ChartState, { state: 'loading' });
  assert.match(html, /min-h-\[200px\]/);
  assert.match(html, /aria-busy="true"/);
  assert.match(html, /Memuat data pemantauan/);
  assert.doesNotMatch(html, /role="alert"/);
});

test('ChartState renders an Indonesian empty state', async () => {
  const html = await render(ChartState, { state: 'empty' });
  assert.match(html, /Tidak ada data pada periode ini/);
  assert.doesNotMatch(html, /role="alert"/);
});

test('ChartState renders an actionable initial error only as an alert', async () => {
  const html = await render(ChartState, { state: 'error', message: 'Rentang tidak valid' });
  assert.match(html, /role="alert"/);
  assert.match(html, /Data gagal dimuat/);
  assert.match(html, /Rentang tidak valid/);
  assert.match(html, /<button[^>]*>Coba Lagi<\/button>/);
});

test('ChartState preserves ready slot content during partial and stale states', async () => {
  const partial = await render(ChartState, {
    state: 'partial', partialReasons: ['missing_intervals', 'event_limit_reached'], availability: 0,
  }, { default: () => h('div', { id: 'chart-snapshot' }, 'snapshot') });
  const stale = await render(ChartState, { state: 'stale', message: 'Jaringan putus' }, {
    default: () => h('div', { id: 'chart-snapshot' }, 'snapshot'),
  });
  assert.match(partial, /id="chart-snapshot"/);
  assert.match(partial, /Data tidak lengkap/);
  assert.match(partial, /Ada interval data yang hilang/);
  assert.match(partial, /Jumlah event dibatasi/);
  assert.match(partial, /Ketersediaan data: 0%/);
  assert.doesNotMatch(partial, /role="alert"/);
  assert.match(stale, /id="chart-snapshot"/);
  assert.match(stale, /Pembaruan gagal — menampilkan data terakhir/);
  assert.match(stale, /aria-live="polite"/);
  assert.match(stale, /Coba Lagi/);
});

test('ChartState emits retry from its labeled native retry action', async () => {
  const view = await mount(ChartStateClient, { state: 'error', message: '', partialReasons: [], availability: undefined });
  const retryButton = allNodes(view.root, (node) => node.type === 'button')[0];
  retryButton.props.onClick();
  assert.deepEqual(view.emitted, [['retry']]);
  view.unmount();
});

test('ChartSummary preserves zero precision, masks absent values, and uses backend status metadata', async () => {
  const html = await render(ChartSummary, {
    field: 'debit', label: 'Debit', unit: 'L/menit', decimals: 2,
    summary: {
      current: 0, avg: null, min: 0, max: 12.345,
      availability_pct: 0, status: 'warning', status_label: 'Periksa aliran',
      status_reason: 'Debit rendah', status_severity: 'warning', flow_state: 'no_flow',
    },
  });
  assert.match(html, /0\.00 L\/menit/);
  assert.match(html, /12\.35 L\/menit/);
  assert.match(html, /—/);
  assert.match(html, /Periksa aliran/);
  assert.match(html, /Debit rendah/);
  assert.match(html, /Aliran terhenti/);
  assert.match(html, /Ketersediaan 0%/);
  assert.match(html, /font-mono/);
});

test('ChartSummary has distinct explicit fallbacks for no-flow, no-data, sensor-error, critical, warning and normal', async () => {
  const cases = [
    ['no_flow', 'Aliran Terhenti'], ['no_data', 'Tidak Ada Data'], ['sensor_error', 'Kesalahan Sensor'],
    ['critical', 'Kritis'], ['warning', 'Peringatan'], ['normal', 'Normal'],
  ];
  for (const [status, label] of cases) {
    const html = await render(ChartSummary, { field: 'debit', summary: { status }, label: 'Debit' });
    assert.match(html, new RegExp(label));
    assert.match(html, /aria-label="Status:/);
  }
  const withoutAvailability = await render(ChartSummary, { field: 'ph', summary: { current: null }, label: 'pH' });
  assert.doesNotMatch(withoutAvailability, /Ketersediaan/);
});

test('DebitTrendChart keeps zero flow, unavailable data, and sensor error as separate textual states', async () => {
  const base = {
    meta: { timezone: 'Asia/Jakarta', date_from: '2026-08-25T00:00:00Z', date_to: '2026-08-25T00:05:00Z', generated_at: '2026-08-25T00:06:00Z', resolution_seconds: 300 },
    series: { debit: { label: 'Debit', unit: 'L/min', points: [{ ts: '2026-08-25T00:05:00Z', value: 0 }] } },
    thresholds: { debit: { warning_max: 20, danger_max: 30 } }, events: [],
  };
  const zero = await render(DebitTrendChart, {
    snapshot: { ...base, statistics: { debit: { current: 0, current_ts: '2026-08-25T00:05:00Z', status: 'no_flow', status_label: 'No Flow', flow_state: 'no_flow' } } },
    state: 'ready', stale: false, focusedEventId: null, reducedMotion: true,
  });
  assert.match(zero, /0\.00 L\/min/);
  assert.match(zero, /No Flow/);
  assert.match(zero, /Aliran terhenti/);

  const missing = await render(DebitTrendChart, {
    snapshot: { ...base, statistics: { debit: { current: null, current_ts: null, status: 'no_data', status_label: 'No Data', flow_state: 'no_data' } } },
    state: 'ready', stale: false, focusedEventId: null, reducedMotion: true,
  });
  assert.match(missing, /No Data/);

  const sensorError = await render(DebitTrendChart, {
    snapshot: { ...base, statistics: { debit: { current: null, current_ts: null, status: 'sensor_error', status_label: 'Sensor Error', flow_state: 'sensor_error' } } },
    state: 'ready', stale: false, focusedEventId: null, reducedMotion: true,
  });
  assert.match(sensorError, /Sensor Error/);
  assert.doesNotMatch(sensorError, />No Data</);
});

test('PeriodFilter renders every period, labels custom controls, and keeps the apply button disabled until complete', async () => {
  const html = await render(PeriodFilter, {
    modelValue: 'custom', customRange: { dateFrom: '2026-08-25T00:00', dateTo: '' }, timezone: 'Asia/Jakarta',
  });
  for (const period of ['1h', '6h', '12h', 'today', '24h', '7d', 'custom']) assert.match(html, new RegExp(`value="${period}"|>${period === 'today' ? 'Hari ini' : period === 'custom' ? 'Kustom' : period}<`));
  assert.match(html, /aria-label="Pilih periode pemantauan"/);
  assert.match(html, /<label[^>]*>Mulai/);
  assert.match(html, /<label[^>]*>Selesai/);
  assert.match(html, /Zona waktu: Asia\/Jakarta/);
  assert.match(html, /disabled/);
});

test('PeriodFilter emits immutable period/range values and applies only a complete custom range', async () => {
  const original = { dateFrom: '', dateTo: '' };
  const periodView = await mount(PeriodFilterClient, { modelValue: '1h', customRange: original, timezone: 'Asia/Jakarta' });
  const customButton = allNodes(periodView.root, (node) => node.type === 'button')
    .find((button) => button.children?.some((child) => child.props?.text === 'Kustom'));
  customButton.props.onClick();
  assert.deepEqual(periodView.emitted, [['update:modelValue', 'custom']]);
  periodView.unmount();

  const view = await mount(PeriodFilterClient, { modelValue: 'custom', customRange: original, timezone: 'Asia/Jakarta' });
  const [start, end] = allNodes(view.root, (node) => node.type === 'input');
  start.props.onInput({ target: { value: '2026-08-25T00:00' } });
  end.props.onInput({ target: { value: '2026-08-25T01:00' } });
  const apply = allNodes(view.root, (node) => node.type === 'button' && node.children?.some((child) => child.props?.text === 'Terapkan rentang'))[0];
  apply.props.onClick();
  assert.deepEqual(original, { dateFrom: '', dateTo: '' });
  assert.deepEqual(view.emitted, [
    ['update:customRange', { dateFrom: '2026-08-25T00:00', dateTo: '' }],
    ['update:customRange', { dateFrom: '', dateTo: '2026-08-25T01:00' }],
  ]);
  view.unmount();

  const complete = await mount(PeriodFilterClient, {
    modelValue: 'custom', customRange: { dateFrom: '2026-08-25T00:00', dateTo: '2026-08-25T01:00' }, timezone: 'Asia/Jakarta',
  });
  const completeApply = allNodes(complete.root, (node) => node.type === 'button' && node.children?.some((child) => child.props?.text === 'Terapkan rentang'))[0];
  assert.equal(completeApply.props.disabled, false);
  completeApply.props.onClick();
  assert.deepEqual(complete.emitted, [['apply-custom']]);
  complete.unmount();
});

test('MonitoringEventList renders deterministic time, useful typed context, capped count, and an empty state', async () => {
  const event = {
    id: 'evt-7', ts: '2026-08-24T18:38:00Z', end_ts: '2026-08-24T18:43:00Z', type: 'low_flow_tss_check',
    field: 'debit', severity: 'warning', direction: 'down', label: 'Debit rendah perlu pemeriksaan',
    context: { interval_seconds: 300, current: 0, debit: { value: 0, flow_state: 'no_flow' }, tss: { baseline: 10, current: 0, delta: -10, percent: -100 } },
  };
  const html = await render(MonitoringEventList, { events: [event], eventTotal: 2, timezone: 'Asia/Jakarta' });
  assert.match(html, /25 Agu 2026 • 01:38/);
  assert.match(html, /Peringatan/);
  assert.match(html, /Debit: 0/);
  assert.match(html, /TSS: 0/);
  assert.match(html, /Interval: 5 menit/);
  assert.match(html, /Menampilkan 1 dari 2 event/);
  assert.match(html, /<button/);
  const empty = await render(MonitoringEventList, { events: [], eventTotal: 0, timezone: 'Asia/Jakarta' });
  assert.match(empty, /Belum ada event pemantauan pada periode ini/);
});

test('MonitoringEventList ignores malformed entries without hiding valid events', async () => {
  const validEvent = {
    id: 'evt-valid', ts: '2026-08-24T18:38:00Z', type: 'rapid_change', severity: 'warning',
    label: 'Perubahan cepat yang valid', context: { current: 0 },
  };
  const html = await render(MonitoringEventList, {
    events: [null, validEvent, 'invalid-record'], eventTotal: 4, timezone: 'Asia/Jakarta',
  });
  assert.match(html, /Perubahan cepat yang valid/);
  assert.match(html, /Menampilkan 1 dari 4 event/);
  assert.doesNotMatch(html, /Belum ada event pemantauan/);
});

test('MonitoringEventList truthfully reports unrenderable event details when every raw record is malformed', async () => {
  const html = await render(MonitoringEventList, {
    events: [null, 'invalid-record'], eventTotal: 2, timezone: 'Asia/Jakarta',
  });
  assert.match(html, /Menampilkan 0 dari 2 event/);
  assert.match(html, /Event terdeteksi, tetapi detailnya tidak dapat ditampilkan/);
  assert.doesNotMatch(html, /Belum ada event pemantauan pada periode ini/);
});

test('reusable PeriodFilter and MonitoringEventList instances do not introduce duplicate static IDs', async () => {
  const html = await renderToString(createSSRApp({
    render: () => h('div', [
      h(PeriodFilter, { modelValue: 'custom', customRange: {}, timezone: 'Asia/Jakarta' }),
      h(PeriodFilter, { modelValue: 'custom', customRange: {}, timezone: 'Asia/Jakarta' }),
      h(MonitoringEventList, { events: [], eventTotal: 0, timezone: 'Asia/Jakarta' }),
      h(MonitoringEventList, { events: [], eventTotal: 0, timezone: 'Asia/Jakarta' }),
    ]),
  }));
  assert.doesNotMatch(html, /\bid="(?:period-custom-(?:start|end)|monitoring-events-title)"/);
});

test('MonitoringEventList emits the original event payload from a focusable native row button', async () => {
  const event = { id: 'evt-1', ts: '2026-08-24T18:38:00Z', type: 'rapid_change', severity: 'critical', label: 'Perubahan cepat', context: { current: 0 } };
  const view = await mount(MonitoringEventListClient, { events: [event], eventTotal: 1, timezone: 'Asia/Jakarta' });
  const rowButton = allNodes(view.root, (node) => node.type === 'button')[0];
  assert.equal(rowButton.props.type, 'button');
  rowButton.props.onClick();
  assert.deepEqual(view.emitted, [['focus-event', event]]);
  view.unmount();
});
