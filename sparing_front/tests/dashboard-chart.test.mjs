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
  '@/Components/PageHeader.vue': '\0dashboard-test:component',
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
              const waterProbe = props.options?.chart?.id === 'dashboard-water-quality'
                ? encodeURIComponent(JSON.stringify({
                  key: instance.vnode.key == null ? '__missing__' : String(instance.vnode.key),
                  options: props.options,
                  series: props.series ?? [],
                  axes,
                  tooltip: tooltips[0] ?? '',
                  tooltips,
                }))
                : undefined;
              return h('div', {
                'data-chart-key': instance.vnode.key == null ? '__missing__' : String(instance.vnode.key),
                'data-chart-type': props.type,
                'data-series-count': props.series?.length ?? 0,
                'data-axis-count': axes.length,
                'data-axis-title': axes[0]?.title?.text ?? '',
                'data-water-probe': waterProbe,
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

  ([{ default: Dashboard }, { default: WaterQualityTrendChart }] = await Promise.all([
    vite.ssrLoadModule('/resources/js/Pages/Dashboard/Index.vue'),
    vite.ssrLoadModule('/resources/js/Components/Dashboard/WaterQualityTrendChart.vue'),
  ]));
  WaterQualityTrendChartClient = await compileWaterClient();
});

test.after(async () => {
  await vite?.close();
});

async function renderDashboard(chartData) {
  const component = {
    ...Dashboard,
    setup(props, context) {
      const state = Dashboard.setup(props, context);
      state.chartData.value = chartData;
      state.latestData.value = chartData.at(-1) ?? null;
      return state;
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

function waterProbe(html) {
  const match = html.match(/data-water-probe="([^"]+)"/);
  assert.ok(match, 'Expected the compiled water-quality ApexChart probe');
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

test('WaterQualityTrendChart keeps pH and TSS series and axes fixed across data shapes', async () => {
  const shapes = [
    sampleSnapshot({ series: { ph: { points: [] }, tss: { points: [] } } }),
    sampleSnapshot({ series: { ph: { points: [{ ts: '2026-08-25T00:05:00Z', value: 7.2 }] }, tss: { points: [] } } }),
    sampleSnapshot({ series: { ph: { points: [] }, tss: { points: [{ ts: '2026-08-25T00:05:00Z', value: 19.5 }] } } }),
    sampleSnapshot(),
  ];

  for (const snapshot of shapes) {
    const probe = waterProbe(await renderWater(snapshot));
    assert.equal(probe.key, 'water-quality:ph|tss:v1');
    assert.deepEqual(probe.series.map((series) => series.name), ['pH', 'TSS']);
    assert.equal(probe.axes.length, 2);
    assert.equal(probe.axes[0].seriesName, 'pH');
    assert.equal(probe.axes[0].min, 0);
    assert.equal(probe.axes[0].max, 14);
    assert.equal(probe.axes[0].title.text, 'pH');
    assert.equal(probe.axes[1].seriesName, 'TSS');
    assert.equal(probe.axes[1].min, 0);
    assert.equal(probe.axes[1].opposite, true);
    assert.equal(probe.axes[1].title.text, 'TSS (mg/L)');
    assert.equal(probe.options.chart.id, 'dashboard-water-quality');
    assert.equal(probe.options.chart.group, 'dashboard-monitoring-time');
    assert.equal(probe.options.yaxis.some((axis) => axis.logarithmic === true), false);
  }
});

test('WaterQualityTrendChart renders measurement-time live copy, response annotations, null gaps, and focused events', async () => {
  const snapshot = sampleSnapshot();
  const html = await renderWater(snapshot, { focusedEventId: 'evt-tss' });
  const probe = waterProbe(html);
  assert.match(html, /Tren Kualitas Air Limbah/);
  assert.match(html, /25 Agu 2026 \u2022 Real-time \u2022 Update terakhir 07:05/);
  assert.deepEqual(probe.series[0].data.map((point) => point.y), [7.1, null, 7.2]);
  assert.deepEqual(probe.series[1].data.map((point) => point.y), [15.5, null, 19.5]);
  assert.equal(probe.options.markers.size, 0);
  assert.equal(probe.axes[1].max, 33);
  assert.equal(probe.options.annotations.yaxis.length, 3);
  assert.deepEqual(probe.options.annotations.yaxis.map((annotation) => annotation.yAxisIndex), [0, 0, 1]);
  assert.equal(probe.options.annotations.points.some((point) => point.id === 'evt-debit'), false);
  assert.equal(probe.options.annotations.points.some((point) => point.id === 'evt-gap'), false);
  assert.equal(probe.options.annotations.points.some((point) => point.id === 'evt-operation'), false);
  assert.deepEqual(probe.options.annotations.points.filter((point) => point.id === 'evt-ph').map((point) => [point.seriesIndex, point.yAxisIndex]), [[0, 0]]);
  assert.deepEqual(probe.options.annotations.points.filter((point) => point.id === 'evt-tss').map((point) => [point.seriesIndex, point.yAxisIndex]), [[1, 1]]);
  assert.deepEqual(probe.options.annotations.points.filter((point) => point.id.startsWith('current-')).map((point) => [point.seriesIndex, point.yAxisIndex]), [[0, 0], [1, 1]]);
  const gap = probe.options.annotations.xaxis.find((annotation) => annotation.id === 'evt-gap');
  assert.ok(gap, 'Expected an x-axis gap annotation without a fabricated y coordinate');
  assert.equal(gap.y, undefined);
  assert.equal(probe.options.annotations.xaxis.find((annotation) => annotation.id === 'evt-operation').y, undefined);
  const focusedGap = waterProbe(await renderWater(snapshot, { focusedEventId: 'evt-gap' }))
    .options.annotations.xaxis.find((annotation) => annotation.id === 'evt-gap');
  assert.equal(focusedGap.borderColor, '#0f766e');
  assert.equal(probe.options.annotations.points.filter((point) => point.id.startsWith('current-')).every((point) => point.label === undefined), true);
  const focused = probe.options.annotations.points.find((point) => point.id === 'evt-tss');
  assert.equal(focused.marker.size, 9);
  assert.match(probe.tooltip, /25 Agu 2026 \u2022 06:55/);
  assert.match(probe.tooltip, /pH:<\/strong> 7\.10/);
  assert.match(probe.tooltip, /TSS:<\/strong> 15\.5 mg\/L/);
  assert.match(probe.tooltip, /Resolusi: 5 menit/);
  assert.match(probe.tooltip, /Minimum: 7\.00/);
  assert.match(probe.tooltip, /Kualitas: Baik/);
});

test('WaterQualityTrendChart uses truthful historical copy, escaped missing-value tooltip, responsive options, and reduced motion', async () => {
  const snapshot = sampleSnapshot({
    meta: { date_from: '2026-08-23T00:00:00Z', date_to: '2026-08-24T00:00:00Z', generated_at: '2026-08-25T00:11:00Z', resolution_seconds: 3600 },
    series: { ph: { points: [{ ts: '2026-08-24T00:00:00Z', value: null, quality: '<img src=x>' }] }, tss: { points: [{ ts: '2026-08-24T00:00:00Z', value: null }] } },
    statistics: { ph: { current: null, current_ts: null, status: 'no_data', status_label: 'Tidak Ada Data', availability_pct: 0 }, tss: { current: null, current_ts: null, status: 'no_data', status_label: 'Tidak Ada Data', availability_pct: 0 } },
  });
  const html = await renderWater(snapshot, { reducedMotion: true });
  const probe = waterProbe(html);
  assert.doesNotMatch(html, /Real-time/);
  assert.match(html, /Resolusi 1 jam/);
  assert.match(probe.tooltip, /Data Tidak Tersedia/);
  assert.match(probe.tooltip, /&lt;img src=x&gt;/);
  assert.doesNotMatch(probe.tooltip, /<img src=x>/);
  assert.match(probe.tooltip, /Kualitas: Tidak Tersedia/);
  assert.equal(probe.options.chart.animations.enabled, false);
  assert.equal(Array.isArray(probe.options.responsive), true);
  assert.match(html, /aria-label="Grafik tren pH dan TSS"/);
  assert.match(html, /Ringkasan aksesibilitas/);
  assert.match(html, /Tidak Ada Data/);
});

test('WaterQualityTrendChart aligns sparse tooltip peers by hovered timestamp and uses the response TSS unit', async () => {
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
  const probe = waterProbe(await renderWater(snapshot));
  const hoverAtPhSecondPoint = probe.tooltips[1];
  assert.match(hoverAtPhSecondPoint, /pH:<\/strong> 7\.30/);
  assert.match(hoverAtPhSecondPoint, /TSS:<\/strong> 20\.4 g\/L/);
  assert.doesNotMatch(hoverAtPhSecondPoint, /15\.5/);
  assert.match(probe.tooltips[0], /TSS:<\/strong> Data Tidak Tersedia/);
});

test('WaterQualityTrendChart renders exact metadata, matching event context, and truthful fallback subtitles', async () => {
  const liveWithoutMeasurement = await renderWater(sampleSnapshot({
    statistics: { ph: { current: null, current_ts: null }, tss: { current: null, current_ts: null } },
  }));
  assert.match(liveWithoutMeasurement, /Real-time \u2022 Waktu pembacaan belum tersedia/);

  const historical = await renderWater(sampleSnapshot({
    meta: { date_from: '2026-08-23T00:00:00Z', date_to: '2026-08-24T00:00:00Z', generated_at: '2026-08-25T00:11:00Z', resolution_seconds: 90 },
  }));
  assert.match(historical, /Periode 23 Agu 2026 \u2013 24 Agu 2026 \u2022 Resolusi 90 detik/);

  const probe = waterProbe(await renderWater(sampleSnapshot()));
  assert.match(probe.tooltip, /Event: pH perlu diperiksa/);
  assert.match(probe.tooltip, /Nilai saat ini: 7\.1/);
  assert.match(probe.tooltip, /Baseline: 7/);
  assert.match(probe.tooltip, /Perubahan: 0\.1/);
  assert.match(probe.tooltip, /Persentase: 1\.4%/);
  assert.match(probe.tooltip, /Interval: 5 menit/);
  assert.match(probe.tooltip, /TSS event: 15\.5/);
  assert.match(probe.tooltip, /Debit event: 0/);
  assert.match(probe.tooltip, /Jumlah bucket: 3/);
});

test('WaterQualityTrendChart forwards retry from its composed stale ChartState', async () => {
  const view = await mountWater();
  const retry = allNodes(view.root, (node) => node.type === 'button' && eventText(node).includes('Coba Lagi'))[0];
  assert.ok(retry, 'Expected the stale ChartState retry action');
  retry.props.onClick();
  assert.deepEqual(view.emitted, ['retry']);
  view.unmount();
});

test('changes the debit chart identity when the temperature series is added', async () => {
  const withoutTemperature = debitTrend(chartProbes(await renderDashboard([{
    ts: '2026-08-25T00:00:00Z',
    ph: 7.1,
    debit: 2.5,
    temp: 0,
  }])));
  const withTemperature = debitTrend(chartProbes(await renderDashboard([{
    ts: '2026-08-25T00:00:00Z',
    ph: 7.1,
    debit: 2.5,
    temp: 27,
  }])));

  assert.ok(withoutTemperature, 'Expected the debit-only chart');
  assert.ok(withTemperature, 'Expected the debit and temperature chart');
  assert.equal(withoutTemperature.seriesCount, 1);
  assert.equal(withoutTemperature.axisCount, 1);
  assert.equal(withTemperature.seriesCount, 2);
  assert.equal(withTemperature.axisCount, 2);
  assert.notEqual(
    withTemperature.key,
    withoutTemperature.key,
    'ApexCharts must remount when the optional temperature series changes the y-axis count',
  );
});
