<template>
  <AppLayout>

    <PageHeader
      :crumb="['Beranda', 'Dashboard']"
      title="Dashboard Pemantauan"
      :subtitle="currentSite ? `${currentSite.name} — ${currentSite.company_name}` : 'Pilih lokasi untuk memantau data'"
    >
      <template #actions>
        <div class="flex min-w-0 max-w-full flex-wrap items-center justify-end gap-2">
          <router-link
            v-if="currentLoggerState"
            to="/loggers"
            class="flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-semibold transition-colors"
            :class="currentLoggerState === 'down'
              ? 'bg-red-50 text-red-700 hover:bg-red-100'
              : 'bg-emerald-50 text-emerald-700 hover:bg-emerald-100'"
          >
            <i class="fas fa-hard-drive text-[11px]"></i>
            {{ currentLoggerState === 'down' ? 'Logger mati' : 'Logger hidup' }}
          </router-link>

          <div class="flex items-center gap-2 text-xs text-[#617377]">
            <i class="fas fa-clock"></i>
            <span>{{ lastUpdatedText }}</span>
          </div>

          <button
            @click="manualRefresh"
            :disabled="isRefreshing || timeseriesIsRefreshing"
            class="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium text-[#617377] hover:bg-[#EEF2F3] transition-colors disabled:opacity-50"
          >
            <i class="fas fa-sync-alt text-xs" :class="{ 'animate-spin': isRefreshing || timeseriesIsRefreshing }"></i>
            Refresh
          </button>
        </div>
      </template>
    </PageHeader>

    <SiteStatusChips :chips="siteChips" :model-value="selectedSiteUid" @update:model-value="selectSite" />

    <!-- ═══════════════════════════════════════════
         KPI Row
         ═══════════════════════════════════════════ -->
    <div class="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-4 md:mb-5">
      <div class="bg-white border border-[#D7E0E1] rounded-lg p-4">
        <p class="text-[11px] text-[#617377] uppercase font-bold tracking-wide">Perangkat Online</p>
        <p class="font-mono text-2xl text-ink mt-1">{{ onlineDevices }} / {{ totalDevices }}</p>
        <p class="text-xs text-[#617377] mt-1">Perangkat aktif saat ini</p>
      </div>

      <div class="bg-white border border-[#D7E0E1] rounded-lg p-4">
        <p class="text-[11px] text-[#617377] uppercase font-bold tracking-wide">Kepatuhan Baku Mutu (30 hr)</p>
        <p class="font-mono text-2xl text-ink mt-1">
          {{ complianceKpi ? formatNumber(complianceKpi.compliance_pct, 1) + '%' : '—' }}
        </p>
        <p class="text-xs mt-1" :class="complianceNoteClass">{{ complianceNote }}</p>
      </div>

      <router-link to="/alarms" class="block bg-white border border-[#D7E0E1] rounded-lg p-4 hover:border-primary transition-colors">
        <p class="text-[11px] text-[#617377] uppercase font-bold tracking-wide">Alarm Aktif</p>
        <p class="font-mono text-2xl text-ink mt-1">{{ activeAlertCountKpi }}</p>
        <p class="text-xs text-[#617377] mt-1">{{ alarmNote }}</p>
      </router-link>

      <div class="bg-white border border-[#D7E0E1] rounded-lg p-4">
        <p class="text-[11px] text-[#617377] uppercase font-bold tracking-wide">Kelengkapan Data Hari Ini</p>
        <p class="font-mono text-2xl text-ink mt-1">
          {{ completenessKpi ? formatNumber(completenessKpi.pct, 1) + '%' : '—' }}
        </p>
        <div class="h-[6px] rounded bg-[#E5EDED] overflow-hidden mt-2">
          <div class="h-full bg-primary rounded" :style="{ width: (completenessKpi?.pct ?? 0) + '%' }"></div>
        </div>
        <p class="text-xs text-[#617377] mt-1">{{ completenessNote }}</p>
      </div>
    </div>

    <!-- ═══════════════════════════════════════════
         Period filter — drives charts, statistics and events below
         ═══════════════════════════════════════════ -->
    <div class="mb-3 flex flex-col gap-1 sm:flex-row sm:items-center sm:gap-3">
      <h2 class="card-title shrink-0">Periode</h2>
      <div class="min-w-0 flex-1">
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

    <!-- ═══════════════════════════════════════════
         Coherent monitoring charts + event detail
         ═══════════════════════════════════════════ -->
    <div class="mb-4 space-y-3 md:mb-5">
      <WaterQualityTrendChart
        :snapshot="monitoringDisplaySnapshot"
        :state="timeseriesState"
        :stale="timeseriesIsStale"
        :focused-event-id="focusedEventId"
        :reduced-motion="reducedMotion"
        @retry="retryMonitoring"
      >
        <!-- Other water-quality readings sit with the pH/TSS summaries, not in a separate section. -->
        <template #extra>
          <section v-if="extraFields.length" class="mb-4 flex min-w-0 flex-wrap items-center gap-2" aria-label="Parameter lain">
            <p class="mr-1 text-xs font-semibold uppercase tracking-wide text-slate-500">Parameter lain</p>
            <ul class="flex min-w-0 flex-wrap gap-2">
              <li
                v-for="field in extraFields"
                :key="field"
                class="flex min-w-0 items-center gap-3 rounded-md border border-slate-200 bg-[#F7FAFA] px-3 py-2"
                :style="{ borderLeft: `3px solid ${tileStatus(field)?.border || '#D7E0E1'}` }"
              >
                <div class="min-w-0">
                  <p class="text-[11px] font-bold uppercase tracking-wide text-[#617377]">{{ FIELD_LABELS[field] || field }}</p>
                  <p class="font-mono text-base text-ink">
                    {{ formatNumber(latestData?.[field], field === 'nh3n' ? 2 : 1) }}
                    <span class="text-xs font-normal text-[#617377]">{{ getSensorUnit(field) }}</span>
                  </p>
                  <p class="text-[10.5px] text-[#617377]">
                    <span v-if="tileStatus(field)" class="font-semibold" :class="tileStatus(field).text">{{ tileStatus(field).label }}</span>
                    · {{ bakuMutuText(field) }}
                  </p>
                </div>
                <div class="ml-auto w-24 shrink-0">
                  <Sparkline :points="sparkPoints[field]" :threshold="dangerMax(field)" />
                </div>
              </li>
            </ul>
          </section>
        </template>
      </WaterQualityTrendChart>

      <div class="grid grid-cols-1 gap-3 lg:grid-cols-[minmax(0,2fr)_minmax(18rem,1fr)]">
        <DebitTrendChart
          :snapshot="monitoringDisplaySnapshot"
          :state="timeseriesState"
          :stale="timeseriesIsStale"
          :focused-event-id="focusedEventId"
          :reduced-motion="reducedMotion"
          @retry="retryMonitoring"
        />
        <MonitoringEventList
          :events="monitoringEvents"
          :event-total="monitoringEventTotal"
          :timezone="monitoringTimezone"
          @focus-event="focusMonitoringEvent"
        />
      </div>
    </div>

    <div v-if="showElectrical" class="grid grid-cols-1 gap-3 mb-4 md:mb-5">
      <!-- Electrical -->
      <div class="bg-white border border-[#D7E0E1] rounded-lg p-4 md:p-6">
        <h3 class="card-title mb-1">Parameter Kelistrikan</h3>
        <p class="text-xs text-[#617377] mb-4">Tegangan & Arus</p>
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
    </div>

    <!-- ═══════════════════════════════════════════
         Device Table
         ═══════════════════════════════════════════ -->
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
              <div><p class="text-xs text-slate-500 mb-0.5">Model</p><p class="font-medium text-slate-800">{{ selectedDevice.model || '-' }}</p></div>
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
import Sparkline from '@/Components/Sparkline.vue';
import PeriodFilter from '@/Components/Dashboard/PeriodFilter.vue';
import MonitoringEventList from '@/Components/Dashboard/MonitoringEventList.vue';
import WaterQualityTrendChart from '@/Components/Dashboard/WaterQualityTrendChart.vue';
import DebitTrendChart from '@/Components/Dashboard/DebitTrendChart.vue';
import SiteStatusChips from '@/Components/Dashboard/SiteStatusChips.vue';
import { useApi } from '@/Composables/useApi';
import { useDashboardTimeseries } from '@/Composables/useDashboardTimeseries';
import { useAuth } from '@/Composables/useAuth';
import { getRelativeTime, getSensorStatus, getSensorUnit, getThresholdStatus, formatNumber, parseUTC } from '@/Utils/helpers';
import { buildSiteChips } from '@/Utils/siteStatus.js';
import logger from '@/Utils/logger';

const apexchart = VueApexCharts;

const colors = {
  voltage: '#f59e0b',
  current: '#ef4444',
};

const FIELD_LABELS = {
  ph: 'pH', tss: 'TSS', cod: 'COD', nh3n: 'NH3-N', temp: 'Temperatur',
  debit: 'Debit Air', noise: 'Kebisingan', pm25: 'PM2.5', pm10: 'PM10',
  device_offline: 'Perangkat Offline',
};

const {
  getLatestData, getData, getDevices, getSites, getSensorHealth,
  getCompliance, getCompleteness, getAlertCount, getAlerts, getAlertRules, getLoggerStatus,
  getDashboardTimeseries,
} = useApi();
const { filterSitesByUser } = useAuth();

// ── State ──────────────────────────────────────────────────────
const latestData      = ref(null);
const devices         = ref([]);
const devicesLoading  = ref(false);
const sites           = ref([]);
const currentSite     = ref(null);
const selectedSiteUid = ref('');
const auxiliaryChartData = ref([]);
const sensorHealth    = ref({});  // map: field -> health object
const isRefreshing    = ref(false);
const focusedEventId  = ref(null);
const monitoringCustomRange = ref({ dateFrom: null, dateTo: null });
const reducedMotion = ref(false);
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

// v2 additions
const complianceKpi      = ref(null);
const completenessKpi    = ref(null);
const activeAlertCountKpi = ref(0);
const activeAlertsTop    = ref([]);
const alertRulesByField  = ref({});
const loggerStates       = ref({});  // map: site_uid -> 'alive' | 'down'
const sitesStatus        = ref([]);

let refreshInterval = null;

// ── Computed ────────────────────────────────────────────────────
const onlineDevices  = computed(() => devices.value.filter(d => getDeviceStatus(d) === 'online').length);
const totalDevices   = computed(() => devices.value.length);

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
const finiteValue = (value) => typeof value === 'number' && Number.isFinite(value) ? value : null;

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

// pH, TSS and Debit live in the trend charts; only these get a small tile.
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

const siteChips = computed(() => buildSiteChips(
  sitesStatus.value.length ? sitesStatus.value : sites.value.map((site) => ({ site, latest: null })),
  loggerStates.value,
));
// null = this site has no logger telemetry yet → the header chip is hidden.
const currentLoggerState = computed(() => loggerStates.value[selectedSiteUid.value] ?? null);

function responseThresholdValue(threshold, names) {
  for (const name of names) {
    const candidate = threshold?.[name];
    const value = finiteValue(typeof candidate === 'object' ? candidate?.value : candidate);
    if (value !== null) return value;
  }
  return null;
}

function dangerMax(field) {
  const rule = alertRulesByField.value[field];
  return rule ? responseThresholdValue(rule, ['danger_max', 'upper', 'reference', 'warning_max']) : null;
}

function bakuMutuText(field) {
  const rule = alertRulesByField.value[field];
  if (!rule) return 'Ambang belum diatur';
  return `Maks ${rule.danger_max ?? '-'} ${getSensorUnit(field)}`;
}

// Same status priority as SensorCard: sensor bad > danger > warning > sensor-warn > ok.
function tileStatus(field) {
  const value = latestData.value?.[field];
  if (value == null) return null;
  const health = sensorHealth.value[field];
  const c = getThresholdStatus(field, value);
  if (health?.status === 'bad')     return { label: 'Cek Sensor', text: 'text-[#B03030]', border: '#B03030' };
  if (c === 'danger')               return { label: 'Bahaya',     text: 'text-[#B03030]', border: '#B03030' };
  if (c === 'warning')              return { label: 'Waspada',    text: 'text-[#9A6B00]', border: '#9A6B00' };
  if (health?.status === 'warning') return { label: 'Cek Sensor', text: 'text-[#9A6B00]', border: '#9A6B00' };
  return { label: 'Baik', text: 'text-[#1F7A4D]', border: '#1F7A4D' };
}

const complianceNote = computed(() => {
  const delta = complianceKpi.value?.delta_pct;
  if (delta == null) return complianceKpi.value ? 'Tidak ada data pembanding' : 'Memuat data...';
  const pct = formatNumber(Math.abs(delta), 1);
  return delta >= 0 ? `Naik ${pct}%` : `Turun ${pct}%`;
});

const complianceNoteClass = computed(() => {
  const delta = complianceKpi.value?.delta_pct;
  if (delta == null) return 'text-[#617377]';
  return delta >= 0 ? 'text-[#1F7A4D]' : 'text-[#B03030]';
});

const alarmNote = computed(() => {
  const a = activeAlertsTop.value[0];
  if (!a) return 'Tidak ada alarm aktif';
  const label = FIELD_LABELS[a.field] || a.field;
  return `${label} — ${a.threshold_type === 'danger' ? 'Bahaya' : 'Peringatan'}`;
});

const completenessNote = computed(() => {
  if (!completenessKpi.value) return '';
  return `${completenessKpi.value.actual} dari ${completenessKpi.value.expected} record`;
});

// Device table columns
const deviceColumns = [
  { key: 'id',          label: 'ID',      format: v => `#IOT-${String(v).padStart(3, '0')}` },
  { key: 'name',        label: 'Nama' },
  { key: 'model',       label: 'Model' },
  { key: 'last_seen',   label: 'Terakhir Update' },
  { key: 'status',      label: 'Status' },
  { key: 'actions',     label: 'Aksi' },
];

// ── Auxiliary electrical chart ─────────────────────────────────
const electricalOptions = computed(() => ({
  chart: { type: 'line', toolbar: { show: false }, zoom: { enabled: false }, animations: { enabled: true, speed: 800 }, fontFamily: 'Inter, sans-serif' },
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
  const selected = sites.value.find(s => s.uid === selectedSiteUid.value);
  currentSite.value = selected || null;
  focusedEventId.value = null;
  if (!selected) {
    await loadTimeseries();
    return;
  }
  await Promise.all([loadLatestData(), loadDevices(), loadMonitoringData(), loadSensorHealth(), loadAlertRules(), loadStats()]);
};

const selectSite = (uid) => {
  selectedSiteUid.value = uid;
  onSiteChange();
};

const loadLatestData = async () => {
  if (!currentSite.value) return;
  try {
    latestData.value = await getLatestData(currentSite.value.uid);
  } catch (e) {
    logger.error('Failed to load latest data:', e);
  }
};

const loadSensorHealth = async () => {
  if (!currentSite.value) return;
  try {
    const list = await getSensorHealth(currentSite.value.uid);
    const map = {};
    (Array.isArray(list) ? list : []).forEach(h => { map[h.field] = h; });
    sensorHealth.value = map;
  } catch (e) {
    logger.error('Failed to load sensor health:', e);
    sensorHealth.value = {};
  }
};

const loadDevices = async () => {
  if (!currentSite.value) return;
  devicesLoading.value = true;
  try {
    const response = await getDevices({ site_uid: currentSite.value.uid });
    let list = response?.items || (Array.isArray(response) ? response : response?.data || []);
    // Backend now supplies real last_seen + status per device.
    devices.value = list.filter(d => d.is_active !== false);
  } catch (e) {
    devices.value = [];
  } finally {
    devicesLoading.value = false;
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
  if (!currentSite.value) return;
  try {
    const list = await getAlertRules(currentSite.value.uid);
    const map = {};
    (Array.isArray(list) ? list : []).forEach(r => { map[r.field] = r; });
    alertRulesByField.value = map;
  } catch (e) {
    logger.error('Failed to load alert rules:', e);
    alertRulesByField.value = {};
  }
};

// v2 KPI stats — scoped to the selected site (fleet-wide when none is
// picked). Each call is independent so one failing endpoint never blanks
// the rest of the dashboard.
// Today 00:00 WIB (UTC+7) expressed as a UTC ISO instant — the start of the
// "Kelengkapan Data Hari Ini" window (target stays the full-day 720).
const todayMidnightWibISO = () => {
  const now = new Date();
  const wib = new Date(now.getTime() + 7 * 3600 * 1000);       // WIB wall clock
  const wall = Date.UTC(wib.getUTCFullYear(), wib.getUTCMonth(), wib.getUTCDate(), 0, 0, 0);
  return new Date(wall - 7 * 3600 * 1000).toISOString();       // back to real UTC
};

const loadStats = async () => {
  const siteUid = selectedSiteUid.value || null;
  try {
    complianceKpi.value = await getCompliance(30, siteUid);
  } catch (e) {
    logger.error('Failed to load compliance stats:', e);
  }
  try {
    completenessKpi.value = await getCompleteness(24, siteUid, todayMidnightWibISO());
  } catch (e) {
    logger.error('Failed to load completeness stats:', e);
  }
  try {
    const res = await getAlertCount('active', siteUid);
    activeAlertCountKpi.value = res?.count ?? 0;
  } catch (e) {
    logger.error('Failed to load alert count:', e);
  }
  try {
    const rows = await getLoggerStatus();
    const list = Array.isArray(rows) ? rows : (rows?.items || []);
    loggerStates.value = Object.fromEntries(list.filter((r) => r.site_uid).map((r) => [r.site_uid, r.state]));
  } catch (e) {
    logger.error('Failed to load logger status:', e);
  }
  try {
    const list = await getAlerts({ status: 'active', ...(siteUid ? { site_uid: siteUid } : {}) });
    const items = Array.isArray(list) ? list : (list?.items || []);
    activeAlertsTop.value = items.slice(0, 3);
  } catch (e) {
    logger.error('Failed to load active alerts:', e);
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
      loadMonitoringData(), loadLatestData(), loadDevices(), loadSensorHealth(),
      loadAlertRules(), loadStats(), loadSitesStatus(),
    ]);
  } finally {
    isRefreshing.value = false;
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
  await Promise.all([loadLatestData(), loadDevices(), loadMonitoringData(), loadSensorHealth(), loadAlertRules(), loadStats()]);
  loadSitesStatus();
  startTimeseriesPolling();
  refreshInterval = setInterval(() => {
    loadLatestData();
    loadSensorHealth();
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
