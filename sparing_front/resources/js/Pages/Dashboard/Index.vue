<template>
  <AppLayout>

    <PageHeader
      :crumb="['Beranda', 'Dashboard']"
      title="Dashboard"
      :subtitle="currentSite ? `${currentSite.name} — ${currentSite.company_name}` : 'Pilih lokasi untuk memantau data'"
    >
      <template #actions>
        <div class="flex items-center gap-2 text-xs text-muted">
          <span class="tabular-nums">{{ lastUpdatedText }}</span>
          <button
            type="button"
            class="flex items-center gap-1.5 rounded-lg px-3 py-1.5 font-semibold text-muted transition-colors hover:bg-[#EEF4F4] disabled:opacity-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary"
            :disabled="isRefreshing || timeseriesIsRefreshing"
            @click="manualRefresh"
          >
            <i class="fas fa-sync-alt" :class="{ 'animate-spin': isRefreshing || timeseriesIsRefreshing }" aria-hidden="true"></i>
            Muat ulang
          </button>
        </div>
      </template>
    </PageHeader>

    <SiteStatusChips class="mb-3" :chips="siteChips" :model-value="selectedSiteUid" @update:model-value="selectSite" />

    <!-- One sheet, three layers: status (everyone), parameters + chart (everyone),
         devices & data (operator/admin). -->
    <article class="overflow-hidden rounded-xl border border-[#DCE6E6] bg-white">
      <!-- The band speaks only once the site's rules, reading and day are loaded;
           before that it would state a status the data does not support. -->
      <StatusBand
        v-if="currentSite && statsLoaded && !statusLoadFailed"
        :band="band"
        :month="month"
        :completeness-pct="completenessKpi?.pct ?? null"
        :completeness-as-of="completenessAsOf"
        :completeness-segments="completenessBar"
        :site-label="siteLabel"
        :date-label="todayLabel"
        :timezone="siteTz"
        :now="nowTick"
        :can-followup="canOperate"
        @followup="openFollowup"
      />
      <div v-else-if="!statsLoaded" class="h-40 animate-pulse bg-deep motion-reduce:animate-none" aria-busy="true" aria-label="Memuat status kepatuhan"></div>
      <p v-else-if="!currentSite" class="bg-idle px-5 py-6 text-[13px] text-white md:px-6">Belum ada lokasi yang bisa ditampilkan.</p>
      <!-- A failed request must not turn into a false status sentence in the band. -->
      <p v-else class="bg-idle px-5 py-6 text-[13px] text-white md:px-6" role="status">Status kepatuhan belum bisa dimuat. Muat ulang untuk mencoba lagi.</p>

      <ParameterStrip :items="parameterItems" :stale="band.state === 'stale'" :model-value="selectedField" chart-id="dashboard-parameter-chart" @update:model-value="selectField" />

      <div class="grid grid-cols-1 lg:grid-cols-[minmax(0,2.2fr)_minmax(16rem,1fr)]">
        <section id="dashboard-parameter-chart" class="min-w-0 px-4 py-4 md:px-6" aria-label="Grafik parameter">
          <div class="mb-3 flex flex-col gap-2 xl:flex-row xl:items-start xl:justify-between">
            <h3 class="shrink-0 text-[15px] font-bold text-ink">{{ FIELD_LABELS[selectedField] }}</h3>
            <div class="min-w-0 xl:max-w-[75%]">
              <PeriodFilter
                :model-value="timeseriesPreset"
                :custom-range="monitoringCustomRange"
                :timezone="monitoringTimezone"
                @update:model-value="selectMonitoringPeriod"
                @update:custom-range="updateMonitoringCustomRange"
                @apply-custom="applyMonitoringCustomRange"
              />
            </div>
          </div>
          <ParameterTrendChart
            :field="selectedField"
            :snapshot="monitoringDisplaySnapshot"
            :state="timeseriesState"
            :stale="timeseriesIsStale"
            :focused-event-id="focusedEventId"
            :reduced-motion="reducedMotion"
            @retry="retryMonitoring"
          />
        </section>
        <MonitoringEventList
          bare
          class="border-t border-line lg:border-l lg:border-t-0"
          :events="monitoringEvents"
          :event-total="monitoringEventTotal"
          :timezone="monitoringTimezone"
          @focus-event="focusMonitoringEvent"
        />
      </div>

      <OpsPanel
        v-if="canOperate"
        :logger="currentLoggerStatus"
        :active-alerts="activeAlerts"
        :active-count="activeAlertCount"
        :received-today="completenessKpi?.actual ?? null"
        :timezone="siteTz"
        :now="nowTick"
      >
        <div v-if="showElectrical" class="rounded-lg border border-[#DCE6E6] bg-white p-4">
          <h4 class="text-[13px] font-bold text-ink">Parameter kelistrikan</h4>
          <p class="mb-3 text-xs text-muted">Tegangan &amp; arus</p>
          <div class="h-52 md:h-60">
            <apexchart
              v-if="electricalOptions"
              type="line"
              height="100%"
              :options="electricalOptions"
              :series="electricalSeries"
            />
          </div>
        </div>

        <DataTable
          title="Status Perangkat Sensor"
          :data="devices"
          :columns="deviceColumns"
          :loading="devicesLoading"
          empty-message="Tidak ada perangkat terdaftar"
        >
          <template #cell-status="{ row }">
            <StatusBadge :status="getDeviceStatus(row)" :label="getDeviceStatusLabel(row)" />
          </template>
          <template #cell-last_seen="{ value }">
            {{ getRelativeTime(value) }}
          </template>
          <template #cell-actions="{ row }">
            <button @click="viewDeviceDetail(row)" class="text-primary hover:underline text-xs font-medium">
              Detail
            </button>
          </template>
        </DataTable>
      </OpsPanel>
    </article>

    <AlertFollowupModal
      :open="followupOpen"
      mode="followup"
      :alert="followupTarget"
      @close="closeFollowup"
      @submit="submitFollowup"
    />

    <!-- ─── Device Detail Modal ─── -->
    <Transition name="fade">
      <div
        v-if="showDeviceDetailModal && selectedDevice"
        class="fixed inset-0 bg-slate-900/60 backdrop-blur-sm flex items-center justify-center z-50 p-4"
        @click.self="closeDeviceDetailModal"
      >
        <div class="bg-white rounded-2xl max-w-lg w-full p-6 shadow-2xl">
          <div class="flex justify-between items-center mb-4">
            <h3 class="text-base font-bold text-slate-800">Detail Perangkat</h3>
            <button @click="closeDeviceDetailModal" class="text-slate-400 hover:text-slate-600 transition-colors">
              <i class="fas fa-times"></i>
            </button>
          </div>
          <div class="space-y-4">
            <div class="bg-slate-50 rounded-xl p-4 grid grid-cols-2 gap-4">
              <div>
                <p class="text-xs text-slate-500 mb-0.5">ID Perangkat</p>
                <p class="text-sm font-bold text-slate-800">#IOT-{{ String(selectedDevice.id).padStart(3, '0') }}</p>
              </div>
              <div>
                <p class="text-xs text-slate-500 mb-0.5">Status</p>
                <StatusBadge :status="getDeviceStatus(selectedDevice)" :label="getDeviceStatusLabel(selectedDevice)" />
              </div>
            </div>
            <div class="grid grid-cols-2 gap-4 text-sm">
              <div><p class="text-xs text-slate-500 mb-0.5">Nama</p><p class="font-medium text-slate-800">{{ selectedDevice.name }}</p></div>
              <div><p class="text-xs text-slate-500 mb-0.5">Model</p><p class="font-medium text-slate-800">{{ deviceModelLabel(selectedDevice.model) }}</p></div>
              <div><p class="text-xs text-slate-500 mb-0.5">Serial Number</p><p class="font-medium text-slate-800">{{ selectedDevice.serial_no || '-' }}</p></div>
              <div><p class="text-xs text-slate-500 mb-0.5">Terakhir Update</p><p class="font-medium text-slate-800">{{ getRelativeTime(selectedDevice.last_seen) }}</p></div>
            </div>
            <div class="flex justify-end pt-3 border-t border-slate-100">
              <button @click="closeDeviceDetailModal" class="px-4 py-2 text-sm bg-slate-100 text-slate-700 rounded-lg hover:bg-slate-200 transition-colors">
                Tutup
              </button>
            </div>
          </div>
        </div>
      </div>
    </Transition>

  </AppLayout>
</template>

<script setup>
import { ref, onMounted, onUnmounted, computed, watch } from 'vue';
import VueApexCharts from 'vue3-apexcharts';
import AppLayout from '@/Layouts/AppLayout.vue';
import PageHeader from '@/Components/PageHeader.vue';
import StatusBadge from '@/Components/StatusBadge.vue';
import DataTable from '@/Components/DataTable.vue';
import AlertFollowupModal from '@/Components/AlertFollowupModal.vue';
import PeriodFilter from '@/Components/Dashboard/PeriodFilter.vue';
import MonitoringEventList from '@/Components/Dashboard/MonitoringEventList.vue';
import SiteStatusChips from '@/Components/Dashboard/SiteStatusChips.vue';
import StatusBand from '@/Components/Dashboard/StatusBand.vue';
import ParameterStrip from '@/Components/Dashboard/ParameterStrip.vue';
import ParameterTrendChart from '@/Components/Dashboard/ParameterTrendChart.vue';
import OpsPanel from '@/Components/Dashboard/OpsPanel.vue';
import { completenessSegments } from '@/Utils/completeness.js';
import { formatDashboardTimestamp, localMidnightISO } from '@/Utils/dashboardTimeseries.js';
import { FIELD_LABELS, bandState, fieldFlagged, localDateISO, monthCompliance } from '@/Utils/dashboardStatus.js';
import { useApi } from '@/Composables/useApi';
import { useDashboardTimeseries } from '@/Composables/useDashboardTimeseries';
import { useAuth } from '@/Composables/useAuth';
import { useToast } from '@/Composables/useToast';
import { getRelativeTime, getSensorStatus, getSensorUnit, parseUTC } from '@/Utils/helpers';
import { buildSiteChips } from '@/Utils/siteStatus.js';
import logger from '@/Utils/logger';

const apexchart = VueApexCharts;

const colors = {
  voltage: '#f59e0b',
  current: '#ef4444',
};

const {
  getLatestData, getData, getDevices, getSites,
  getCompleteness, getComplianceDaily, getAlerts, getAlertRules, getLoggerStatus,
  getDashboardTimeseries, followupAlert, getAlertCount,
} = useApi();
const toast = useToast();
const { filterSitesByUser, isOperator } = useAuth();
// Operators and admins get the devices & data layer and the follow-up action;
// viewers (clients) do not. Presentation only: the API scopes the data itself.
const canOperate = computed(() => Boolean(isOperator?.value));

// ── State ──────────────────────────────────────────────────────
const latestData      = ref(null);
const devices         = ref([]);
const devicesLoading  = ref(false);
const sites           = ref([]);
const currentSite     = ref(null);
const selectedSiteUid = ref('');
const selectedField   = ref('tss');
const auxiliaryChartData = ref([]);
const isRefreshing    = ref(false);
const focusedEventId  = ref(null);
const monitoringCustomRange = ref({ dateFrom: null, dateTo: null });
const reducedMotion = ref(false);
// "Now" for the status band; refreshed with every stats load.
const nowTick = ref(Date.now());
let reducedMotionMediaQuery = null;
let removeReducedMotionListener = null;

const {
  preset: timeseriesPreset,
  snapshot: timeseriesSnapshot,
  state: timeseriesState,
  errorMessage: timeseriesErrorMessage,
  isRefreshing: timeseriesIsRefreshing,
  isStale: timeseriesIsStale,
  load: loadTimeseries,
  retry: retryTimeseries,
  setPreset: setTimeseriesPreset,
  setCustomRange: setTimeseriesCustomRange,
  startPolling: startTimeseriesPolling,
  stopPolling: stopTimeseriesPolling,
} = useDashboardTimeseries({
  siteUid: selectedSiteUid,
  fetchTimeseries: getDashboardTimeseries,
  pollMs: 30000,
});

const completenessKpi   = ref(null);
const complianceDays    = ref([]);
const activeAlerts      = ref([]);
const activeAlertCount  = ref(null);
const alertRulesByField = ref({});
const loggerRows        = ref([]);
const sitesStatus       = ref([]);
const followupOpen      = ref(false);
const followupTarget    = ref(null);
const followupSaving    = ref(false);
// True once the selected site's rules, latest reading and stats have loaded.
const statsLoaded       = ref(false);
// The band's three sources; a failed one hides the band instead of letting it
// say something false ("Baku mutu belum diatur", "Belum ada data").
const rulesError        = ref(false);
const latestError       = ref(false);
const daysError         = ref(false);
const statusLoadFailed  = computed(() => rulesError.value || latestError.value || daysError.value);

let refreshInterval = null;

// A response belongs to the site selected when it was requested; once the
// user has moved on it is dropped, or site B would be judged with site A's data.
const stillCurrent = (uid) => uid === (selectedSiteUid.value || null);
// Bumped by every site switch, so only the latest switch marks the stats loaded.
let siteLoadSeq = 0;

// ── Computed ────────────────────────────────────────────────────
const siteTz = computed(() => currentSite.value?.timezone || 'Asia/Jakarta');
const monitoringTimezone = computed(() => timeseriesSnapshot.value?.meta?.timezone || siteTz.value);
const monitoringDisplaySnapshot = computed(() => {
  if (!timeseriesErrorMessage.value) return timeseriesSnapshot.value;
  return {
    ...(timeseriesSnapshot.value || {}),
    meta: {
      ...(timeseriesSnapshot.value?.meta || {}),
      message: timeseriesErrorMessage.value,
    },
  };
});
const monitoringEvents = computed(() => timeseriesSnapshot.value?.events || []);
const monitoringEventTotal = computed(() => timeseriesSnapshot.value?.event_total ?? monitoringEvents.value.length);
const MONITORING_FIELDS = new Set(['ph', 'tss', 'debit']);

function monitoringSummary(field) {
  return timeseriesSnapshot.value?.statistics?.[field] ?? null;
}

const lastMeasurementTimestamp = computed(() => {
  const timestamps = [...MONITORING_FIELDS]
    .map((field) => monitoringSummary(field)?.current_ts)
    .filter((value) => typeof value === 'string' && Number.isFinite(Date.parse(value)))
    .sort((left, right) => Date.parse(right) - Date.parse(left));
  return timestamps[0] || latestData.value?.ts || null;
});

const lastUpdatedText = computed(() => lastMeasurementTimestamp.value
  ? `Diperbarui ${getRelativeTime(lastMeasurementTimestamp.value)}`
  : 'Belum diperbarui');

// pH, TSS and Debit pick the chart; these optional readings join the strip.
const EXTRA_FIELDS = ['cod', 'nh3n', 'temp'];

// Unfitted auxiliary sensors historically report a constant zero, so a field
// only counts as present once it reports a non-zero value.
function hasAuxiliaryData(field) {
  const series = auxiliaryChartData.value || [];
  if (series.some(d => d[field] != null && d[field] !== 0)) return true;
  const latest = latestData.value?.[field];
  return latest != null && latest !== 0;
}
const extraFields = computed(() => EXTRA_FIELDS.filter(hasAuxiliaryData));
const showElectrical = computed(() => hasAuxiliaryData('voltage') || hasAuxiliaryData('current'));

const sparkPoints = computed(() => Object.fromEntries(EXTRA_FIELDS.map((field) => [
  field, auxiliaryChartData.value.slice(-30).map((d) => (d[field] != null ? d[field] : null)),
])));

const loggerStates = computed(() => Object.fromEntries(
  loggerRows.value.filter((row) => row.site_uid).map((row) => [row.site_uid, row.state]),
));
const currentLoggerStatus = computed(() => loggerRows.value.find((row) => row.site_uid === selectedSiteUid.value) ?? null);

const siteChips = computed(() => buildSiteChips(
  sitesStatus.value.length ? sitesStatus.value : sites.value.map((site) => ({ site, latest: null })),
  loggerStates.value,
));

// "Today" in the site's own calendar (WIB/WITA/WIT), the day compliance-daily counts.
const todayISO = computed(() => localDateISO(siteTz.value, new Date(nowTick.value)));
const todayStatus = computed(() => complianceDays.value.find((day) => day.date === todayISO.value)?.status ?? null);
const STRIP_FIELDS = ['ph', 'tss', 'debit'];
// What the site actually reports: pH, TSS and Debit always, other readings once
// they report a non-zero value. The band and the strip judge only these.
const reportedFields = computed(() => [...STRIP_FIELDS, ...extraFields.value]);
const band = computed(() => bandState({
  rules: alertRulesByField.value,
  latest: latestData.value,
  todayStatus: todayStatus.value,
  activeAlerts: activeAlerts.value,
  now: nowTick.value,
  reported: reportedFields.value,
}));
// Without rules the backend still counts any day with readings as "ok"; a
// month figure would contradict "Baku mutu belum diatur".
const month = computed(() => ((!complianceDays.value.length || band.value.state === 'no_rules')
  ? null
  : monthCompliance(complianceDays.value, todayISO.value)));
const siteLabel = computed(() => (currentSite.value
  ? [currentSite.value.name, currentSite.value.company_name].filter(Boolean).join(' · ')
  : ''));
const todayLabel = computed(() => {
  const options = { weekday: 'long', day: 'numeric', month: 'short' };
  const now = new Date(nowTick.value);
  try {
    return new Intl.DateTimeFormat('id-ID', { ...options, timeZone: siteTz.value }).format(now);
  } catch {
    // An unknown IANA zone in the site record must not take the page down.
    return new Intl.DateTimeFormat('id-ID', { ...options, timeZone: 'Asia/Jakarta' }).format(now);
  }
});

// An operational-status row (calibration, stopped, malfunction) is not a
// measurement; like the band, the strip does not judge it.
const latestIsMeasurement = computed(() => latestData.value?.op_status == null);

const parameterItems = computed(() => reportedFields.value.map((field) => ({
  field,
  label: FIELD_LABELS[field] ?? field,
  value: latestData.value?.[field] ?? null,
  // getSensorUnit('ph') is 'pH'; the column label already says it.
  unit: field === 'ph' ? '' : getSensorUnit(field),
  // undefined = not known yet (loading or failed): never "tanpa baku mutu".
  rule: (rulesError.value || !statsLoaded.value) ? undefined : (alertRulesByField.value[field] ?? null),
  spark: STRIP_FIELDS.includes(field) ? null : sparkPoints.value[field],
  // Same per-field quality rule as the status band: a flagged value is not judged.
  flagged: Boolean(latestData.value) && (!latestIsMeasurement.value || fieldFlagged(latestData.value, field)),
  flagNote: latestData.value && !latestIsMeasurement.value ? 'bukan pengukuran' : null,
})));

const completenessBar = computed(() => completenessSegments(completenessKpi.value));
// When the percentage was calculated, in the site's clock ("s.d. 17:04").
const completenessAsOf = computed(() => {
  const asOf = completenessKpi.value?.as_of;
  return asOf ? formatDashboardTimestamp(asOf, siteTz.value, true) : '';
});

// Devices created automatically on first ingest carry an internal placeholder model.
const deviceModelLabel = v => (!v || v === 'Auto-provisioned' ? 'Belum diatur' : v);

// Device table columns
const deviceColumns = [
  { key: 'id',          label: 'ID',      format: v => `#IOT-${String(v).padStart(3, '0')}` },
  { key: 'name',        label: 'Nama' },
  { key: 'model',       label: 'Model',   format: deviceModelLabel },
  { key: 'last_seen',   label: 'Terakhir Update' },
  { key: 'status',      label: 'Status' },
  { key: 'actions',     label: 'Aksi' },
];

// ── Auxiliary electrical chart ─────────────────────────────────
const electricalOptions = computed(() => ({
  chart: { type: 'line', toolbar: { show: false }, zoom: { enabled: false }, animations: { enabled: true, speed: 800 }, fontFamily: 'Plus Jakarta Sans, sans-serif' },
  colors: [colors.voltage, colors.current],
  dataLabels: { enabled: false },
  stroke: { curve: 'straight', width: 2.5 },
  xaxis: {
    type: 'datetime',
    labels: {
      style: { colors: '#94a3b8', fontSize: '10px' },
      formatter: (val) => new Date(val).toLocaleTimeString('id-ID', { timeZone: siteTz.value, hour: '2-digit', minute: '2-digit' }),
    },
    axisBorder: { show: false },
    axisTicks: { show: false },
  },
  yaxis: [
    { title: { text: 'V', style: { color: colors.voltage, fontSize: '11px' } }, labels: { style: { colors: '#94a3b8', fontSize: '10px' } } },
    { opposite: true, title: { text: 'A', style: { color: colors.current, fontSize: '11px' } }, labels: { style: { colors: '#94a3b8', fontSize: '10px' } } },
  ],
  legend: { position: 'top', fontSize: '11px' },
  grid: { borderColor: '#f1f5f9', strokeDashArray: 4 },
  tooltip: {
    x: {
      formatter: (val) => new Date(val).toLocaleString('id-ID', { timeZone: siteTz.value, day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' }),
    },
    theme: 'light',
  },
}));

const electricalSeries = computed(() => [
  { name: 'Voltage', data: auxiliaryChartData.value.map(d => ({ x: parseUTC(d.ts), y: d.voltage })) },
  { name: 'Current', data: auxiliaryChartData.value.map(d => ({ x: parseUTC(d.ts), y: d.current })) },
]);

// ── Data loaders ────────────────────────────────────────────────
const loadSites = async () => {
  try {
    const response = await getSites({ per_page: 100 });
    let list = response?.items || (Array.isArray(response) ? response : response?.data || []);
    sites.value = filterSitesByUser(list);
    if (sites.value.length > 0) {
      selectedSiteUid.value = sites.value[0].uid;
      currentSite.value     = sites.value[0];
    }
  } catch (e) {
    logger.error('Failed to load sites:', e);
  }
};

const onSiteChange = async () => {
  const seq = ++siteLoadSeq;
  const selected = sites.value.find(s => s.uid === selectedSiteUid.value);
  currentSite.value = selected || null;
  focusedEventId.value = null;
  // Never judge this site with the previous site's reading, day, alerts or rules
  // (a failed request below would otherwise leave them in place).
  latestData.value = null;
  complianceDays.value = [];
  activeAlerts.value = [];
  activeAlertCount.value = null;
  completenessKpi.value = null;
  alertRulesByField.value = {};
  statsLoaded.value = false;
  rulesError.value = false;
  latestError.value = false;
  daysError.value = false;
  if (!selected) {
    statsLoaded.value = true;
    await loadTimeseries();
    return;
  }
  await Promise.all([loadLatestData(), loadDevices(), loadMonitoringData(), loadAlertRules(), loadStats()]);
  if (seq === siteLoadSeq) statsLoaded.value = true;
};

const selectSite = (uid) => {
  selectedSiteUid.value = uid;
  onSiteChange();
};

const selectField = (field) => {
  selectedField.value = field;
  focusedEventId.value = null;
};

const loadLatestData = async () => {
  const uid = selectedSiteUid.value || null;
  if (!uid) return;
  try {
    const row = await getLatestData(uid);
    if (!stillCurrent(uid)) return;
    latestData.value = row;
    latestError.value = false;
  } catch (e) {
    if (!stillCurrent(uid)) return;
    latestError.value = true;
    logger.error('Failed to load latest data:', e);
  }
};

const loadDevices = async () => {
  const uid = selectedSiteUid.value || null;
  // Only operators and admins see the device table.
  if (!uid || !canOperate.value) return;
  devicesLoading.value = true;
  try {
    const response = await getDevices({ site_uid: uid });
    if (!stillCurrent(uid)) return;
    let list = response?.items || (Array.isArray(response) ? response : response?.data || []);
    // Backend now supplies real last_seen + status per device.
    devices.value = list.filter(d => d.is_active !== false);
  } catch (e) {
    if (stillCurrent(uid)) devices.value = [];
  } finally {
    if (stillCurrent(uid)) devicesLoading.value = false;
  }
};

let auxiliaryRequestToken = 0;
let latestAuxiliaryLoad = Promise.resolve();

const loadAuxiliaryChartData = async (snapshot) => {
  const token = ++auxiliaryRequestToken;
  const siteUid = selectedSiteUid.value;
  const dateFrom = snapshot?.meta?.date_from;
  const dateTo = snapshot?.meta?.date_to;
  if (!siteUid || !dateFrom || !dateTo) {
    auxiliaryChartData.value = [];
    return;
  }

  try {
    const response = await getData({
      site_uid: siteUid,
      date_from: dateFrom,
      date_to: dateTo,
      fields: 'cod,nh3n,voltage,current,temp',
      per_page: 100,
      order: 'desc',
    });
    if (token !== auxiliaryRequestToken || selectedSiteUid.value !== siteUid || timeseriesSnapshot.value !== snapshot) return;
    const rows = response?.items || (Array.isArray(response) ? response : []);
    auxiliaryChartData.value = rows.slice().reverse();
  } catch (e) {
    if (token === auxiliaryRequestToken && selectedSiteUid.value === siteUid) auxiliaryChartData.value = [];
    logger.error('Failed to load auxiliary chart data:', e);
  }
};

watch(timeseriesSnapshot, (snapshot) => {
  if (focusedEventId.value && !snapshot?.events?.some((event) => event?.id === focusedEventId.value)) {
    focusedEventId.value = null;
  }
  latestAuxiliaryLoad = loadAuxiliaryChartData(snapshot);
}, { flush: 'sync' });

const loadMonitoringData = async (options) => {
  await loadTimeseries(options);
  await latestAuxiliaryLoad;
};

const retryMonitoring = async () => {
  await retryTimeseries();
  await latestAuxiliaryLoad;
};

const selectMonitoringPeriod = async (preset) => {
  focusedEventId.value = null;
  if (preset === 'custom') {
    await setTimeseriesCustomRange({ dateFrom: null, dateTo: null });
    return;
  }
  await setTimeseriesPreset(preset);
  await latestAuxiliaryLoad;
};

const updateMonitoringCustomRange = (range) => {
  monitoringCustomRange.value = {
    dateFrom: typeof range?.dateFrom === 'string' ? range.dateFrom : null,
    dateTo: typeof range?.dateTo === 'string' ? range.dateTo : null,
  };
  // Editing is a draft operation. Invalidate any request started with the
  // previously applied range, but wait for the explicit Apply action to load.
  void setTimeseriesCustomRange({ dateFrom: null, dateTo: null });
};

const applyMonitoringCustomRange = async () => {
  if (!monitoringCustomRange.value.dateFrom || !monitoringCustomRange.value.dateTo) return;
  focusedEventId.value = null;
  await setTimeseriesCustomRange(monitoringCustomRange.value);
  await latestAuxiliaryLoad;
};

const focusMonitoringEvent = (event) => {
  const id = event?.id;
  focusedEventId.value = typeof id === 'string' || (typeof id === 'number' && Number.isFinite(id)) ? id : null;
};

const loadAlertRules = async () => {
  const uid = selectedSiteUid.value || null;
  if (!uid) return;
  try {
    const list = await getAlertRules(uid);
    if (!stillCurrent(uid)) return;
    const map = {};
    (Array.isArray(list) ? list : []).forEach(r => { map[r.field] = r; });
    alertRulesByField.value = map;
    rulesError.value = false;
  } catch (e) {
    if (!stillCurrent(uid)) return;
    logger.error('Failed to load alert rules:', e);
    alertRulesByField.value = {};
    rulesError.value = true;
  }
};

// Status band, ops panel and chips — scoped to the selected site. Each call is
// independent so one failing endpoint never blanks the rest of the dashboard.
const loadStats = async () => {
  const siteUid = selectedSiteUid.value || null;
  nowTick.value = Date.now();
  try {
    // "Hari ini" starts at the site's local midnight (WIB/WITA/WIT).
    const kpi = await getCompleteness(24, siteUid, localMidnightISO(siteTz.value));
    if (!stillCurrent(siteUid)) return;
    completenessKpi.value = kpi;
  } catch (e) {
    if (!stillCurrent(siteUid)) return;
    logger.error('Failed to load completeness stats:', e);
  }
  try {
    const response = await getComplianceDaily(todayISO.value.slice(0, 7), siteUid);
    if (!stillCurrent(siteUid)) return;
    complianceDays.value = Array.isArray(response?.days) ? response.days : [];
    daysError.value = false;
  } catch (e) {
    if (!stillCurrent(siteUid)) return;
    daysError.value = true;
    logger.error('Failed to load daily compliance:', e);
  }
  try {
    const rows = await getLoggerStatus();
    if (!stillCurrent(siteUid)) return;
    loggerRows.value = Array.isArray(rows) ? rows : (rows?.items || []);
  } catch (e) {
    if (!stillCurrent(siteUid)) return;
    logger.error('Failed to load logger status:', e);
  }
  try {
    // limit 100: the default 20 newest could push the breaching compliance
    // alert out behind data-quality alerts, which never auto-resolve.
    const list = await getAlerts({ status: 'active', limit: 100, ...(siteUid ? { site_uid: siteUid } : {}) });
    if (!stillCurrent(siteUid)) return;
    activeAlerts.value = Array.isArray(list) ? list : (list?.items || []);
  } catch (e) {
    if (!stillCurrent(siteUid)) return;
    logger.error('Failed to load active alerts:', e);
  }
  try {
    // The list above stops at 100; the panel's count must not.
    const response = await getAlertCount('active', siteUid);
    if (!stillCurrent(siteUid)) return;
    activeAlertCount.value = typeof response?.count === 'number' ? response.count : null;
  } catch (e) {
    if (!stillCurrent(siteUid)) return;
    activeAlertCount.value = null;
    logger.error('Failed to load active alarm count:', e);
  }
};

// Latest reading of every scoped site, for the status chips (independent of the selected site).
const loadSitesStatus = async () => {
  try {
    sitesStatus.value = await Promise.all(sites.value.map(async (site) => {
      try {
        return { site, latest: await getLatestData(site.uid) };
      } catch (e) {
        return { site, latest: null };
      }
    }));
  } catch (e) {
    logger.error('Failed to load sites status:', e);
  }
};

const manualRefresh = async () => {
  isRefreshing.value = true;
  try {
    await Promise.all([
      loadMonitoringData(), loadLatestData(), loadDevices(),
      loadAlertRules(), loadStats(), loadSitesStatus(),
    ]);
  } finally {
    isRefreshing.value = false;
  }
};

// ── Follow-up of a breach (operator/admin) ──────────────────────
const openFollowup = (alertId) => {
  followupTarget.value = activeAlerts.value.find((alert) => alert.id === alertId) ?? null;
  followupOpen.value = Boolean(followupTarget.value);
};
const closeFollowup = () => {
  followupOpen.value = false;
  followupTarget.value = null;
};
const submitFollowup = async ({ note }) => {
  const target = followupTarget.value;
  if (!target || followupSaving.value) return;
  followupSaving.value = true;
  try {
    await followupAlert(target.id, note);
    toast.success('Catatan tindak lanjut tersimpan');
    closeFollowup();
    await loadStats();
  } catch (e) {
    logger.error('Failed to save alert follow-up:', e);
    toast.error(e?.response?.data?.detail || 'Gagal menyimpan tindak lanjut');
  } finally {
    followupSaving.value = false;
  }
};

// Trust the backend-computed status; fall back to deriving it from last_seen.
const getDeviceStatus      = d => d.status || getSensorStatus(d.last_seen);
const getDeviceStatusLabel = d => ({ online: 'Aktif', warning: 'Sleep', offline: 'Offline', unknown: 'Tidak diketahui' }[getDeviceStatus(d)] || 'Offline');

const showDeviceDetailModal = ref(false);
const selectedDevice        = ref(null);
const viewDeviceDetail      = d => { selectedDevice.value = d; showDeviceDetailModal.value = true; };
const closeDeviceDetailModal = () => { showDeviceDetailModal.value = false; selectedDevice.value = null; };

// ── Lifecycle ───────────────────────────────────────────────────
onMounted(async () => {
  if (typeof window !== 'undefined' && typeof window.matchMedia === 'function') {
    reducedMotionMediaQuery = window.matchMedia('(prefers-reduced-motion: reduce)');
    const updateReducedMotion = (event) => { reducedMotion.value = Boolean(event.matches); };
    updateReducedMotion(reducedMotionMediaQuery);
    if (typeof reducedMotionMediaQuery.addEventListener === 'function') {
      reducedMotionMediaQuery.addEventListener('change', updateReducedMotion);
      removeReducedMotionListener = () => reducedMotionMediaQuery?.removeEventListener('change', updateReducedMotion);
    } else if (typeof reducedMotionMediaQuery.addListener === 'function') {
      reducedMotionMediaQuery.addListener(updateReducedMotion);
      removeReducedMotionListener = () => reducedMotionMediaQuery?.removeListener(updateReducedMotion);
    }
  }
  await loadSites();
  const seq = ++siteLoadSeq;
  await Promise.all([loadLatestData(), loadDevices(), loadMonitoringData(), loadAlertRules(), loadStats()]);
  if (seq === siteLoadSeq) statsLoaded.value = true;
  loadSitesStatus();
  startTimeseriesPolling();
  refreshInterval = setInterval(() => {
    loadLatestData();
    loadStats();
    loadSitesStatus();
  }, 30000);
});

onUnmounted(() => {
  if (refreshInterval) clearInterval(refreshInterval);
  stopTimeseriesPolling();
  removeReducedMotionListener?.();
  removeReducedMotionListener = null;
  reducedMotionMediaQuery = null;
});
</script>

<style scoped>
.fade-enter-active, .fade-leave-active { transition: opacity 0.2s ease; }
.fade-enter-from, .fade-leave-to       { opacity: 0; }
</style>
