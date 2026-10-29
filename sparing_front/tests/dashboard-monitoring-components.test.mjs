import assert from 'node:assert/strict';
import test from 'node:test';
import { fileURLToPath } from 'node:url';
import { resolve } from 'node:path';
import { readFile } from 'node:fs/promises';
import { createRenderer, createSSRApp, h, nextTick, ssrContextKey } from 'vue';
import * as VueRuntime from 'vue';
import { renderToString } from '@vue/server-renderer';
import { parse, compileScript } from '@vue/compiler-sfc';
import postcss from 'postcss';
import tailwindcss from 'tailwindcss';
import tailwindConfig from '../tailwind.config.js';
import * as dashboardTimeseriesModule from '../resources/js/Utils/dashboardTimeseries.js';

process.env.BROWSERSLIST_IGNORE_OLD_DATA = 'true';

const projectRoot = fileURLToPath(new URL('..', import.meta.url));
let vite;
let ChartState;
let ChartSummary;
let PeriodFilter;
let MonitoringEventList;
let DebitTrendChart;
let WaterQualityTrendChart;
let Dashboard;
let ChartStateClient;
let PeriodFilterClient;
let MonitoringEventListClient;
let SiteStatusChips;
let SiteStatusChipsClient;

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
      resolveId(id) {
        const normalized = id.replaceAll('\\\\', '/');
        if (id === 'vue3-apexcharts') return '\0component-test:apexchart';
        if (id === '@/Layouts/AppLayout.vue') return '\0component-test:layout';
        if (id === '@/Components/PageHeader.vue') return '\0component-test:page-header';
        if (['@/Components/SiteMap.vue', '@/Components/StatusBadge.vue', '@/Components/DataTable.vue', '@/Components/Sparkline.vue'].includes(id)) return '\0component-test:component';
        if (id === '@/Composables/useApi') return '\0component-test:api';
        if (id === '@/Composables/useAuth') return '\0component-test:auth';
        if (normalized.endsWith('/resources/js/Layouts/AppLayout.vue')) return '\0component-test:layout';
        if (normalized.endsWith('/resources/js/Components/PageHeader.vue')) return '\0component-test:page-header';
        if (['SiteMap.vue', 'StatusBadge.vue', 'DataTable.vue', 'Sparkline.vue'].some((name) => normalized.endsWith(`/resources/js/Components/${name}`))) return '\0component-test:component';
        if (normalized.endsWith('/resources/js/Composables/useApi.js')) return '\0component-test:api';
        if (normalized.endsWith('/resources/js/Composables/useAuth.js')) return '\0component-test:auth';
        return null;
      },
      load(id) {
        if (id === '\0component-test:apexchart') return "import { h } from 'vue'; export default { props: { options: Object }, setup(props, { attrs }) { return () => h('div', { ...attrs, 'data-apex-id': props.options?.chart?.id, 'data-apex-motion': String(Boolean(props.options?.chart?.animations?.enabled)) }); } };";
        if (id === '\0component-test:layout') return "import { h } from 'vue'; export default { setup(_props, { slots }) { return () => h('main', slots.default?.()); } };";
        if (id === '\0component-test:page-header') return "import { h } from 'vue'; export default { setup(_props, { slots }) { return () => h('header', [slots.default?.(), slots.actions?.()]); } };";
        if (id === '\0component-test:component') return "import { h } from 'vue'; export default { setup() { return () => h('div'); } };";
        if (id === '\0component-test:api') return "export function useApi() { const list = async () => []; return { getLatestData: async () => null, getData: list, getDevices: list, getSites: list, getSensorHealth: list, getCompliance: async () => null, getCompleteness: async () => null, getAlertCount: async () => ({ count: 0 }), getAlerts: list, getAlertRules: list, getLoggerStatus: list, getComplianceDaily: async () => ({ days: [] }), followupAlert: async () => ({}), getDashboardTimeseries: async () => ({ meta: { timezone: 'Asia/Jakarta' }, series: {}, statistics: {}, thresholds: {}, events: [], event_total: 0 }) }; }";
        if (id === '\0component-test:auth') return "import { ref } from 'vue'; export function useAuth() { return { filterSitesByUser: (sites) => sites, isOperator: ref(true) }; }";
        return null;
      },
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
    { default: WaterQualityTrendChart },
    { default: Dashboard },
    { default: SiteStatusChips },
  ] = await Promise.all([
    vite.ssrLoadModule('/resources/js/Components/Dashboard/ChartState.vue'),
    vite.ssrLoadModule('/resources/js/Components/Dashboard/ChartSummary.vue'),
    vite.ssrLoadModule('/resources/js/Components/Dashboard/PeriodFilter.vue'),
    vite.ssrLoadModule('/resources/js/Components/Dashboard/MonitoringEventList.vue'),
    vite.ssrLoadModule('/resources/js/Components/Dashboard/DebitTrendChart.vue'),
    vite.ssrLoadModule('/resources/js/Components/Dashboard/WaterQualityTrendChart.vue'),
    vite.ssrLoadModule('/resources/js/Pages/Dashboard/Index.vue'),
    vite.ssrLoadModule('/resources/js/Components/Dashboard/SiteStatusChips.vue'),
  ]));

  [ChartStateClient, PeriodFilterClient, MonitoringEventListClient, SiteStatusChipsClient] = await Promise.all([
    compileClientComponent('ChartState.vue'),
    compileClientComponent('PeriodFilter.vue'),
    compileClientComponent('MonitoringEventList.vue'),
    compileClientComponent('SiteStatusChips.vue'),
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
  return new Function('VueRuntime', 'dashboardTimeseries', code)(VueRuntime, dashboardTimeseriesModule);
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

async function mountDashboardMotionProbe() {
  const root = makeNode('root');
  let state;
  const app = testRenderer.createApp({
    setup(props, context) {
      state = Dashboard.setup(props, context);
      return () => h('div');
    },
  });
  app.provide(ssrContextKey, { modules: new Set() });
  app.mount(root);
  await nextTick();
  return { state, unmount: () => app.unmount() };
}

async function compiledTailwind(html) {
  const result = await postcss([
    tailwindcss({ ...tailwindConfig, content: [{ raw: html, extension: 'html' }] }),
  ]).process('@tailwind utilities;', { from: undefined });
  return result.css;
}

async function compiledDashboardStyles(html) {
  const source = await readFile(resolve(projectRoot, 'resources/css/app.css'), 'utf8');
  return postcss([
    tailwindcss({ ...tailwindConfig, content: [{ raw: html, extension: 'html' }] }),
  ]).process(source, { from: resolve(projectRoot, 'resources/css/app.css') });
}

function generatedDeclaration(root, selectorPart, property, media = null) {
  const matches = [];
  let order = 0;
  root.walkRules((rule) => {
    const currentOrder = order++;
    const mediaAncestor = (() => {
      let parent = rule.parent;
      while (parent) {
        if (parent.type === 'atrule' && parent.name === 'media') return parent.params;
        parent = parent.parent;
      }
      return null;
    })();
    if (!rule.selector?.includes(selectorPart) || mediaAncestor !== media) return;
    rule.walkDecls(property, (declaration) => matches.push({ value: declaration.value, order: currentOrder, selector: rule.selector }));
  });
  assert.equal(matches.length, 1, `Expected one generated ${property} declaration for ${selectorPart}`);
  return matches[0];
}

async function renderDashboard(snapshot) {
  const component = {
    ...Dashboard,
    setup(props, context) {
      const state = Dashboard.setup(props, context);
      const site = { uid: 'site-1', name: 'IPAL Utama', company_name: 'PT Tirta', timezone: 'Asia/Jakarta' };
      state.sites.value = [site];
      state.currentSite.value = site;
      state.selectedSiteUid.value = site.uid;
      state.latestData.value = { ts: '2026-08-25T00:05:00Z', ph: 7.2, tss: 19.5, debit: 0 };
      state.timeseriesSnapshot.value = snapshot;
      state.timeseriesState.value = 'ready';
      state.statsLoaded.value = true;
      return state;
    },
  };
  const app = createSSRApp(component);
  app.component('router-link', { setup(_props, { slots }) { return () => h('a', slots.default?.()); } });
  return renderToString(app);
}

function monitoringSnapshot() {
  return {
    meta: { timezone: 'Asia/Jakarta', date_from: '2026-08-25T00:00:00Z', date_to: '2026-08-25T01:00:00Z', generated_at: '2026-08-25T01:00:00Z', resolution_seconds: 300 },
    series: {
      ph: { label: 'pH', points: [{ ts: '2026-08-25T00:55:00Z', value: 7.2 }] },
      tss: { label: 'TSS', unit: 'mg/L', points: [{ ts: '2026-08-25T00:55:00Z', value: 19.5 }] },
      debit: { label: 'Debit', unit: 'L/min', points: [{ ts: '2026-08-25T00:55:00Z', value: 0 }] },
    },
    statistics: {
      ph: { current: 7.2, current_ts: '2026-08-25T00:55:00Z', status: 'normal', status_label: 'Normal', availability_pct: 100 },
      tss: { current: 19.5, current_ts: '2026-08-25T00:55:00Z', status: 'warning', status_label: 'Peringatan', availability_pct: 100 },
      debit: { current: 0, current_ts: '2026-08-25T00:55:00Z', status: 'no_flow', status_label: 'Aliran Terhenti', availability_pct: 100 },
    }, thresholds: { ph: {}, tss: {}, debit: {} }, events: [{ id: 'event-1', ts: '2026-08-25T00:55:00Z', field: 'debit', type: 'no_flow', label: 'Debit rendah' }], event_total: 1,
  };
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
  assert.match(html, /0,00 L\/menit/);
  assert.match(html, /12,35 L\/menit/);
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
  assert.match(zero, /0,00 L\/min/);
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

test('DebitTrendChart gives explicit flow state precedence and truthful status-only flow fallbacks', async () => {
  const base = {
    meta: { timezone: 'Asia/Jakarta', date_from: '2026-08-25T00:00:00Z', date_to: '2026-08-25T00:05:00Z', generated_at: '2026-08-25T00:06:00Z', resolution_seconds: 300 },
    series: { debit: { label: 'Debit', unit: 'L/min', points: [{ ts: '2026-08-25T00:05:00Z', value: 2 }] } }, thresholds: { debit: {} }, events: [],
  };
  const cases = [
    [{ current: 2, status: 'no_flow', status_label: 'No Flow', flow_state: 'flowing' }, 'Aliran normal'],
    [{ current: 0, status: 'no_flow', status_label: 'No Flow' }, 'Aliran terhenti'],
    [{ current: 1, status: 'warning', status_label: 'Peringatan', status_reason: 'low_flow_detected' }, 'Aliran rendah'],
    [{ current: null, status: 'sensor_error', status_label: 'Sensor Error' }, 'Kesalahan sensor aliran'],
    [{ current: null, status: 'no_data', status_label: 'No Data' }, 'Tidak ada data aliran'],
    [{ current: 0, status: 'normal', status_label: 'Normal' }, 'Pembacaan debit 0,00 L/min terdeteksi; status aliran belum dikonfigurasi'],
    [{ current: 2, status: 'normal', status_label: 'Normal' }, 'Aliran terdeteksi; status aliran belum dikonfigurasi'],
  ];
  for (const [summary, expected] of cases) {
    const html = await render(DebitTrendChart, {
      snapshot: { ...base, statistics: { debit: { ...summary, current_ts: summary.current === null ? null : '2026-08-25T00:05:00Z' } } },
      state: 'ready', stale: false, focusedEventId: null, reducedMotion: true,
    });
    assert.match(html, new RegExp(expected.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')));
    assert.match(html, new RegExp(summary.status_label));
  }
});

test('PeriodFilter renders every period, labels custom controls, and keeps the apply button disabled until complete', async () => {
  const html = await render(PeriodFilter, {
    modelValue: 'custom', customRange: { dateFrom: '2026-08-25T00:00', dateTo: '' }, timezone: 'Asia/Jakarta',
  });
  const labels = { '1h': '1 jam', '6h': '6 jam', '12h': '12 jam', today: 'Hari ini', '24h': '24 jam', '7d': '7 hari', custom: 'Kustom' };
  for (const [period, label] of Object.entries(labels)) {
    assert.match(html, new RegExp(`value="${period}"`));
    assert.match(html, new RegExp(`>${label}<`));
  }
  assert.doesNotMatch(html, />(1h|6h|12h|24h|7d)</);
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

test('responsive containment mutation: compiled monitoring SSR keeps chart items shrink-safe while period controls switch at 375px and 768px', async () => {
  const html = await renderDashboard(monitoringSnapshot());
  const css = await compiledTailwind(html);

  assert.match(html, /<section class="chart-container[^\"]*\bmin-w-0\b[^\"]*\bmax-w-full\b/);
  assert.match(html, /<div class="[^\"]*\bmin-w-0\b[^\"]*\bmax-w-full\b[^\"]*" role="img"/);
  assert.match(html, /class="hidden w-full flex-wrap gap-1 sm:flex"/);
  assert.match(html, /class="block sm:hidden"/);
  // The event list sits bare inside the sheet and stacks under the chart below lg.
  assert.match(html, /<section class="min-w-0 max-w-full overflow-hidden[^"]*"[^>]*aria-label="Event pemantauan"[\s\S]*?<button type="button" class="w-full/);
  assert.match(html, /class="grid grid-cols-1 lg:grid-cols-\[minmax\(0,2\.2fr\)_minmax\(16rem,1fr\)\]"/);
  assert.match(css, /\.min-w-0\s*\{\s*min-width:\s*0px/);
  assert.match(css, /\.max-w-full\s*\{\s*max-width:\s*100%/);
  assert.match(css, /@media \(min-width: 640px\)[\s\S]*?\.sm\\:hidden\s*\{\s*display:\s*none/);
  assert.match(css, /@media \(min-width: 640px\)[\s\S]*?\.sm\\:flex\s*\{\s*display:\s*flex/);
});

test('keyboard accessibility mutation: monitoring actions expose local focus rings and the debit scale has group semantics', async () => {
  const [error, stale, period, events, debit, siteChips] = await Promise.all([
    render(ChartState, { state: 'error' }),
    render(ChartState, { state: 'stale' }),
    render(PeriodFilter, { modelValue: 'custom', customRange: { dateFrom: '2026-08-25T00:00', dateTo: '2026-08-25T01:00' } }),
    render(MonitoringEventList, { events: [{ id: 'event-1', ts: '2026-08-25T00:00:00Z', label: 'Debit rendah' }], eventTotal: 1 }),
    render(DebitTrendChart, { snapshot: monitoringSnapshot(), state: 'ready' }),
    render(SiteStatusChips, { chips: [{ uid: 'a', name: 'IPAL Utama', status: 'normal' }, { uid: 'b', name: 'IPAL Cadangan', status: 'warning' }], modelValue: 'a' }),
  ]);

  for (const html of [error, stale]) assert.match(html, /<button[^>]*class="[^\"]*focus-visible:outline[^\"]*focus-visible:outline-2[^\"]*focus-visible:outline-offset-2/);
  assert.match(period, /<button[^>]*class="[^\"]*focus-visible:outline[^\"]*focus-visible:outline-2/);
  assert.match(period, /<select[^>]*class="[^\"]*focus-visible:outline[^\"]*focus-visible:outline-2/);
  assert.match(period, /<input[^>]*class="[^\"]*focus-visible:outline[^\"]*focus-visible:outline-2/);
  assert.match(events, /<button[^>]*class="[^\"]*focus-visible:outline[^\"]*focus-visible:outline-2[^\"]*focus-visible:outline-offset-\[-2px\]/);
  assert.match(siteChips, /<button[^>]*class="[^\"]*focus-visible:outline[^\"]*focus-visible:outline-2[^\"]*focus-visible:outline-offset-2/);
  assert.match(debit, /role="group" aria-label="Pilihan skala grafik debit"/);
  assert.match(debit, /Status aliran: Aliran terhenti/);
});

test('local motion-reduce mutation: monitoring cards and loading skeletons opt out of their own hover and animation effects', async () => {
  const [loading, water, events] = await Promise.all([
    render(ChartState, { state: 'loading' }),
    render(WaterQualityTrendChart, { snapshot: monitoringSnapshot(), state: 'ready' }),
    render(MonitoringEventList, { events: [{ id: 'event-1', ts: '2026-08-25T00:00:00Z', label: 'Debit rendah' }], eventTotal: 1 }),
  ]);
  assert.match(loading, /class="skeleton[^\"]*motion-reduce:animate-none/);
  assert.match(water, /class="sensor-card[^\"]*motion-reduce:hover:transform-none[^\"]*motion-reduce:transition-none/);
  assert.match(events, /class="sensor-card[^\"]*motion-reduce:hover:transform-none[^\"]*motion-reduce:transition-none/);
});

test('reduced-motion hover cascade mutation: compiled card hover translation loses to an equally specific reduce-motion hover override', async () => {
  const water = await render(WaterQualityTrendChart, { snapshot: monitoringSnapshot(), state: 'ready' });
  const styles = await compiledDashboardStyles(water);
  const hoverTransform = generatedDeclaration(styles.root, '.sensor-card:hover', 'transform');
  const reducedHoverTransform = generatedDeclaration(styles.root, '.motion-reduce\\:hover\\:transform-none:hover', 'transform', '(prefers-reduced-motion: reduce)');

  assert.match(water, /class="sensor-card[^\"]*motion-reduce:hover:transform-none/);
  assert.equal(hoverTransform.value, 'translateY(-1px)');
  assert.equal(reducedHoverTransform.value, 'none');
  assert.ok(reducedHoverTransform.order > hoverTransform.order, 'the equally specific reduce-motion hover rule must follow the card hover rule');
});

test('event focus containment mutation: compiled event focus indicator uses an inset offset inside the clipped sensor card', async () => {
  const events = await render(MonitoringEventList, {
    events: [{ id: 'event-1', ts: '2026-08-25T00:00:00Z', label: 'Debit rendah' }], eventTotal: 1,
  });
  const styles = await compiledDashboardStyles(events);
  const cardOverflow = generatedDeclaration(styles.root, '.sensor-card', 'overflow');
  const focusOffset = generatedDeclaration(styles.root, '.focus-visible\\:outline-offset-\\[-2px\\]:focus-visible', 'outline-offset');

  assert.match(events, /class="w-full[^\"]*focus-visible:outline-offset-\[-2px\]/);
  assert.equal(cardOverflow.value, 'hidden');
  assert.equal(focusOffset.value, '-2px');
});

test('reduced-motion mutation: Dashboard tracks the media preference, disables both compiled chart animations, and unregisters the listener', async () => {
  const previousWindow = globalThis.window;
  const listeners = new Set();
  const media = {
    matches: true,
    addEventListener(type, listener) { if (type === 'change') listeners.add(listener); },
    removeEventListener(type, listener) { if (type === 'change') listeners.delete(listener); },
  };
  globalThis.window = { matchMedia: () => media };

  let view;
  try {
    view = await mountDashboardMotionProbe();
    await nextTick();
    await new Promise((resolve) => setImmediate(resolve));
    await nextTick();
    assert.equal(listeners.size, 1);
    assert.equal(view.state.reducedMotion.value, true);
    const [water, debit] = await Promise.all([
      render(WaterQualityTrendChart, { snapshot: monitoringSnapshot(), state: 'ready', reducedMotion: view.state.reducedMotion.value }),
      render(DebitTrendChart, { snapshot: monitoringSnapshot(), state: 'ready', reducedMotion: view.state.reducedMotion.value }),
    ]);
    assert.match(water, /data-apex-id="dashboard-ph" data-apex-motion="false"/);
    assert.match(water, /data-apex-id="dashboard-tss" data-apex-motion="false"/);
    assert.match(debit, /data-apex-id="dashboard-debit" data-apex-motion="false"/);
    view.unmount();
    view = null;
    assert.equal(listeners.size, 0);
  } finally {
    view?.unmount();
    if (previousWindow === undefined) delete globalThis.window;
    else globalThis.window = previousWindow;
  }
});

test('SiteStatusChips renders one pressed chip per site with status text and hides for a single site', async () => {
  const chips = [
    { uid: 'b', name: 'IPAL Cadangan', status: 'offline' },
    { uid: 'a', name: 'IPAL Utama', status: 'normal' },
  ];
  const html = await render(SiteStatusChips, { chips, modelValue: 'a' });
  assert.match(html, /role="group" aria-label="Pilih lokasi pemantauan"/);
  assert.equal(html.match(/aria-pressed="true"/g)?.length, 1);
  assert.match(html, /<button[^>]*aria-pressed="true"[^>]*>(?:(?!<\/button>)[\s\S])*IPAL Utama/);
  assert.match(html, /IPAL Cadangan(?:(?!<\/button>)[\s\S])*mati/);
  // The scroller must be a containing block: the absolutely positioned sr-only
  // status text otherwise escapes the overflow clip and widens the whole page.
  const scrollerClass = html.match(/role="group" aria-label="Pilih lokasi pemantauan" class="([^"]*)"/)?.[1].split(/\s+/) ?? [];
  assert.ok(scrollerClass.includes('overflow-x-auto'));
  assert.ok(scrollerClass.includes('relative'), 'chip scroller must be position: relative');
  // Phones: no native scrollbar under the chips; an edge fade shows there is more.
  assert.ok(scrollerClass.includes('chip-scroller'));
  // No scroll-snap: when chips re-sort the browser kept the old snap target in
  // view and pushed the selected chip out of the row.
  assert.ok(!scrollerClass.includes('snap-x'));

  const single = await render(SiteStatusChips, { chips: [chips[1]], modelValue: 'a' });
  assert.doesNotMatch(single, /Pilih lokasi pemantauan/);
});

test('SiteStatusChips emits the clicked site and ignores the active one', async () => {
  const chips = [
    { uid: 'a', name: 'IPAL Utama', status: 'normal' },
    { uid: 'b', name: 'IPAL Cadangan', status: 'warning' },
  ];
  const view = await mount(SiteStatusChipsClient, { chips, modelValue: 'a' });
  const buttons = allNodes(view.root, (node) => node.type === 'button');
  buttons[0].props.onClick();
  buttons[1].props.onClick();
  assert.deepEqual(view.emitted, [['update:modelValue', 'b']]);
  view.unmount();
});

test('ChartSummary translates API reason codes and never shows a raw code', async () => {
  const cases = [
    [{ status: 'sensor_error', status_reason: 'explicit_sensor_error' }, /Logger melaporkan sensor error\./],
    [{ status: 'warning', status_reason: 'low_flow_detected' }, /Debit rendah terdeteksi\./],
    [{ status: 'critical', status_reason: 'some_future_code' }, /Nilai melewati batas bahaya\./],
  ];
  for (const [summary, text] of cases) {
    const html = await render(ChartSummary, { field: 'ph', label: 'pH', summary: { current: 7, ...summary } });
    assert.match(html, text);
    assert.doesNotMatch(html, new RegExp(summary.status_reason));
  }
});

test('ChartSummary labels an old-but-present reading as Data Tidak Terbaru', async () => {
  const stale = await render(ChartSummary, { field: 'ph', label: 'pH', summary: {
    current: 8.21, status: 'no_data', status_label: 'Tidak Ada Data', status_reason: 'stale_measurement', status_severity: 'warning',
  } });
  assert.match(stale, /Data Tidak Terbaru/);
  assert.match(stale, /Pembacaan terakhir sudah lama\./);
  assert.doesNotMatch(stale, /Tidak Ada Data/);

  const empty = await render(ChartSummary, { field: 'ph', label: 'pH', summary: {
    current: null, status: 'no_data', status_label: 'Tidak Ada Data', status_reason: 'stale_measurement',
  } });
  assert.match(empty, /Tidak Ada Data/);
});

test('MonitoringEventList shows the six newest events first and expands to the rest', async () => {
  const events = Array.from({ length: 8 }, (_, index) => ({
    id: `evt-${index}`, ts: new Date(Date.UTC(2026, 9, 13, index)).toISOString(),
    type: 'send_fail', severity: 'warning', label: `Event ${index}`,
  }));
  const html = await render(MonitoringEventList, { events, eventTotal: 8, timezone: 'Asia/Jakarta' });
  assert.deepEqual([...html.matchAll(/Event (\d)/g)].map((match) => match[1]), ['7', '6', '5', '4', '3', '2']);
  assert.match(html, /Menampilkan 6 dari 8 event/);
  assert.match(html, /Tampilkan semua \(8\)/);

  const view = await mount(MonitoringEventListClient, { events, eventTotal: 8, timezone: 'Asia/Jakarta' });
  const toggle = allNodes(view.root, (node) => node.type === 'button' && node.props['aria-expanded'] !== undefined)[0];
  assert.equal(toggle.props['aria-expanded'], 'false');
  toggle.props.onClick();
  await nextTick();
  assert.equal(allNodes(view.root, (node) => node.type === 'li').length, 8);
  view.unmount();

  const few = await render(MonitoringEventList, { events: events.slice(0, 6), eventTotal: 6, timezone: 'Asia/Jakarta' });
  assert.doesNotMatch(few, /Tampilkan semua/);
});


test('ChartState can leave the partial-data notice to a sibling chart', async () => {
  const html = await render(ChartState, {
    state: 'partial', partialReasons: ['missing_intervals'], availability: 90.2, showPartialNotice: false,
  }, { default: () => h('div', { id: 'chart-snapshot' }, 'snapshot') });
  assert.match(html, /id="chart-snapshot"/);
  assert.doesNotMatch(html, /Data tidak lengkap/);

  const shown = await render(ChartState, { state: 'partial', partialReasons: [], availability: 90.2 }, {
    default: () => h('div', 'snapshot'),
  });
  assert.match(shown, /Ketersediaan data: 90,2%/);
});

test('MonitoringEventList names parameters, formats values in Indonesian and hides empty intervals', async () => {
  const html = await render(MonitoringEventList, {
    events: [
      { id: 'a', ts: '2026-08-24T18:38:00Z', type: 'sensor_error', field: 'debit', severity: 'critical', label: 'Kesalahan Sensor', context: { current: 0.02, interval_seconds: 0 } },
      { id: 'b', ts: '2026-08-24T18:40:00Z', type: 'net_up', severity: 'info', label: 'Internet Tersambung', context: { interval_seconds: 0 } },
      // Sub-minute values were delivery latency from older API versions ("Interval: 0 menit").
      { id: 'c', ts: '2026-08-24T18:41:00Z', type: 'send_fail', severity: 'info', label: 'Gagal Kirim ke KLHK', context: { interval_seconds: 2 } },
    ],
    eventTotal: 2,
    timezone: 'Asia/Jakarta',
  });
  assert.match(html, /Parameter: Debit/);
  assert.doesNotMatch(html, /Parameter: debit/);
  assert.match(html, /Nilai: 0,02/);
  assert.doesNotMatch(html, /Interval: 0/);
});


test('SiteStatusChips hides the native scrollbar and fades the overflowing edge', async () => {
  const source = await readFile(resolve(projectRoot, 'resources/js/Components/Dashboard/SiteStatusChips.vue'), 'utf8');
  assert.match(source, /\.chip-scroller\s*\{[^}]*scrollbar-width:\s*none/);
  assert.match(source, /\.chip-scroller::-webkit-scrollbar\s*\{[^}]*display:\s*none/);
  assert.match(source, /\.chip-scroller\s*\{[^}]*mask-image:/);
});
