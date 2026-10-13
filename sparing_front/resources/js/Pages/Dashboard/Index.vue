<template>
  <AppLayout>

    <PageHeader
      :crumb="['Beranda', 'Dashboard']"
      title="Dashboard Pemantauan"
      :subtitle="currentSite ? `${currentSite.name} — ${currentSite.company_name}` : 'Pilih lokasi untuk memantau data'"
    >
      <template #actions>
        <div class="flex items-center gap-2 flex-wrap justify-end">
          <select
            v-model="selectedSiteUid"
            @change="onSiteChange"
            aria-label="Pilih lokasi pemantauan"
            class="px-3 py-1.5 border border-[#D7E0E1] rounded-lg text-sm focus:ring-2 focus:ring-primary focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary bg-white"
          >
            <option value="">-- Pilih Lokasi --</option>
            <option v-for="site in sites" :key="site.uid" :value="site.uid">
              {{ site.name }} — {{ site.company_name }}
            </option>
          </select>

          <div class="flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-semibold"
            :class="onlineDevices === totalDevices && totalDevices > 0
              ? 'bg-emerald-50 text-emerald-700'
              : totalDevices === 0 ? 'bg-slate-100 text-slate-500'
              : 'bg-amber-50 text-amber-700'"
          >
            <span class="w-1.5 h-1.5 rounded-full animate-pulse"
              :class="onlineDevices === totalDevices && totalDevices > 0
                ? 'bg-emerald-500'
                : totalDevices === 0 ? 'bg-slate-400' : 'bg-amber-500'"
            ></span>
            {{ onlineDevices }}/{{ totalDevices }} online
          </div>

          <router-link
            v-if="loggerTotal > 0"
            to="/loggers"
            class="flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-semibold transition-colors"
            :class="loggerDown === 0 ? 'bg-emerald-50 text-emerald-700 hover:bg-emerald-100'
              : 'bg-red-50 text-red-700 hover:bg-red-100'"
            :title="loggerDown === 0 ? 'Semua logger aktif' : `${loggerDown} logger mati`"
          >
            <i class="fas fa-hard-drive text-[11px]"></i>
            {{ loggerDown === 0 ? 'Logger aktif' : `${loggerDown} logger mati` }}
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

    <!-- ═══════════════════════════════════════════
         KPI Row
         ═══════════════════════════════════════════ -->
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3 mb-4 md:mb-5">
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

      <div class="bg-white border border-[#D7E0E1] rounded-lg p-4">
        <p class="text-[11px] text-[#617377] uppercase font-bold tracking-wide">Alarm Aktif</p>
        <p class="font-mono text-2xl text-ink mt-1">{{ activeAlertCountKpi }}</p>
        <p class="text-xs text-[#617377] mt-1">{{ alarmNote }}</p>
      </div>

      <div class="bg-white border border-[#D7E0E1] rounded-lg p-4">
        <p class="text-[11px] text-[#617377] uppercase font-bold tracking-wide">Kelengkapan Data Hari Ini</p>
        <p class="font-mono text-2xl text-ink mt-1">
          {{ completenessKpi ? formatNumber(completenessKpi.pct, 1) + '%' : '—' }}
        </p>
        <p class="text-xs text-[#617377] mt-1">{{ completenessNote }}</p>
      </div>
    </div>

    <!-- ═══════════════════════════════════════════
         Parameter Strip
         ═══════════════════════════════════════════ -->
    <div v-if="tileFields.length" class="grid gap-3 mb-4 md:mb-5"
      :style="{ gridTemplateColumns: `repeat(auto-fit, minmax(200px, 1fr))` }">
      <div
        v-for="field in tileFields"
        :key="field"
        class="bg-white border border-[#D7E0E1] rounded-lg p-3"
        :style="{ borderLeftColor: tileStatus(field)?.border || '#D7E0E1', borderLeftWidth: '3px' }"
      >
        <div class="flex items-center justify-between gap-1">
          <span class="text-[10px] font-bold text-[#617377] uppercase tracking-wide">{{ FIELD_LABELS[field] || field }}</span>
          <span v-if="tileStatus(field)" class="text-[10px] font-semibold" :class="tileStatus(field).text">
            {{ tileStatus(field).label }}
          </span>
        </div>
        <p class="font-mono text-lg text-ink mt-1">
          {{ formatNumber(tileCurrentValue(field), field === 'ph' || field === 'nh3n' ? 2 : 1) }}
          <span class="text-xs font-normal text-[#617377]">{{ getSensorUnit(field) }}</span>
        </p>
        <p class="text-[10px] text-[#617377] mt-0.5">{{ bakuMutuText(field) }}</p>
        <Sparkline :points="sparkPoints[field]" :threshold="dangerMax(field)" />
      </div>
    </div>

    <!-- ═══════════════════════════════════════════
         Status Table + Right Column
         ═══════════════════════════════════════════ -->
    <div class="grid lg:grid-cols-[2fr_1fr] gap-3 mb-4 md:mb-5">

      <!-- Status table over scoped sites -->
      <div class="bg-white border border-[#D7E0E1] rounded-lg p-4 overflow-x-auto">
        <h3 class="card-title mb-3">Status Stasiun</h3>
        <table class="w-full text-sm">
          <thead>
            <tr class="text-left text-[11px] text-[#617377] uppercase border-b border-[#D7E0E1]">
              <th class="py-2 pr-3 font-bold">Stasiun</th>
              <th class="py-2 pr-3 font-bold">Lokasi</th>
              <th class="py-2 pr-3 font-bold">Update</th>
              <th class="py-2 pr-3 font-bold">pH</th>
              <th class="py-2 pr-3 font-bold">TSS</th>
              <th class="py-2 pr-3 font-bold">Status</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in sitesStatus" :key="row.site.uid" class="border-b border-[#EEF2F3] last:border-0">
              <td class="py-2 pr-3 font-medium text-ink">{{ row.site.name }}</td>
              <td class="py-2 pr-3 text-[#617377]">{{ row.site.company_name }}</td>
              <td class="py-2 pr-3 text-[#617377]">{{ getRelativeTime(row.latest?.ts) }}</td>
              <td class="py-2 pr-3 font-mono">{{ formatNumber(row.latest?.ph, 2) }}</td>
              <td class="py-2 pr-3 font-mono">{{ formatNumber(row.latest?.tss, 1) }}</td>
              <td class="py-2 pr-3">
                <span class="text-[11px] font-semibold px-1.5 py-0.5 rounded" :class="rowStatusClass(row.status)">
                  {{ rowStatusLabel(row.status) }}
                </span>
              </td>
            </tr>
            <tr v-if="!sitesStatus.length">
              <td colspan="6" class="py-4 text-center text-[#617377] text-xs">Belum ada lokasi</td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Right column -->
      <div class="flex flex-col gap-3">
        <!-- Alarm aktif -->
        <div class="bg-white border border-[#D7E0E1] rounded-lg p-4">
          <div class="flex items-center justify-between mb-3">
            <h3 class="card-title">Alarm Aktif</h3>
            <router-link to="/alarms" class="text-xs text-primary hover:underline">Lihat semua</router-link>
          </div>
          <div v-if="activeAlertsTop.length" class="space-y-2">
            <div v-for="a in activeAlertsTop" :key="a.id" class="flex items-start gap-2 pl-2"
              :style="{ borderLeft: `3px solid ${a.threshold_type === 'danger' ? '#B03030' : '#9A6B00'}` }"
            >
              <div class="flex-1 min-w-0">
                <p class="text-xs font-semibold text-ink truncate">{{ FIELD_LABELS[a.field] || a.field }}</p>
                <p class="text-[11px] text-[#617377]">{{ getRelativeTime(a.triggered_at) }}</p>
              </div>
            </div>
          </div>
          <div v-else class="text-xs text-[#617377] py-4 text-center">Tidak ada alarm aktif</div>
        </div>

        <!-- Kelengkapan -->
        <div class="bg-white border border-[#D7E0E1] rounded-lg p-4">
          <h3 class="card-title mb-3">Kelengkapan Data</h3>
          <div class="h-[7px] rounded bg-[#E5EDED] overflow-hidden">
            <div class="h-full bg-primary rounded" :style="{ width: (completenessKpi?.pct ?? 0) + '%' }"></div>
          </div>
          <p class="text-xs text-[#617377] mt-2">{{ completenessNote || 'Memuat data...' }}</p>
        </div>
      </div>
    </div>

    <!-- ═══════════════════════════════════════════
         Main Trend Chart
         ═══════════════════════════════════════════ -->
    <div class="mb-4 rounded-lg border border-[#D7E0E1] bg-white p-4 md:mb-5 md:p-5">
      <div class="mb-3">
        <h2 class="card-title">Periode Pemantauan</h2>
        <p class="mt-0.5 text-xs text-[#617377]">Rentang yang sama digunakan untuk grafik, statistik, dan event.</p>
      </div>
      <PeriodFilter
        :model-value="timeseriesPreset"
        :custom-range="monitoringCustomRange"
        :timezone="monitoringTimezone"
        @update:model-value="selectMonitoringPeriod"
        @update:custom-range="updateMonitoringCustomRange"
        @apply-custom="applyMonitoringCustomRange"
      />
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
      />

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
         Device Table + Mini Map
         ═══════════════════════════════════════════ -->
    <div class="grid grid-cols-1 lg:grid-cols-3 gap-3">

      <!-- Device Table (2/3) -->
      <div class="lg:col-span-2">
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
      </div>

      <!-- Mini Map (1/3) -->
      <div class="bg-white border border-[#D7E0E1] rounded-lg p-4 flex flex-col">
        <div class="flex items-center gap-2 mb-3">
          <h3 class="card-title flex-1">Peta Lokasi</h3>
          <span class="ml-auto text-xs text-[#617377]">{{ sites.length }} site</span>
        </div>
        <div class="flex-1 min-h-[220px]">
          <SiteMap
            v-if="sites.length"
            :sites="sites"
            :active-site-uid="selectedSiteUid"
            height="100%"
            :zoom="10"
            @site-click="(site) => { selectedSiteUid = site.uid; onSiteChange(); }"
          />
          <div v-else class="h-full flex items-center justify-center text-[#617377] text-xs gap-2">
            <i class="fas fa-map-marked-alt text-xl"></i>
            <span>Belum ada lokasi</span>
          </div>
        </div>
      </div>
    </div>

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
import SiteMap from '@/Components/SiteMap.vue';
import StatusBadge from '@/Components/StatusBadge.vue';
import DataTable from '@/Components/DataTable.vue';
import Sparkline from '@/Components/Sparkline.vue';
import PeriodFilter from '@/Components/Dashboard/PeriodFilter.vue';
import MonitoringEventList from '@/Components/Dashboard/MonitoringEventList.vue';
import WaterQualityTrendChart from '@/Components/Dashboard/WaterQualityTrendChart.vue';
import DebitTrendChart from '@/Components/Dashboard/DebitTrendChart.vue';
import { useApi } from '@/Composables/useApi';
import { useDashboardTimeseries } from '@/Composables/useDashboardTimeseries';
import { useAuth } from '@/Composables/useAuth';
import { getRelativeTime, getSensorStatus, getSensorUnit, getThresholdStatus, formatNumber, parseUTC } from '@/Utils/helpers';
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
const loggerTotal        = ref(0);
const loggerDown         = ref(0);
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

const REAL_PARAMS = ['ph', 'tss', 'cod', 'nh3n', 'debit', 'temp'];
function hasMonitoringData(field) {
  if (finiteValue(monitoringSummary(field)?.current) !== null) return true;
  return (timeseriesSnapshot.value?.series?.[field]?.points || [])
    .some((point) => finiteValue(point?.value) !== null);
}

// Unfitted auxiliary sensors historically report a constant zero. Retain that
// filtering only for untouched fields; zero is always valid for pH/TSS/Debit.
function hasAuxiliaryData(field) {
  const series = auxiliaryChartData.value || [];
  if (series.some(d => d[field] != null && d[field] !== 0)) return true;
  const latest = latestData.value?.[field];
  return latest != null && latest !== 0;
}
const tileFields = computed(() => REAL_PARAMS.filter((field) => MONITORING_FIELDS.has(field)
  ? hasMonitoringData(field)
  : hasAuxiliaryData(field)));
const showElectrical = computed(() => hasAuxiliaryData('voltage') || hasAuxiliaryData('current'));

const sparkPoints = computed(() => {
  const map = {};
  ['ph', 'tss', 'cod', 'nh3n', 'debit', 'temp'].forEach(f => {
    map[f] = MONITORING_FIELDS.has(f)
      ? (timeseriesSnapshot.value?.series?.[f]?.points || []).slice(-30).map((point) => finiteValue(point?.value))
      : auxiliaryChartData.value.slice(-30).map(d => (d[f] != null ? d[f] : null));
  });
  return map;
});

function tileCurrentValue(field) {
  return MONITORING_FIELDS.has(field) ? monitoringSummary(field)?.current : latestData.value?.[field];
}

function responseThresholdValue(threshold, names) {
  for (const name of names) {
    const candidate = threshold?.[name];
    const value = finiteValue(typeof candidate === 'object' ? candidate?.value : candidate);
    if (value !== null) return value;
  }
  return null;
}

function dangerMax(field) {
  const rule = MONITORING_FIELDS.has(field)
    ? timeseriesSnapshot.value?.thresholds?.[field]
    : alertRulesByField.value[field];
  if (!rule) return null;
  return responseThresholdValue(rule, ['danger_max', 'upper', 'reference', 'warning_max']);
}

function bakuMutuText(field) {
  if (MONITORING_FIELDS.has(field)) {
    const threshold = timeseriesSnapshot.value?.thresholds?.[field];
    if (!threshold) return 'Ambang belum diatur';
    const minimum = responseThresholdValue(threshold, ['danger_min', 'lower', 'warning_min']);
    const maximum = responseThresholdValue(threshold, ['danger_max', 'upper', 'reference', 'warning_max']);
    if (minimum === null && maximum === null) return 'Ambang belum diatur';
    const unit = threshold.unit || getSensorUnit(field);
    if (minimum !== null && maximum !== null) return `Batas ${minimum}-${maximum}${unit ? ` ${unit}` : ''}`;
    return `${minimum !== null ? 'Min' : 'Maks'} ${minimum ?? maximum}${unit ? ` ${unit}` : ''}`;
  }
  const rule = alertRulesByField.value[field];
  if (!rule) return 'Ambang belum diatur';
  if (field === 'ph') {
    return `Batas ${rule.danger_min ?? '-'}–${rule.danger_max ?? '-'}`;
  }
  return `Maks ${rule.danger_max ?? '-'} ${getSensorUnit(field)}`;
}

// Same status priority as SensorCard: sensor bad > danger > warning > sensor-warn > ok.
function tileStatus(field) {
  const value = tileCurrentValue(field);
  if (value == null) return null;
  if (MONITORING_FIELDS.has(field)) {
    const summary = monitoringSummary(field) || {};
    const severity = summary.status_severity || ({ critical: 'critical', sensor_error: 'critical', warning: 'warning', no_flow: 'warning', normal: 'normal' }[summary.status] ?? 'normal');
    const presentation = {
      critical: { text: 'text-[#B03030]', border: '#B03030' },
      warning: { text: 'text-[#9A6B00]', border: '#9A6B00' },
      normal: { text: 'text-[#1F7A4D]', border: '#1F7A4D' },
    }[severity] || { text: 'text-[#617377]', border: '#617377' };
    return {
      key: summary.status || severity,
      label: summary.status_label || ({ no_flow: 'Aliran Terhenti', sensor_error: 'Cek Sensor', warning: 'Waspada', normal: 'Baik' }[summary.status] ?? 'Belum diketahui'),
      ...presentation,
    };
  }
  const health = sensorHealth.value[field];
  const c = getThresholdStatus(field, value);
  if (health?.status === 'bad')     return { key: 'sensor_bad', label: 'Cek Sensor', text: 'text-[#B03030]', border: '#B03030' };
  if (c === 'danger')               return { key: 'danger',     label: 'Bahaya',     text: 'text-[#B03030]', border: '#B03030' };
  if (c === 'warning')              return { key: 'warning',    label: 'Waspada',    text: 'text-[#9A6B00]', border: '#9A6B00' };
  if (health?.status === 'warning') return { key: 'sensor_warn',label: 'Cek Sensor', text: 'text-[#9A6B00]', border: '#9A6B00' };
  return { key: 'ok', label: 'Baik', text: 'text-[#1F7A4D]', border: '#1F7A4D' };
}

function rowStatusFromLatest(d) {
  if (!d) return 'nodata';
  const statuses = ['ph', 'tss', 'cod', 'nh3n']
    .filter(f => d[f] != null)
    .map(f => getThresholdStatus(f, d[f]));
  if (!statuses.length) return 'nodata';
  if (statuses.includes('danger')) return 'danger';
  if (statuses.includes('warning')) return 'warning';
  return 'normal';
}

function rowStatusClass(status) {
  return {
    danger: 'bg-[#F7E4E4] text-[#B03030]',
    warning: 'bg-[#F7EFD9] text-[#9A6B00]',
    normal: 'bg-[#E6F2EC] text-[#1F7A4D]',
    nodata: 'bg-[#EAEEEF] text-[#617377]',
  }[status] || 'bg-[#EAEEEF] text-[#617377]';
}

function rowStatusLabel(status) {
  return { danger: 'Bahaya', warning: 'Waspada', normal: 'Baik', nodata: 'Belum ada data' }[status] || 'Belum ada data';
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
    loggerTotal.value = list.length;
    loggerDown.value = list.filter((r) => r.state === 'down').length;
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

// Status table over every scoped site (independent of the chart's selected site).
const loadSitesStatus = async () => {
  try {
    sitesStatus.value = await Promise.all(sites.value.map(async (site) => {
      try {
        const d = await getLatestData(site.uid);
        return { site, latest: d, status: rowStatusFromLatest(d) };
      } catch (e) {
        return { site, latest: null, status: 'nodata' };
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
