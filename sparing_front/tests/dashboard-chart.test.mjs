import assert from 'node:assert/strict';
import test from 'node:test';
import { fileURLToPath } from 'node:url';
import { resolve } from 'node:path';
import { readFile } from 'node:fs/promises';
import { createRenderer, createSSRApp, h, nextTick, ssrContextKey } from 'vue';
import * as VueRuntime from 'vue';
import { renderToString } from '@vue/server-renderer';
import { parse, compileScript } from '@vue/compiler-sfc';
import * as dashboardTimeseries from '../resources/js/Utils/dashboardTimeseries.js';

process.env.BROWSERSLIST_IGNORE_OLD_DATA = 'true';
process.env.VITE_DEBUG = 'false';

const projectRoot = fileURLToPath(new URL('..', import.meta.url));

const virtualModules = {
  'vue3-apexcharts': '\0dashboard-test:apexchart',
  '@/Layouts/AppLayout.vue': '\0dashboard-test:layout',
  '@/Components/PageHeader.vue': '\0dashboard-test:page-header',
  '@/Components/SiteMap.vue': '\0dashboard-test:component',
  '@/Components/StatusBadge.vue': '\0dashboard-test:component',
  '@/Components/DataTable.vue': '\0dashboard-test:component',
  '@/Components/Sparkline.vue': '\0dashboard-test:component',
  '@/Composables/useApi': '\0dashboard-test:api',
  '@/Composables/useAuth': '\0dashboard-test:auth',
};

const dashboardStubs = {
  name: 'dashboard-test-stubs',
  enforce: 'pre',
  resolveId(source) {
    if (virtualModules[source]) return virtualModules[source];

    const normalized = source.replaceAll('\\', '/');
    for (const [request, virtualId] of Object.entries(virtualModules)) {
      if (!request.startsWith('@/')) continue;
      const resolvedSuffix = `/resources/js/${request.slice(2)}`;
      if (normalized.endsWith(resolvedSuffix) || normalized.endsWith(`${resolvedSuffix}.js`)) {
        return virtualId;
      }
    }

    return null;
  },
  load(id) {
    if (id === '\0dashboard-test:apexchart') {
      return `
        import { defineComponent, getCurrentInstance, h } from 'vue';

        export default defineComponent({
          name: 'ApexChartProbe',
          props: {
            type: String,
            height: [String, Number],
            options: Object,
            series: Array,
          },
          setup(props) {
            const instance = getCurrentInstance();
            return () => {
              const axes = Array.isArray(props.options?.yaxis)
                ? props.options.yaxis
                : (props.options?.yaxis ? [props.options.yaxis] : []);
              const tooltipArgs = [[0, 0], [0, 1], [1, 0]];
              const tooltips = typeof props.options?.tooltip?.custom === 'function'
                ? tooltipArgs.map(([seriesIndex, dataPointIndex]) => props.options.tooltip.custom({
                  series: (props.series ?? []).map((series) => series.data?.map((point) => point.y) ?? []),
                  seriesIndex,
                  dataPointIndex,
                  w: { config: { series: props.series ?? [] } },
                }))
                : [];
              const labelFormatter = props.options?.xaxis?.labels?.formatter;
              const xLabelSamples = typeof labelFormatter === 'function'
                ? [labelFormatter(undefined, Date.parse('2026-08-25T00:00:00Z'))]
                : [];
              const chartProbe = ['dashboard-ph', 'dashboard-tss', 'dashboard-debit'].includes(props.options?.chart?.id)
                ? encodeURIComponent(JSON.stringify({
                  key: instance.vnode.key == null ? '__missing__' : String(instance.vnode.key),
                  options: props.options,
                  series: props.series ?? [],
                  axes,
                  tooltip: tooltips[0] ?? '',
                  tooltips,
                  xLabelSamples,
                }))
                : undefined;
              return h('div', {
                'data-chart-key': instance.vnode.key == null ? '__missing__' : String(instance.vnode.key),
                'data-chart-type': props.type,
                'data-series-count': props.series?.length ?? 0,
                'data-axis-count': axes.length,
                'data-axis-title': axes[0]?.title?.text ?? '',
                'data-ph-probe': props.options?.chart?.id === 'dashboard-ph' ? chartProbe : undefined,
                'data-tss-probe': props.options?.chart?.id === 'dashboard-tss' ? chartProbe : undefined,
                'data-debit-probe': props.options?.chart?.id === 'dashboard-debit' ? chartProbe : undefined,
              });
            };
          },
        });
      `;
    }

    if (id === '\0dashboard-test:layout') {
      return `
        import { h } from 'vue';
        export default {
          name: 'AppLayoutStub',
          setup(_props, { slots }) {
            return () => h('main', slots.default?.());
          },
        };
      `;
    }

    if (id === '\0dashboard-test:page-header') {
      return `
        import { h } from 'vue';
        export default {
          name: 'PageHeaderStub',
          setup(_props, { slots }) {
            return () => h('header', [slots.default?.(), slots.actions?.()]);
          },
        };
      `;
    }

    if (id === '\0dashboard-test:component') {
      return `
        import { h } from 'vue';
        export default { name: 'ComponentStub', render: () => h('div') };
      `;
    }

    if (id === '\0dashboard-test:api') {
      return `
        export function useApi() {
          const emptyList = async () => [];
          return {
            getLatestData: async () => null,
            getData: emptyList,
            getDashboardTimeseries: async () => ({
              meta: { timezone: 'Asia/Jakarta', is_partial: false, partial_reasons: [] },
              series: {
                ph: { label: 'pH', unit: '', points: [] },
                tss: { label: 'TSS', unit: 'mg/L', points: [] },
                debit: { label: 'Debit', unit: 'L/min', points: [] },
              },
              statistics: {},
              thresholds: {},
              events: [],
              event_total: 0,
            }),
            getDevices: emptyList,
            getSites: emptyList,
            getSensorHealth: emptyList,
            getCompliance: async () => null,
            getCompleteness: async () => null,
            getAlertCount: async () => ({ count: 0 }),
            getAlerts: emptyList,
            getAlertRules: emptyList,
            getLoggerStatus: emptyList,
          };
        }
      `;
    }

    if (id === '\0dashboard-test:auth') {
      return `
        export function useAuth() {
          return { filterSitesByUser: (sites) => sites };
        }
      `;
    }

    return null;
  },
};

let vite;
let Dashboard;
let WaterQualityTrendChart;
let WaterQualityTrendChartClient;
let DebitTrendChart;
let DebitTrendChartClient;

test.before(async () => {
  const [{ default: vue }, { createServer }] = await Promise.all([
    import('@vitejs/plugin-vue'),
    import('vite'),
  ]);

  vite = await createServer({
    appType: 'custom',
    configFile: false,
    logLevel: 'silent',
    plugins: [dashboardStubs, vue()],
    resolve: {
      alias: {
        '@': resolve(projectRoot, 'resources/js'),
      },
    },
    root: projectRoot,
    ssr: {
      noExternal: ['vue3-apexcharts'],
    },
    server: {
      middlewareMode: true,
    },
  });

  ([{ default: Dashboard }, { default: WaterQualityTrendChart }, { default: DebitTrendChart }] = await Promise.all([
    vite.ssrLoadModule('/resources/js/Pages/Dashboard/Index.vue'),
    vite.ssrLoadModule('/resources/js/Components/Dashboard/WaterQualityTrendChart.vue'),
    vite.ssrLoadModule('/resources/js/Components/Dashboard/DebitTrendChart.vue'),
  ]));
  [WaterQualityTrendChartClient, DebitTrendChartClient] = await Promise.all([
    compileWaterClient(),
    compileDebitClient(),
  ]);
});

test.after(async () => {
  await vite?.close();
});

const TWO_SITES = [
  { uid: 'site-1', name: 'IPAL Utama', company_name: 'PT Tirta', timezone: 'Asia/Jakarta' },
  { uid: 'site-2', name: 'IPAL Cadangan', company_name: 'PT Tirta', timezone: 'Asia/Jakarta' },
];

async function renderDashboard({
  snapshot = null, state = 'ready', errorMessage = '', focusEvent = null,
  sites = null, sitesStatus = null, loggerStates = null, latestData = null,
  kpis = null, inspect = null,
} = {}) {
  const component = {
    ...Dashboard,
    setup(props, context) {
      const dashboardState = Dashboard.setup(props, context);
      const siteList = sites ?? [TWO_SITES[0]];

      dashboardState.sites.value = siteList;
      dashboardState.currentSite.value = siteList[0];
      dashboardState.selectedSiteUid.value = siteList[0].uid;
      dashboardState.latestData.value = latestData ?? {
        ts: '2026-08-25T00:05:00Z', ph: 7.2, tss: 19.5, debit: 0,
      };
      if (sitesStatus) dashboardState.sitesStatus.value = sitesStatus;
      if (loggerStates && dashboardState.loggerStates) dashboardState.loggerStates.value = loggerStates;

      // These bindings are introduced by the Dashboard integration. Guarding
      // them keeps RED a behavior assertion against the old page instead of a
      // setup exception caused by the intentionally missing feature.
      if (dashboardState.timeseriesSnapshot) dashboardState.timeseriesSnapshot.value = snapshot;
      if (dashboardState.timeseriesState) dashboardState.timeseriesState.value = state;
      if (dashboardState.timeseriesErrorMessage) dashboardState.timeseriesErrorMessage.value = errorMessage;
      if (focusEvent && dashboardState.focusMonitoringEvent) dashboardState.focusMonitoringEvent(focusEvent);
      for (const [name, value] of Object.entries(kpis ?? {})) dashboardState[name].value = value;
      inspect?.(dashboardState);

      return dashboardState;
    },
  };

  const app = createSSRApp(component);
  app.component('router-link', {
    name: 'RouterLinkStub',
    setup(_props, { slots }) {
      return () => h('a', slots.default?.());
    },
  });

  return renderToString(app);
}

function chartProbes(html) {
  return Array.from(html.matchAll(/<div\b([^>]*\bdata-chart-key="[^"]*"[^>]*)>/g), ([, rawAttributes]) => {
    const attributes = Object.fromEntries(
      Array.from(rawAttributes.matchAll(/([\w-]+)="([^"]*)"/g), ([, name, value]) => [name, value]),
    );
    return {
      key: attributes['data-chart-key'],
      type: attributes['data-chart-type'],
      seriesCount: Number(attributes['data-series-count']),
      axisCount: Number(attributes['data-axis-count']),
      axisTitle: attributes['data-axis-title'],
    };
  });
}

function waterTrend(probes) {
  return probes.find((probe) => probe.axisTitle === 'pH');
}

function debitTrend(probes) {
  return probes.find((probe) => probe.axisTitle === 'L/min');
}

function eventText(node) {
  return node.children?.map((child) => child.props?.text ?? eventText(child)).join('') ?? '';
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

async function renderWater(snapshot, props = {}) {
  return renderToString(createSSRApp({
    render: () => h(WaterQualityTrendChart, {
      snapshot,
      state: 'ready',
      stale: false,
      focusedEventId: null,
      reducedMotion: false,
      ...props,
    }),
  }));
}

async function renderDebit(snapshot, props = {}) {
  return renderToString(createSSRApp({
    render: () => h(DebitTrendChart, {
      snapshot,
      state: 'ready',
      stale: false,
      focusedEventId: null,
      reducedMotion: false,
      ...props,
    }),
  }));
}

async function mountWater(props = {}) {
  const root = makeNode('root');
  const emitted = [];
  const app = testRenderer.createApp({
    render: () => h(WaterQualityTrendChartClient, {
      snapshot: sampleSnapshot(), state: 'stale', stale: true, focusedEventId: null, reducedMotion: false,
      ...props,
      onRetry: () => emitted.push('retry'),
    }),
  });
  app.provide(ssrContextKey, { modules: new Set() });
  app.mount(root);
  await nextTick();
  return { root, emitted, unmount: () => app.unmount() };
}

function importBindings(spec) {
  return spec.split(',').map((entry) => {
    const [name, alias] = entry.trim().split(/\s+as\s+/);
    return alias ? `${name}: ${alias}` : name;
  }).join(', ');
}

async function compileWaterClient() {
  const source = await readFile(resolve(projectRoot, 'resources/js/Components/Dashboard/WaterQualityTrendChart.vue'), 'utf8');
  const { descriptor } = parse(source, { filename: 'WaterQualityTrendChart.vue' });
  let code = compileScript(descriptor, { id: 'water-quality-chart-test', inlineTemplate: true }).content;
  code = code.replace(/import \{([^}]+)\} from ['"]vue['"];?/g, (_match, bindings) => `const { ${importBindings(bindings)} } = VueRuntime;`);
  code = code.replace(/import ApexChart from ['"]vue3-apexcharts['"];?/, 'const ApexChart = ApexChartStub;');
  code = code.replace(/import ChartState from ['"]\.\/ChartState\.vue['"];?/, 'const ChartState = ChartStateStub;');
  code = code.replace(/import ChartSummary from ['"]\.\/ChartSummary\.vue['"];?/, 'const ChartSummary = ChartSummaryStub;');
  code = code.replace(/import \{([\s\S]*?)\} from ['"]@\/Utils\/dashboardTimeseries\.js['"];?/, (_match, bindings) => `const { ${importBindings(bindings)} } = dashboardTimeseries;`);
  code = code.replace('export default', 'return');
  const ChartStateStub = {
    props: ['state'],
    emits: ['retry'],
    setup(props, { emit, slots }) {
      return () => h('section', [
        props.state === 'stale' ? h('button', { type: 'button', onClick: () => emit('retry') }, 'Coba Lagi') : null,
        slots.default?.(),
      ]);
    },
  };
  const ChartSummaryStub = { setup() { return () => h('div'); } };
  const ApexChartStub = { setup() { return () => h('div'); } };
  return new Function('VueRuntime', 'dashboardTimeseries', 'ApexChartStub', 'ChartStateStub', 'ChartSummaryStub', code)(
    VueRuntime, dashboardTimeseries, ApexChartStub, ChartStateStub, ChartSummaryStub,
  );
}

async function compileDebitClient() {
  const source = await readFile(resolve(projectRoot, 'resources/js/Components/Dashboard/DebitTrendChart.vue'), 'utf8');
  const { descriptor } = parse(source, { filename: 'DebitTrendChart.vue' });
  let code = compileScript(descriptor, { id: 'debit-chart-test', inlineTemplate: true }).content;
  code = code.replace(/import \{([^}]+)\} from ['"]vue['"];?/g, (_match, bindings) => `const { ${importBindings(bindings)} } = VueRuntime;`);
  code = code.replace(/import ApexChart from ['"]vue3-apexcharts['"];?/, 'const ApexChart = ApexChartStub;');
  code = code.replace(/import ChartState from ['"]\.\/ChartState\.vue['"];?/, 'const ChartState = ChartStateStub;');
  code = code.replace(/import ChartSummary from ['"]\.\/ChartSummary\.vue['"];?/, 'const ChartSummary = ChartSummaryStub;');
  code = code.replace(/import \{([\s\S]*?)\} from ['"]@\/Utils\/dashboardTimeseries\.js['"];?/, (_match, bindings) => `const { ${importBindings(bindings)} } = dashboardTimeseries;`);
  code = code.replace('export default', 'return');
  const ChartStateStub = {
    props: ['state'], emits: ['retry'],
    setup(props, { emit, slots }) {
      return () => h('section', [
        props.state === 'stale' ? h('button', { type: 'button', onClick: () => emit('retry') }, 'Coba Lagi') : null,
        slots.default?.(),
      ]);
    },
  };
  const ChartSummaryStub = { setup() { return () => h('div'); } };
  const ApexChartStub = {
    props: ['options', 'series'],
    setup(props) { return () => h('apex-chart', { options: props.options, series: props.series }); },
  };
  return new Function('VueRuntime', 'dashboardTimeseries', 'ApexChartStub', 'ChartStateStub', 'ChartSummaryStub', code)(
    VueRuntime, dashboardTimeseries, ApexChartStub, ChartStateStub, ChartSummaryStub,
  );
}

async function mountDebit(props = {}) {
  const root = makeNode('root');
  const emitted = [];
  const app = testRenderer.createApp({
    render: () => h(DebitTrendChartClient, {
      snapshot: sampleDebitSnapshot(), state: 'ready', stale: false, focusedEventId: null, reducedMotion: false,
      ...props,
      onRetry: () => emitted.push('retry'),
    }),
  });
  app.provide(ssrContextKey, { modules: new Set() });
  app.mount(root);
  await nextTick();
  return { root, emitted, unmount: () => app.unmount() };
}

function chartProbe(html, name) {
  const match = html.match(new RegExp(`data-${name}-probe="([^"]+)"`));
  assert.ok(match, `Expected the compiled ${name} ApexChart probe`);
  return JSON.parse(decodeURIComponent(match[1]));
}

// pH and TSS are separate single-axis charts.
function waterProbes(html) {
  return { ph: chartProbe(html, 'ph'), tss: chartProbe(html, 'tss') };
}

function debitProbe(html) {
  const match = html.match(/data-debit-probe="([^"]+)"/);
  assert.ok(match, 'Expected the compiled debit ApexChart probe');
  return JSON.parse(decodeURIComponent(match[1]));
}

function sampleSnapshot(overrides = {}) {
  const base = {
    meta: {
      timezone: 'Asia/Jakarta', date_from: '2026-08-24T23:00:00Z', date_to: '2026-08-25T00:10:00Z',
      generated_at: '2026-08-25T00:11:00Z', resolution_seconds: 300, is_partial: false,
    },
    series: {
      ph: { label: 'pH', unit: '', points: [
        { ts: '2026-08-24T23:55:00Z', value: 7.1, quality: 'Baik', bucket_min: 7, bucket_max: 7.2, count: 3 },
        { ts: '2026-08-25T00:00:00Z', value: null },
        { ts: '2026-08-25T00:05:00Z', value: 7.2, quality: 'Baik' },
      ] },
      tss: { label: 'TSS', unit: 'mg/L', precision: 1, points: [
        { ts: '2026-08-24T23:55:00Z', value: 15.5, quality: 'Valid', bucket_min: 14, bucket_max: 16, count: 3 },
        { ts: '2026-08-25T00:00:00Z', value: null },
        { ts: '2026-08-25T00:05:00Z', value: 19.5, quality: 'Valid' },
      ] },
    },
    statistics: {
      ph: { current: 7.2, current_ts: '2026-08-25T00:05:00Z', avg: 7.15, min: 7.1, max: 7.2, status: 'normal', status_label: 'Normal', availability_pct: 67 },
      tss: { current: 19.5, current_ts: '2026-08-25T00:05:00Z', avg: 17.5, min: 15.5, max: 19.5, status: 'warning', status_label: 'Peringatan', availability_pct: 67 },
    },
    thresholds: {
      ph: { lower: { value: 6, source: 'Baku mutu' }, upper: { value: 9, source: 'Baku mutu' } },
      tss: { reference: { value: 30, source: 'Baku mutu' } },
    },
    events: [
      { id: 'evt-ph', ts: '2026-08-24T23:55:00Z', field: 'ph', type: 'threshold_warning', label: 'pH perlu diperiksa', context: { current: 7.1, baseline: 7, delta: 0.1, percent: 1.4, interval_seconds: 300, tss: { current: 15.5 }, debit: { value: 0 } } },
      { id: 'evt-tss', ts: '2026-08-25T00:05:00Z', field: 'tss', type: 'rapid_change', label: 'TSS naik', context: { current: 19.5, baseline: 10, delta: 9.5, percent: 95, interval_seconds: 300, tss: { current: 19.5 }, debit: { value: 0 } } },
      { id: 'evt-debit', ts: '2026-08-25T00:05:00Z', field: 'debit', type: 'flow_drop', label: 'Debit turun', context: { debit: { value: 0 } } },
      { id: 'evt-gap', ts: '2026-08-25T00:00:00Z', type: 'data_gap', label: 'Data terputus' },
      { id: 'evt-operation', ts: '2026-08-25T00:00:00Z', type: 'op_status', label: 'Pompa diperiksa', context: { debit: { value: 0 } } },
    ],
  };
  return { ...base, ...overrides, meta: { ...base.meta, ...overrides.meta }, series: { ...base.series, ...overrides.series }, statistics: { ...base.statistics, ...overrides.statistics } };
}

function sampleDebitSnapshot(overrides = {}) {
  const base = sampleSnapshot({
    series: {
      debit: { label: 'Debit', unit: 'L/min', precision: 2, points: [
        { ts: '2026-08-24T23:55:00Z', value: 2.5, quality: 'Baik', bucket_min: 2.2, bucket_max: 2.8, count: 3 },
        { ts: '2026-08-25T00:00:00Z', value: 0, quality: 'Baik' },
        { ts: '2026-08-25T00:05:00Z', value: 120, quality: 'Baik' },
      ] },
    },
    statistics: {
      debit: {
        current: 0, current_ts: '2026-08-25T00:00:00Z', avg: 2.1, min: 0, max: 120,
        status: 'no_flow', status_label: 'No Flow', status_reason: 'Pompa berhenti', status_severity: 'warning',
        flow_state: 'no_flow', current_quality: 'Baik', availability_pct: 100,
      },
    },
    thresholds: { debit: { warning_max: 80, danger_max: 100 } },
    events: [
      { id: 'evt-flow', ts: '2026-08-25T00:00:00Z', field: 'debit', type: 'no_flow', label: 'Tidak ada aliran', context: { debit: { value: 0 } } },
      { id: 'evt-low-tss', ts: '2026-08-25T00:05:00Z', field: 'debit', type: 'low_flow_tss_check', label: 'Periksa TSS', context: { debit: { value: 120 }, tss: { current: 9 } } },
      { id: 'evt-gap', ts: '2026-08-25T00:02:00Z', type: 'data_gap', label: 'Data terputus' },
    ],
  });
  return {
    ...base,
    ...overrides,
    meta: { ...base.meta, ...overrides.meta },
    series: { ...base.series, ...overrides.series },
    statistics: { ...base.statistics, ...overrides.statistics },
    thresholds: { ...base.thresholds, ...overrides.thresholds },
    events: overrides.events ?? base.events,
  };
}

test('Dashboard renders one coherent monitoring surface with accessible site and period controls', async () => {
  const html = await renderDashboard({
    snapshot: sampleDebitSnapshot({ event_total: 6 }),
    state: 'ready',
    sites: TWO_SITES,
  });

  assert.match(html, /aria-label="Pilih lokasi pemantauan"/);
  assert.match(html, /aria-label="Filter periode pemantauan"/);
  assert.match(html, /Tren Kualitas Air Limbah/);
  assert.match(html, /Debit Air Limbah/);
  assert.match(html, /aria-label="Ringkasan pH"/);
  assert.match(html, /aria-label="Ringkasan TSS"/);
  assert.match(html, /aria-label="Ringkasan Debit"/);
  assert.match(html, /Ketersediaan 67%/);
  assert.match(html, /Ketersediaan 100%/);
  assert.match(html, /Event pemantauan/);
  assert.match(html, /Menampilkan 3 dari 6 event/);
  assert.match(html, /Tidak ada aliran/);
  assert.doesNotMatch(html, /Tren Parameter Air Limbah|Debit &amp; Temperatur/);
});

test('Dashboard focuses on one site: status chips, site logger chip, no fleet table, map, or duplicate cards', async () => {
  const recent = new Date(Date.now() - 10 * 60 * 1000).toISOString();
  const html = await renderDashboard({
    snapshot: sampleDebitSnapshot(),
    sites: TWO_SITES,
    sitesStatus: [
      { site: TWO_SITES[0], latest: { ts: recent, ph: 7.2, tss: 19.5 } },
      { site: TWO_SITES[1], latest: { ts: recent, ph: 7.0 } },
    ],
    loggerStates: { 'site-1': 'alive', 'site-2': 'down' },
  });
  assert.match(html, /role="group" aria-label="Pilih lokasi pemantauan"/);
  assert.match(html, /<button[^>]*aria-pressed="true"[^>]*>(?:(?!<\/button>)[\s\S])*IPAL Utama/);
  assert.match(html, /IPAL Cadangan(?:(?!<\/button>)[\s\S])*mati/);
  assert.match(html, /Logger hidup/);
  assert.match(html, /Kelengkapan Data Hari Ini/);
  assert.doesNotMatch(html, /<select[^>]*Pilih lokasi pemantauan/);
  assert.doesNotMatch(html, /Status Stasiun/);
  assert.doesNotMatch(html, /Peta Lokasi/);
  assert.doesNotMatch(html, /\d+ logger mati/);
  assert.doesNotMatch(html, /Parameter lain/i);

  const withCod = await renderDashboard({ snapshot: sampleDebitSnapshot(), latestData: { ts: recent, ph: 7.2, cod: 101.4 } });
  // Extra parameters live inside the water-quality card, next to the pH/TSS summaries.
  const extraAt = withCod.indexOf('Parameter lain');
  assert.ok(extraAt > withCod.indexOf('aria-label="Ringkasan TSS"'), 'extra parameters follow the pH/TSS summaries');
  assert.ok(extraAt < withCod.indexOf('aria-label="Grafik tren pH dan TSS"'), 'extra parameters precede the chart');
  assert.match(withCod, /COD/);
});

test('Dashboard exposes partial monitoring details and initial error retry without hiding other panels', async () => {
  const partialHtml = await renderDashboard({
    snapshot: sampleDebitSnapshot({
      meta: { is_partial: true, partial_reasons: ['missing_intervals'] },
    }),
    state: 'partial',
  });
  assert.match(partialHtml, /Data tidak lengkap/);
  assert.match(partialHtml, /Ada interval data yang hilang/);
  assert.match(partialHtml, /Status Perangkat Sensor/);

  const errorHtml = await renderDashboard({
    snapshot: null,
    state: 'error',
    errorMessage: 'Koneksi pemantauan terputus.',
  });
  assert.match(errorHtml, /Data gagal dimuat/);
  assert.match(errorHtml, /Koneksi pemantauan terputus\./);
  assert.match(errorHtml, /Coba Lagi/);
  assert.match(errorHtml, /Status Perangkat Sensor/);
});

test('Dashboard preserves numeric event IDs when synchronizing event focus', async () => {
  const numericEvent = {
    id: 42,
    ts: '2026-08-25T00:00:00Z',
    field: 'debit',
    type: 'no_flow',
    label: 'Aliran numerik',
    context: { debit: { value: 0 } },
  };
  const html = await renderDashboard({
    snapshot: sampleDebitSnapshot({ events: [numericEvent], event_total: 1 }),
    focusEvent: numericEvent,
  });
  const focused = debitProbe(html).options.annotations.points.find((annotation) => annotation.marker?.size === 9);
  assert.equal(focused?.x, Date.parse(numericEvent.ts));
});

test('chart event points carry no text labels and are coloured by severity', async () => {
  const events = [
    { id: 'ph-crit', ts: '2026-08-24T23:55:00Z', field: 'ph', type: 'sensor_error', severity: 'critical', label: 'Kesalahan Sensor', context: { current: 7.1 } },
    { id: 'tss-warn', ts: '2026-08-25T00:05:00Z', field: 'tss', type: 'rapid_change', severity: 'warning', label: 'Kesalahan Sensor', context: { current: 19.5 } },
  ];
  const html = await renderWater(sampleSnapshot({ events }));
  const { ph, tss } = waterProbes(html);
  const phPoints = ph.options.annotations.points.filter((point) => point.id === 'ph-crit');
  const tssPoints = tss.options.annotations.points.filter((point) => point.id === 'tss-warn');
  assert.equal(phPoints.length, 1);
  assert.equal(tssPoints.length, 1);
  assert.ok([...phPoints, ...tssPoints].every((point) => !point.label?.text));
  assert.equal(phPoints[0].marker.fillColor, '#B03030');
  assert.equal(tssPoints[0].marker.fillColor, '#9A6B00');
  // The markers are explained in a legend instead of unlabeled dots.
  const legend = html.match(/aria-label="Keterangan penanda peristiwa"[\s\S]*?<\/div>/)?.[0] ?? '';
  assert.match(legend, /Peristiwa kritis/);
  assert.match(legend, /Peristiwa peringatan/);

  const debitEvents = [{ id: 'debit-crit', ts: '2026-08-25T00:00:00Z', field: 'debit', type: 'flow_drop', severity: 'critical', label: 'Kesalahan Sensor', context: { debit: { value: 0 } } }];
  const debit = debitProbe(await renderDebit(sampleDebitSnapshot({ events: debitEvents })));
  const debitPoints = debit.options.annotations.points.filter((point) => point.id === 'debit-crit' || String(point.id).startsWith('outlier-'));
  assert.ok(debitPoints.some((point) => point.id === 'debit-crit'));
  assert.ok(debitPoints.every((point) => !point.label?.text));
  assert.equal(debitPoints.find((point) => point.id === 'debit-crit').marker.fillColor, '#B03030');
});

test('pH/TSS threshold lines carry no inline labels; a legend below the charts explains them', async () => {
  const thresholds = {
    ph: { warning_min: 6.5, warning_max: 8.5, danger_min: 6, danger_max: 9, source: 'site_alert_rule', regulation: 'Permen LHK 5/2014' },
    tss: { warning_max: 150, danger_max: 200, source: 'site_alert_rule', regulation: 'Permen LHK 5/2014' },
  };
  const html = await renderWater(sampleSnapshot({ thresholds }));
  const { ph, tss } = waterProbes(html);
  assert.equal(ph.options.annotations.yaxis.length, 4);
  assert.equal(tss.options.annotations.yaxis.length, 2);
  assert.ok([...ph.options.annotations.yaxis, ...tss.options.annotations.yaxis].every((annotation) => !annotation.label?.text));
  const legend = html.match(/aria-label="Keterangan garis batas"[\s\S]*?<\/div>/)?.[0] ?? '';
  assert.match(legend, /Peringatan/);
  assert.match(legend, /Bahaya/);
  assert.match(legend, /Permen LHK 5\/2014/);
  assert.equal(legend.match(/Peringatan/g).length, 1, 'one legend entry per threshold kind');
});

test('global event lines on every chart carry no vertical text labels', async () => {
  const { ph, tss } = waterProbes(await renderWater(sampleSnapshot()));
  for (const probe of [ph, tss]) {
    assert.ok(probe.options.annotations.xaxis.length > 0);
    assert.ok(probe.options.annotations.xaxis.every((annotation) => !annotation.label?.text));
  }
  const debit = debitProbe(await renderDebit(sampleDebitSnapshot()));
  assert.ok(debit.options.annotations.xaxis.length > 0);
  assert.ok(debit.options.annotations.xaxis.every((annotation) => !annotation.label?.text));
});

test('WaterQualityTrendChart places the extra slot between the summaries and the chart', async () => {
  const html = await renderToString(createSSRApp({
    render: () => h(WaterQualityTrendChart, {
      snapshot: sampleSnapshot(), state: 'ready', stale: false, focusedEventId: null, reducedMotion: false,
    }, { extra: () => h('div', { 'data-test': 'extra' }, 'COD 113') }),
  }));
  const extra = html.indexOf('data-test="extra"');
  assert.ok(extra > html.indexOf('aria-label="Ringkasan TSS"'));
  assert.ok(extra < html.indexOf('aria-label="Grafik tren pH dan TSS"'));
});

test('WaterQualityTrendChart draws pH and TSS as separate single-axis line charts across data shapes', async () => {
  const shapes = [
    sampleSnapshot({ series: { ph: { points: [] }, tss: { points: [] } } }),
    sampleSnapshot({ series: { ph: { points: [{ ts: '2026-08-25T00:05:00Z', value: 7.2 }] }, tss: { points: [] } } }),
    sampleSnapshot({ series: { ph: { points: [] }, tss: { points: [{ ts: '2026-08-25T00:05:00Z', value: 19.5 }] } } }),
    sampleSnapshot(),
  ];

  for (const snapshot of shapes) {
    const html = await renderWater(snapshot);
    const { ph, tss } = waterProbes(html);
    assert.equal(ph.key, 'water-quality:ph:v2');
    assert.equal(tss.key, 'water-quality:tss:v2');
    assert.deepEqual(ph.series.map((series) => series.name), ['pH']);
    assert.deepEqual(tss.series.map((series) => series.name), ['TSS']);
    for (const probe of [ph, tss]) {
      assert.equal(probe.axes.length, 1);
      // Charts must NOT share an ApexCharts group: updateOptions() on one grouped
      // chart is applied to every chart in the group, so Debit's single L/min axis
      // overwrote the water-quality axes in production.
      assert.equal(probe.options.chart.group, undefined);
      assert.equal(probe.options.yaxis.some((axis) => axis.logarithmic === true), false);
      // Evenly spaced ticks between step-aligned bounds land on round local times.
      const { min, max, tickAmount } = probe.options.xaxis;
      if (snapshot.meta.date_from) {
        const step = (max - min) / tickAmount;
        assert.ok(Number.isInteger(tickAmount) && step % (5 * 60 * 1000) === 0, 'round tick step');
        assert.equal((min + 7 * 3600 * 1000) % step, 0, 'first tick on a round WIB time');
      }
      assert.ok(Number.isInteger(probe.axes[0].tickAmount));
    }
    assert.equal(ph.options.chart.id, 'dashboard-ph');
    assert.equal(tss.options.chart.id, 'dashboard-tss');
    assert.equal(ph.axes[0].seriesName, 'pH');
    assert.equal(ph.axes[0].title.text, 'pH');
    assert.ok(ph.axes[0].min >= 0 && ph.axes[0].max <= 14);
    assert.ok(ph.axes[0].min < 6 && ph.axes[0].max > 9, 'pH limits stay visible');
    assert.equal(tss.axes[0].seriesName, 'TSS');
    assert.equal(tss.axes[0].min, 0);
    assert.equal(tss.axes[0].title.text, 'TSS (mg/L)');
    assert.equal(tss.axes[0].opposite, undefined);
    assert.match(html, /data-chart-type="line"/);
    assert.doesNotMatch(html, /data-chart-type="area"/);
  }
});

test('WaterQualityTrendChart renders measurement-time live copy, response annotations, null gaps, and focused events', async () => {
  const snapshot = sampleSnapshot();
  const html = await renderWater(snapshot, { focusedEventId: 'evt-tss' });
  const { ph, tss } = waterProbes(html);
  assert.match(html, /Tren Kualitas Air Limbah/);
  assert.match(html, /25 Agu 2026 • Real-time • Update terakhir 07:05/);
  assert.deepEqual(ph.series[0].data.map((point) => point.y), [7.1, null, 7.2]);
  assert.deepEqual(tss.series[0].data.map((point) => point.y), [15.5, null, 19.5]);
  assert.equal(ph.options.markers.size, 0);
  assert.equal(tss.options.markers.size, 0);
  assert.equal(tss.axes[0].max, 40);
  assert.equal(tss.axes[0].tickAmount, 4);
  assert.equal(ph.options.annotations.yaxis.length, 2);
  assert.equal(tss.options.annotations.yaxis.length, 1);
  assert.ok([...ph.options.annotations.yaxis, ...tss.options.annotations.yaxis].every((annotation) => annotation.yAxisIndex === 0));
  for (const probe of [ph, tss]) {
    for (const id of ['evt-debit', 'evt-gap', 'evt-operation']) {
      assert.equal(probe.options.annotations.points.some((point) => point.id === id), false);
    }
  }
  assert.deepEqual(ph.options.annotations.points.filter((point) => point.id === 'evt-ph').map((point) => [point.seriesIndex, point.yAxisIndex]), [[0, 0]]);
  assert.equal(ph.options.annotations.points.some((point) => point.id === 'evt-tss'), false);
  assert.deepEqual(tss.options.annotations.points.filter((point) => point.id === 'evt-tss').map((point) => [point.seriesIndex, point.yAxisIndex]), [[0, 0]]);
  assert.deepEqual(ph.options.annotations.points.filter((point) => point.id.startsWith('current-')).map((point) => point.id), ['current-ph']);
  assert.deepEqual(tss.options.annotations.points.filter((point) => point.id.startsWith('current-')).map((point) => point.id), ['current-tss']);
  const gap = ph.options.annotations.xaxis.find((annotation) => annotation.id === 'evt-gap');
  assert.ok(gap, 'Expected an x-axis gap annotation without a fabricated y coordinate');
  assert.equal(gap.y, undefined);
  assert.equal(ph.options.annotations.xaxis.find((annotation) => annotation.id === 'evt-operation').y, undefined);
  const focusedGap = waterProbes(await renderWater(snapshot, { focusedEventId: 'evt-gap' }))
    .tss.options.annotations.xaxis.find((annotation) => annotation.id === 'evt-gap');
  assert.equal(focusedGap.borderColor, '#0f766e');
  assert.ok([...ph.options.annotations.points, ...tss.options.annotations.points]
    .filter((point) => point.id.startsWith('current-')).every((point) => point.label === undefined));
  assert.equal(tss.options.annotations.points.find((point) => point.id === 'evt-tss').marker.size, 9);
  assert.match(ph.tooltip, /25 Agu 2026 • 06:55/);
  assert.match(ph.tooltip, /pH:<\/strong> 7,10/);
  assert.match(ph.tooltip, /Resolusi: 5 menit/);
  assert.match(ph.tooltip, /Minimum: 7,00/);
  assert.match(ph.tooltip, /Kualitas: Baik/);
  assert.match(tss.tooltip, /TSS:<\/strong> 15,5 mg\/L/);
  assert.doesNotMatch(ph.tooltip, /TSS:<\/strong>/, 'each chart explains its own parameter');
});

test('WaterQualityTrendChart formats x-axis labels in the response timezone', async () => {
  const { ph, tss } = waterProbes(await renderWater(sampleSnapshot({
    meta: { timezone: 'Pacific/Auckland' },
  })));

  assert.deepEqual(ph.xLabelSamples, ['12:00']);
  assert.deepEqual(tss.xLabelSamples, ['12:00']);
});

test('WaterQualityTrendChart uses truthful historical copy, escaped missing-value tooltip, responsive options, and reduced motion', async () => {
  const snapshot = sampleSnapshot({
    meta: { date_from: '2026-08-23T00:00:00Z', date_to: '2026-08-24T00:00:00Z', generated_at: '2026-08-25T00:11:00Z', resolution_seconds: 3600 },
    series: { ph: { points: [{ ts: '2026-08-24T00:00:00Z', value: null, quality: '<img src=x>' }] }, tss: { points: [{ ts: '2026-08-24T00:00:00Z', value: null }] } },
    statistics: { ph: { current: null, current_ts: null, status: 'no_data', status_label: 'Tidak Ada Data', availability_pct: 0 }, tss: { current: null, current_ts: null, status: 'no_data', status_label: 'Tidak Ada Data', availability_pct: 0 } },
  });
  const html = await renderWater(snapshot, { reducedMotion: true });
  const { ph, tss } = waterProbes(html);
  assert.doesNotMatch(html, /Real-time/);
  assert.match(html, /Resolusi 1 jam/);
  assert.match(ph.tooltip, /Data Tidak Tersedia/);
  assert.match(ph.tooltip, /&lt;img src=x&gt;/);
  assert.doesNotMatch(ph.tooltip, /<img src=x>/);
  assert.match(tss.tooltip, /Kualitas: Tidak Tersedia/);
  for (const probe of [ph, tss]) {
    assert.equal(probe.options.chart.animations.enabled, false);
    assert.equal(Array.isArray(probe.options.responsive), true);
  }
  assert.match(html, /aria-label="Grafik tren pH dan TSS"/);
  assert.match(html, /Ringkasan aksesibilitas/);
  assert.match(html, /Tidak Ada Data/);
});

test('WaterQualityTrendChart tooltips read the hovered point of their own chart and use the response TSS unit', async () => {
  const snapshot = sampleSnapshot({
    series: {
      ph: { points: [
        { ts: '2026-08-24T23:55:00Z', value: 7.1 },
        { ts: '2026-08-25T00:05:00Z', value: 7.3 },
      ] },
      tss: { unit: 'g/L', precision: 1, points: [
        { ts: '2026-08-25T00:05:00Z', value: 20.4, quality: 'Valid' },
      ] },
    },
  });
  const { ph, tss } = waterProbes(await renderWater(snapshot));
  assert.match(ph.tooltips[1], /pH:<\/strong> 7,30/);
  assert.doesNotMatch(ph.tooltips[1], /15[.,]5/);
  assert.match(tss.tooltips[0], /TSS:<\/strong> 20,4 g\/L/);
  assert.equal(tss.axes[0].title.text, 'TSS (g/L)');
});

test('WaterQualityTrendChart renders exact metadata, matching event context, and truthful fallback subtitles', async () => {
  const liveWithoutMeasurement = await renderWater(sampleSnapshot({
    statistics: { ph: { current: null, current_ts: null }, tss: { current: null, current_ts: null } },
  }));
  assert.match(liveWithoutMeasurement, /Real-time • Waktu pembacaan belum tersedia/);

  const historical = await renderWater(sampleSnapshot({
    meta: { date_from: '2026-08-23T00:00:00Z', date_to: '2026-08-24T00:00:00Z', generated_at: '2026-08-25T00:11:00Z', resolution_seconds: 90 },
  }));
  assert.match(historical, /Periode 23 Agu 2026 – 24 Agu 2026 • Resolusi 90 detik/);

  const { ph } = waterProbes(await renderWater(sampleSnapshot()));
  assert.match(ph.tooltip, /Event: pH perlu diperiksa/);
  assert.match(ph.tooltip, /Nilai saat ini: 7,1/);
  assert.match(ph.tooltip, /Baseline: 7/);
  assert.match(ph.tooltip, /Perubahan: 0,1/);
  assert.match(ph.tooltip, /Persentase: 1,4%/);
  assert.match(ph.tooltip, /Interval: 5 menit/);
  assert.match(ph.tooltip, /TSS event: 15,5/);
  assert.match(ph.tooltip, /Debit event: 0/);
  assert.match(ph.tooltip, /Jumlah bucket: 3/);
});

test('WaterQualityTrendChart forwards retry from its composed stale ChartState', async () => {
  const view = await mountWater();
  const retry = allNodes(view.root, (node) => node.type === 'button' && eventText(node).includes('Coba Lagi'))[0];
  assert.ok(retry, 'Expected the stale ChartState retry action');
  retry.props.onClick();
  assert.deepEqual(view.emitted, ['retry']);
  view.unmount();
});

test('DebitTrendChart keeps one Debit series and one linear axis across empty, zero, null, ordinary, and spike data', async () => {
  const shapes = [
    sampleDebitSnapshot({ series: { debit: { unit: 'm³/jam', points: [] } } }),
    sampleDebitSnapshot({ series: { debit: { unit: 'm³/jam', points: [{ ts: '2026-08-25T00:00:00Z', value: 0 }] } } }),
    sampleDebitSnapshot({ series: { debit: { unit: 'm³/jam', points: [{ ts: '2026-08-25T00:00:00Z', value: null }] } } }),
    sampleDebitSnapshot({ series: { debit: { unit: 'm³/jam', points: [{ ts: '2026-08-25T00:00:00Z', value: 2.5 }, { ts: '2026-08-25T00:05:00Z', value: 500 }] } } }),
  ];
  for (const snapshot of shapes) {
    const probe = debitProbe(await renderDebit(snapshot));
    assert.equal(probe.key, 'debit:flow:v1');
    assert.deepEqual(probe.series.map((series) => series.name), ['Debit']);
    assert.equal(probe.axes.length, 1);
    assert.equal(probe.axes[0].seriesName, 'Debit');
    assert.equal(probe.axes[0].min, 0);
    assert.equal(probe.options.chart.id, 'dashboard-debit');
    assert.equal(probe.options.chart.group, undefined); // see WaterQualityTrendChart axis test
    assert.equal(probe.options.yaxis.some((axis) => Object.hasOwn(axis, 'logarithmic')), false);
    assert.doesNotMatch(JSON.stringify(probe), /Temperature/);
  }
});

test('DebitTrendChart renders response-based flow summary, live and historical timestamps, escaped tooltip, events, and accessible retry', async () => {
  const snapshot = sampleDebitSnapshot({
    series: { debit: { unit: 'm³/jam', points: [{ ts: '2026-08-24T23:55:00Z', value: 0, quality: '<img src=x>', bucket_min: 0, bucket_max: 0, count: 3 }] } },
    statistics: { debit: { current: 0, current_ts: '2026-08-24T23:55:00Z', status: 'no_flow', status_label: 'No Flow', status_reason: 'Pompa berhenti', status_severity: 'warning', flow_state: 'no_flow', current_quality: 'Baik', availability_pct: 100 } },
  });
  const html = await renderDebit(snapshot, { focusedEventId: 'evt-flow', state: 'stale', stale: true, reducedMotion: true });
  const probe = debitProbe(html);
  assert.match(html, /Debit Air Limbah/);
  assert.match(html, /Monitoring laju aliran real-time/);
  assert.match(html, /25 Agu 2026 • Update terakhir 06:55/);
  assert.match(html, /0,00 m³\/jam/);
  assert.match(html, /No Flow/);
  assert.match(html, /Aliran terhenti/);
  assert.match(html, /Grafik tren debit air limbah/);
  assert.match(html, /Coba Lagi/);
  assert.match(probe.tooltip, /Data Tidak Tersedia|0,00 m³\/jam/);
  assert.match(probe.tooltip, /&lt;img src=x&gt;/);
  assert.match(probe.tooltip, /Resolusi: 5 menit/);
  assert.match(probe.tooltip, /Status: No Flow/);
  assert.match(probe.tooltip, /Kualitas: &lt;img src=x&gt;/);
  assert.deepEqual(probe.options.annotations.points.filter((point) => point.id === 'evt-flow').map((point) => [point.seriesIndex, point.yAxisIndex, point.y]), [[0, 0, 0]]);
  assert.deepEqual(probe.options.annotations.points.filter((point) => point.id === 'evt-low-tss').map((point) => [point.seriesIndex, point.yAxisIndex, point.y]), [[0, 0, 120]]);
  assert.equal(probe.options.annotations.points.find((point) => point.id === 'evt-flow').marker.size, 9);
  assert.equal(probe.options.annotations.xaxis.find((point) => point.id === 'evt-gap').y, undefined);
  assert.deepEqual(probe.options.annotations.points.filter((point) => point.id === 'current-debit').map((point) => [point.seriesIndex, point.yAxisIndex, point.y]), [[0, 0, 0]]);
  assert.equal(probe.options.chart.animations.enabled, false);

  const historical = debitProbe(await renderDebit(sampleDebitSnapshot({
    meta: { date_from: '2026-08-23T00:00:00Z', date_to: '2026-08-24T00:00:00Z', generated_at: '2026-08-25T00:11:00Z', resolution_seconds: 3600 },
  }))).options;
  assert.equal(historical.chart.group, undefined);
  assert.doesNotMatch(await renderDebit(sampleDebitSnapshot({ meta: { date_from: '2026-08-23T00:00:00Z', date_to: '2026-08-24T00:00:00Z', generated_at: '2026-08-25T00:11:00Z', resolution_seconds: 3600 } })), /real-time/);
});

test('DebitTrendChart formats x-axis labels in the response timezone', async () => {
  const probe = debitProbe(await renderDebit(sampleDebitSnapshot({
    meta: { timezone: 'Pacific/Auckland' },
  })));

  assert.deepEqual(probe.xLabelSamples, ['12:00']);
});

test('DebitTrendChart toggles only the visible scale and truthfully omits generic alert thresholds as flow references', async () => {
  const steady = Array.from({ length: 20 }, (_, index) => ({ ts: `2026-08-24T23:${String(30 + index).padStart(2, '0')}:00Z`, value: 2 + (index % 3) * 0.2 }));
  const spiky = sampleDebitSnapshot({ series: { debit: { unit: 'L/min', points: [...steady, { ts: '2026-08-25T00:05:00Z', value: 120 }] } } });
  const view = await mountDebit({ snapshot: spiky });
  const chart = allNodes(view.root, (node) => node.type === 'apex-chart')[0];
  const beforeSeries = chart.props.series;
  const beforeMax = chart.props.options.yaxis[0].max;
  assert.ok(chart.props.options.annotations.yaxis.every((annotation) => !/Aliran (rendah|terhenti)/i.test(annotation.label?.text ?? '')));
  assert.ok(chart.props.options.annotations.points.some((point) => point.id.startsWith('outlier-')));
  const normal = allNodes(view.root, (node) => node.type === 'button' && eventText(node).includes('Skala normal'))[0];
  const full = allNodes(view.root, (node) => node.type === 'button' && eventText(node).includes('Skala penuh'))[0];
  assert.equal(normal.props['aria-pressed'], 'true');
  assert.equal(full.props['aria-pressed'], 'false');
  full.props.onClick();
  await nextTick();
  assert.equal(full.props['aria-pressed'], 'true');
  assert.equal(chart.props.options.yaxis[0].max >= 120, true);
  assert.equal(chart.props.options.annotations.points.some((point) => point.id.startsWith('outlier-')), false);
  assert.deepEqual(chart.props.series, beforeSeries);
  assert.ok(chart.props.options.yaxis[0].max >= beforeMax);
  view.unmount();

  const normalHtml = await renderDebit(spiky);
  assert.match(normalHtml, /1 nilai di luar skala normal/);
  const operational = debitProbe(await renderDebit(sampleDebitSnapshot({
    thresholds: { debit: { operational_flow: { no_flow: 0.1, low_flow: 1 } } },
  })));
  assert.deepEqual(operational.options.annotations.yaxis.map((annotation) => annotation.label.text), ['Batas tanpa aliran', 'Batas aliran rendah']);
});

test('DebitTrendChart counts only values clipped at the visible normal-scale ceiling', async () => {
  const point = (value) => ({ ts: `2026-08-25T00:${String(value).padStart(2, '0')}:00Z`, value });
  const headroomOnly = sampleDebitSnapshot({
    series: { debit: { unit: 'L/min', points: Array.from({ length: 20 }, (_, value) => point(value)) } },
  });
  const headroomHtml = await renderDebit(headroomOnly);
  const headroomProbe = debitProbe(headroomHtml);
  assert.equal(headroomProbe.options.annotations.points.filter((annotation) => annotation.id.startsWith('outlier-')).length, 0);
  assert.doesNotMatch(headroomHtml, /nilai di luar skala normal/);

  const clipped = sampleDebitSnapshot({
    series: { debit: { unit: 'L/min', points: [...Array.from({ length: 20 }, (_, value) => point(value)), { ts: '2026-08-25T01:00:00Z', value: 200 }] } },
  });
  const clippedHtml = await renderDebit(clipped);
  const clippedProbe = debitProbe(clippedHtml);
  assert.equal(clippedProbe.options.annotations.points.filter((annotation) => annotation.id.startsWith('outlier-')).length, 1);
  assert.match(clippedHtml, /1 nilai di luar skala normal/);
});

test('DebitTrendChart keeps global data, logger, operation, and fieldless sensor events on the x axis', async () => {
  const events = [
    { id: 'gap-with-field', ts: '2026-08-25T00:00:00Z', field: 'debit', type: 'data_gap', label: 'Gap', context: { current: 7 } },
    { id: 'logger', ts: '2026-08-25T00:01:00Z', type: 'logger_offline', label: 'Logger mati', context: { current: 7 } },
    { id: 'operation', ts: '2026-08-25T00:02:00Z', type: 'op_status', label: 'Pompa dicek', context: { current: 7 } },
    { id: 'sensor-fail', ts: '2026-08-25T00:03:00Z', type: 'sensor_fail', label: 'Sensor gagal', context: { current: 7 } },
    { id: 'sensor-recover', ts: '2026-08-25T00:04:00Z', type: 'sensor_recover', label: 'Sensor pulih', context: { current: 7 } },
  ];
  const probe = debitProbe(await renderDebit(sampleDebitSnapshot({ events })));
  assert.deepEqual(probe.options.annotations.points.filter((annotation) => events.some((event) => event.id === annotation.id)), []);
  assert.deepEqual(probe.options.annotations.xaxis.map((annotation) => annotation.id), events.map((event) => event.id));
  assert.equal(probe.options.annotations.xaxis.every((annotation) => annotation.y === undefined), true);
});

test('DebitTrendChart uses distinct flow event shapes and preserves typed low-flow TSS tooltip context', async () => {
  const events = [
    { id: 'drop', ts: '2026-08-24T23:55:00Z', field: 'debit', type: 'flow_drop', label: 'Turun', context: { debit: { value: 2.5 } } },
    { id: 'none', ts: '2026-08-25T00:00:00Z', field: 'debit', type: 'no_flow', label: 'Tidak ada', context: { debit: { value: 0 } } },
    { id: 'restored', ts: '2026-08-25T00:05:00Z', field: 'debit', type: 'flow_restored', label: 'Pulih', context: { debit: { value: 2.5 } } },
    { id: 'tss-check', ts: '2026-08-24T23:55:00Z', field: 'debit', type: 'low_flow_tss_check', label: 'TSS <periksa>', context: { interval_seconds: 300, debit: { value: 2.5 }, tss: { baseline: 10, current: 4, delta: -6, percent: -60 } } },
  ];
  const probe = debitProbe(await renderDebit(sampleDebitSnapshot({ events })));
  const shapes = Object.fromEntries(probe.options.annotations.points.filter((annotation) => events.some((event) => event.id === annotation.id)).map((annotation) => [annotation.id, annotation.marker.shape]));
  assert.deepEqual(shapes, { drop: 'triangle', none: 'square', restored: 'diamond', 'tss-check': 'star' });
  assert.match(probe.tooltip, /Event: TSS &lt;periksa&gt;/);
  assert.match(probe.tooltip, /Interval: 5 menit/);
  assert.match(probe.tooltip, /TSS baseline: 10/);
  assert.match(probe.tooltip, /TSS saat ini: 4/);
  assert.match(probe.tooltip, /TSS perubahan: -6/);
  assert.match(probe.tooltip, /TSS persentase: -60%/);
});

test('DebitTrendChart renders focused Debit rapid-change events as exact point annotations with their own shape', async () => {
  const rapid = {
    id: 'rapid-debit', ts: '2026-08-24T23:55:00Z', field: 'debit', type: 'rapid_change', label: 'Debit <cepat>',
    context: { baseline: 12, current: 9, delta: -3, percent: -25, points: 5, debit: { value: 9, flow_state: 'low_flow', baseline: 12, current: 8, delta: -4, percent: -33 }, interval_seconds: 300, tss: { baseline: 10, current: 4, delta: -6, percent: -60 } },
  };
  const probe = debitProbe(await renderDebit(sampleDebitSnapshot({ events: [rapid] }), { focusedEventId: rapid.id }));
  const annotation = probe.options.annotations.points.find((point) => point.id === rapid.id);
  assert.deepEqual([annotation.x, annotation.y, annotation.seriesIndex, annotation.yAxisIndex], [Date.parse(rapid.ts), 9, 0, 0]);
  assert.equal(annotation.marker.shape, 'plus');
  assert.equal(annotation.marker.size, 9);
  assert.equal(annotation.marker.fillColor, '#0f766e');
  assert.match(probe.tooltip, /Event: Debit &lt;cepat&gt;/);
});

test('DebitTrendChart tooltip keeps escaped top-level and non-duplicate nested Debit rapid-change context', async () => {
  const rapid = {
    id: 'rapid-context', ts: '2026-08-24T23:55:00Z', field: 'debit', type: 'rapid_change', label: 'Perubahan <cepat>',
    context: { baseline: 12, current: 9, delta: -3, percent: -25, points: 5, debit: { value: 9, flow_state: 'low_<flow>', baseline: 12, current: 8, delta: -4, percent: -33 }, interval_seconds: 300, tss: { baseline: 10, current: 4, delta: -6, percent: -60 } },
  };
  const probe = debitProbe(await renderDebit(sampleDebitSnapshot({ events: [rapid] })));
  for (const expected of [
    'Baseline event: 12', 'Nilai event saat ini: 9', 'Perubahan event: -3', 'Persentase event: -25%', 'Jumlah titik: 5',
    'Status debit: low_&lt;flow&gt;', 'Debit saat ini: 8', 'Debit perubahan: -4', 'Debit persentase: -33%',
    'TSS baseline: 10', 'TSS saat ini: 4', 'TSS perubahan: -6', 'TSS persentase: -60%', 'Interval: 5 menit',
  ]) assert.match(probe.tooltip, new RegExp(expected.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')));
  assert.doesNotMatch(probe.tooltip, /Debit baseline: 12/);
  assert.doesNotMatch(probe.tooltip, /Pengukuran Debit: 9,00 L\/min/);
});

test('DebitTrendChart tooltip keeps conflicting event current and nested Debit measurement as distinct values', async () => {
  const compound = {
    id: 'compound-conflict', ts: '2026-08-24T23:55:00Z', field: 'debit', type: 'rapid_change', label: 'Periksa <gabungan>',
    context: { current: 47, debit: { value: 2.5, flow_state: 'low_flow' }, tss: { current: 47 }, interval_seconds: 300 },
  };
  const probe = debitProbe(await renderDebit(sampleDebitSnapshot({ events: [compound] })));
  assert.match(probe.tooltip, /Nilai event saat ini: 47/);
  assert.match(probe.tooltip, /Pengukuran Debit: 2,50 L\/min/);
  assert.match(probe.tooltip, /Event: Periksa &lt;gabungan&gt;/);
  assert.equal((probe.tooltip.match(/2,50 L\/min/g) ?? []).length >= 2, true);
});


test('Dashboard KPI notes explain the numbers instead of contradicting them', async () => {
  let state;
  const html = await renderDashboard({
    snapshot: sampleDebitSnapshot(),
    kpis: {
      complianceKpi: { compliance_pct: 100, delta_pct: 0 },
      completenessKpi: { actual: 307, expected: 327, pct: 93.9 },
      activeAlertsTop: [{ field: 'cod', threshold_type: 'warning', category: 'data_quality', anomaly_type: 'drift' }],
    },
    inspect: (dashboardState) => { state = dashboardState; },
  });
  assert.match(html, /Stabil dibanding 30 hari sebelumnya/);
  assert.doesNotMatch(html, /Naik 0,0%/);
  assert.match(html, /93,9%/);
  assert.match(html, /307 dari 327 data yang seharusnya sudah masuk/);
  assert.match(html, /Terbaru: COD · Peringatan/);
  const model = state.deviceColumns.find((column) => column.key === 'model');
  assert.equal(model.format('Auto-provisioned'), 'Belum diatur');
  assert.equal(model.format('YSI EXO2'), 'YSI EXO2');
});

test('completeness card shows the share of data due so far and where the day stands', async () => {
  const html = await renderDashboard({
    snapshot: sampleDebitSnapshot(),
    kpis: {
      completenessKpi: { actual: 496, expected: 513, expected_total: 720, pct: 96.7, as_of: '2026-10-17T10:04:00Z' },
    },
  });
  assert.match(html, /96,7%/);
  assert.match(html, /s\.d\. 17:04/);
  const text = html.replace(/<!--[\s\S]*?-->|<[^>]+>/g, '').replace(/\s+/g, ' ');
  assert.match(text, /496 masuk · 17 hilang · 207 belum waktunya/);
  assert.match(html, /aria-label="496 dari 513 data yang seharusnya sudah masuk; 207 data lagi sampai akhir hari"/);
});

test('compact water chart draws only the requested field, without card, heading or summaries, and shades beyond the danger limit', async () => {
  const thresholds = { tss: { warning_max: 15, danger_max: 18, source: 'site_alert_rule' } };
  const html = await renderWater(sampleSnapshot({ thresholds }), { compact: true, fields: ['tss'] });
  assert.doesNotMatch(html, /data-ph-probe=/);
  assert.doesNotMatch(html, /Tren Kualitas Air Limbah/);
  assert.doesNotMatch(html, /aria-label="Ringkasan TSS"/);
  assert.doesNotMatch(html, /class="sensor-card/);
  assert.match(html, /aria-label="Grafik tren TSS"/);
  assert.match(html, /data-chart-type="area"/);
  const tss = chartProbe(html, 'tss');
  assert.deepEqual(tss.options.colors, ['#0E7C86']);
  const bands = tss.options.annotations.yaxis.filter((annotation) => annotation.y2 !== undefined);
  assert.equal(bands.length, 1);
  assert.equal(bands[0].y, 18);
  assert.ok(bands[0].y2 > 18);
  assert.equal(bands[0].fillColor, '#F7E3D8');
});

test('compact pH chart shades below the lower and above the upper limit', async () => {
  const html = await renderWater(sampleSnapshot(), { compact: true, fields: ['ph'] });
  assert.doesNotMatch(html, /data-tss-probe=/);
  const ph = chartProbe(html, 'ph');
  const bands = ph.options.annotations.yaxis.filter((annotation) => annotation.y2 !== undefined);
  assert.equal(bands.length, 2);
  assert.ok(bands.some((band) => band.y === 9 && band.y2 > 9));
  assert.ok(bands.some((band) => band.y2 === 6 && band.y < 6));
});

test('the full water chart keeps threshold lines only (no shaded bands)', async () => {
  const thresholds = { tss: { warning_max: 15, danger_max: 18 } };
  const { ph, tss } = waterProbes(await renderWater(sampleSnapshot({ thresholds })));
  assert.ok([...ph.options.annotations.yaxis, ...tss.options.annotations.yaxis].every((annotation) => annotation.y2 === undefined));
});

test('compact debit chart drops its card heading and summary but keeps scale and flow state', async () => {
  const html = await renderDebit(sampleDebitSnapshot(), { compact: true });
  assert.doesNotMatch(html, /Debit Air Limbah/);
  assert.doesNotMatch(html, /aria-label="Ringkasan Debit"/);
  assert.doesNotMatch(html, /class="sensor-card/);
  assert.match(html, /aria-label="Pilihan skala grafik debit"/);
  assert.match(html, /Status aliran:/);
  assert.match(html, /data-debit-probe=/);
});
