import assert from 'node:assert/strict';
import test from 'node:test';
import { fileURLToPath } from 'node:url';
import { resolve } from 'node:path';
import { createSSRApp, h } from 'vue';
import { renderToString } from '@vue/server-renderer';

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
              return h('div', {
                'data-chart-key': instance.vnode.key == null ? '__missing__' : String(instance.vnode.key),
                'data-chart-type': props.type,
                'data-series-count': props.series?.length ?? 0,
                'data-axis-count': axes.length,
                'data-axis-title': axes[0]?.title?.text ?? '',
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

  ({ default: Dashboard } = await vite.ssrLoadModule('/resources/js/Pages/Dashboard/Index.vue'));
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

test('changes the water-trend chart identity when its active series structure changes', async () => {
  const initial = waterTrend(chartProbes(await renderDashboard([])));
  const populated = waterTrend(chartProbes(await renderDashboard([{
    ts: '2026-08-25T00:00:00Z',
    ph: 7.1,
    tss: 12,
    cod: 24,
    nh3n: 0.4,
  }])));

  assert.ok(initial, 'Expected the initial water-trend chart');
  assert.ok(populated, 'Expected the populated water-trend chart');
  assert.equal(initial.seriesCount, 1);
  assert.equal(initial.axisCount, 1);
  assert.equal(populated.seriesCount, 4);
  assert.equal(populated.axisCount, 4);
  assert.notEqual(
    populated.key,
    initial.key,
    'ApexCharts must remount instead of racing separate series and y-axis updates',
  );
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
