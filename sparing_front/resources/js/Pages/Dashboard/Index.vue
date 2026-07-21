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
            class="px-3 py-1.5 border border-[#D7E0E1] rounded-lg text-sm focus:ring-2 focus:ring-primary bg-white"
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
            :disabled="isRefreshing"
            class="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium text-[#617377] hover:bg-[#EEF2F3] transition-colors disabled:opacity-50"
          >
            <i class="fas fa-sync-alt text-xs" :class="{ 'animate-spin': isRefreshing }"></i>
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
    <div v-if="tileFields.length" class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3 mb-4 md:mb-5">
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
          {{ formatNumber(latestData[field], field === 'ph' || field === 'nh3n' ? 2 : 1) }}
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
    <div class="bg-white border border-[#D7E0E1] rounded-lg p-4 md:p-6 mb-4 md:mb-5">
      <div class="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-2 mb-4">
        <div>
          <h3 class="card-title">Tren Parameter Air Limbah</h3>
          <p class="text-xs text-[#617377] mt-0.5">Kualitas air real-time</p>
        </div>
        <select
          v-model="chartPeriod"
          @change="loadChartData"
          class="px-3 py-1.5 border border-[#D7E0E1] rounded-lg text-xs focus:ring-2 focus:ring-primary bg-white"
        >
          <option value="today">Hari Ini</option>
          <option value="week">Minggu Ini</option>
          <option value="month">Bulan Ini</option>
        </select>
      </div>
      <div class="h-60 md:h-72">
        <apexchart
          v-if="chartOptions"
          type="area"
          height="100%"
          :options="chartOptions"
          :series="chartSeries"
        />
        <div v-else class="h-full flex items-center justify-center text-[#617377] text-sm">
          <i class="fas fa-chart-area mr-2"></i> Pilih lokasi untuk melihat data
        </div>
      </div>
    </div>

    <!-- ═══════════════════════════════════════════
         Secondary Charts (only rendered when at least one has real data;
         collapses to a single column instead of leaving a blank half)
         ═══════════════════════════════════════════ -->
    <div
      v-if="secondaryChartsCount > 0"
      class="grid gap-3 mb-4 md:mb-5"
      :class="secondaryChartsCount > 1 ? 'grid-cols-1 md:grid-cols-2' : 'grid-cols-1'"
    >
      <!-- Electrical -->
      <div v-if="showElectrical" class="bg-white border border-[#D7E0E1] rounded-lg p-4 md:p-6">
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

      <!-- Debit (& Temp when it has real data) -->
      <div v-if="showDebitCard" class="bg-white border border-[#D7E0E1] rounded-lg p-4 md:p-6">
        <h3 class="card-title mb-1">{{ debitCardTitle }}</h3>
        <p class="text-xs text-[#617377] mb-4">{{ debitCardSubtitle }}</p>
        <div class="h-52 md:h-60">
          <apexchart
            v-if="debitTempOptions"
            type="area"
            height="100%"
            :options="debitTempOptions"
            :series="debitTempSeries"
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
import { ref, onMounted, onUnmounted, computed } from 'vue';
import VueApexCharts from 'vue3-apexcharts';
import AppLayout from '@/Layouts/AppLayout.vue';
import PageHeader from '@/Components/PageHeader.vue';
import SiteMap from '@/Components/SiteMap.vue';
import StatusBadge from '@/Components/StatusBadge.vue';
import DataTable from '@/Components/DataTable.vue';
import Sparkline from '@/Components/Sparkline.vue';
import { useApi } from '@/Composables/useApi';
import { useAuth } from '@/Composables/useAuth';
import { getRelativeTime, getSensorStatus, getSensorUnit, getThresholdStatus, formatNumber, parseUTC } from '@/Utils/helpers';
import logger from '@/Utils/logger';

const apexchart = VueApexCharts;

const colors = {
  ph: '#1e40af',
  tss: '#0ea5e9',
  cod: '#6366f1',
  nh3n: '#10b981',
  debit: '#0891b2',
  voltage: '#f59e0b',
  current: '#ef4444',
  temp: '#f97316',
};

const FIELD_LABELS = {
  ph: 'pH', tss: 'TSS', cod: 'COD', nh3n: 'NH3-N', temp: 'Temperatur',
  debit: 'Debit Air', noise: 'Kebisingan', pm25: 'PM2.5', pm10: 'PM10',
  device_offline: 'Perangkat Offline',
};

const {
  getLatestData, getData, getDevices, getSites, getSensorHealth,
  getCompliance, getCompleteness, getAlertCount, getAlerts, getAlertRules, getLoggerStatus,
} = useApi();
const { filterSitesByUser } = useAuth();

// ── State ──────────────────────────────────────────────────────
const latestData      = ref(null);
const previousData    = ref(null);
const chartPeriod     = ref('today');
const devices         = ref([]);
const devicesLoading  = ref(false);
const sites           = ref([]);
const currentSite     = ref(null);
const selectedSiteUid = ref('');
const chartData       = ref([]);
const sensorHealth    = ref({});  // map: field -> health object
const lastUpdated     = ref(null);
const isRefreshing    = ref(false);

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

const lastUpdatedText = computed(() => {
  if (!lastUpdated.value) return 'Belum diperbarui';
  return `Diperbarui ${getRelativeTime(lastUpdated.value)}`;
});

const siteTz = computed(() => currentSite.value?.timezone || 'Asia/Jakarta');

// Parameters shown as tiles / charts: only those with at least one real
// (non-null AND non-zero) reading in the recent series or the latest reading.
// Unfitted sensors on the live logger (NH3-N, Temp, Voltage, Current) send a
// constant 0/null, which must be treated as "no data", not just null.
const REAL_PARAMS = ['ph', 'tss', 'cod', 'nh3n', 'debit', 'temp'];
function hasRealData(field) {
  const series = (chartData.value || []);
  if (series.some(d => d[field] != null && d[field] !== 0)) return true;
  const latest = latestData.value?.[field];
  return latest != null && latest !== 0;
}
const tileFields = computed(() => REAL_PARAMS.filter(hasRealData));

// Secondary-chart visibility, computed once so both the template and chart
// series/options stay consistent.
const showElectrical = computed(() => hasRealData('voltage') || hasRealData('current'));
const showDebitCard  = computed(() => hasRealData('debit'));
const showTempSeries = computed(() => hasRealData('temp'));
const secondaryChartsCount = computed(() => (showElectrical.value ? 1 : 0) + (showDebitCard.value ? 1 : 0));

// Sparkline series reuse the trend-chart's already-loaded data (no extra calls).
const sparkPoints = computed(() => {
  const map = {};
  ['ph', 'tss', 'cod', 'nh3n', 'debit', 'temp'].forEach(f => {
    map[f] = chartData.value.slice(-30).map(d => (d[f] != null ? d[f] : null));
  });
  return map;
});

function dangerMax(field) {
  const rule = alertRulesByField.value[field];
  if (!rule) return null;
  return rule.danger_max ?? null;
}

function bakuMutuText(field) {
  const rule = alertRulesByField.value[field];
  if (!rule) return 'Ambang belum diatur';
  if (field === 'ph') {
    return `Batas ${rule.danger_min ?? '-'}–${rule.danger_max ?? '-'}`;
  }
  return `Maks ${rule.danger_max ?? '-'} ${getSensorUnit(field)}`;
}

// Same status priority as SensorCard: sensor bad > danger > warning > sensor-warn > ok.
function tileStatus(field) {
  const value = latestData.value?.[field];
  if (value == null) return null;
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

// ── Chart options ───────────────────────────────────────────────
const chartOptions = computed(() => ({
  chart: {
    type: 'area',
    toolbar: { show: false },
    zoom: { enabled: false },
    animations: { enabled: true, easing: 'easeinout', speed: 800 },
    fontFamily: 'Inter, sans-serif',
  },
  colors: [colors.ph, colors.tss, colors.cod, colors.nh3n],
  dataLabels: { enabled: false },
  stroke: { curve: 'smooth', width: 2 },
  fill: {
    type: 'gradient',
    gradient: { shadeIntensity: 1, opacityFrom: 0.35, opacityTo: 0.05, stops: [0, 90, 100] },
  },
  xaxis: {
    type: 'datetime',
    labels: {
      style: { colors: '#94a3b8', fontSize: '10px' },
      formatter: (val) => new Date(val).toLocaleTimeString('id-ID', { timeZone: siteTz.value, hour: '2-digit', minute: '2-digit' }),
    },
    axisBorder: { show: false },
    axisTicks: { show: false },
  },
  // pH (unitless, 0–14) and the mg/L parameters live on separate axes so their
  // very different scales don't distort each other. TSS/COD/NH3-N share the
  // right-hand mg/L axis via a common seriesName.
  yaxis: [
    {
      seriesName: 'pH', min: 0, max: 14, tickAmount: 7,
      title: { text: 'pH', style: { color: colors.ph, fontSize: '10px', fontWeight: 600 } },
      labels: { style: { colors: '#94a3b8', fontSize: '10px' } },
      axisBorder: { show: false }, axisTicks: { show: false },
    },
    {
      seriesName: 'TSS', opposite: true, min: 0,
      title: { text: 'mg/L', style: { color: '#94a3b8', fontSize: '10px', fontWeight: 600 } },
      labels: { style: { colors: '#94a3b8', fontSize: '10px' } },
      axisBorder: { show: false }, axisTicks: { show: false },
    },
    { seriesName: 'TSS', opposite: true, show: false },
    { seriesName: 'TSS', opposite: true, show: false },
  ],
  tooltip: {
    x: {
      formatter: (val) => new Date(val).toLocaleString('id-ID', { timeZone: siteTz.value, day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' }),
    },
    theme: 'light',
  },
  legend: { position: 'top', horizontalAlign: 'left', fontSize: '11px', markers: { radius: 12 } },
  grid: { borderColor: '#f1f5f9', strokeDashArray: 4 },
}));

const chartSeries = computed(() => [
  { name: 'pH',    data: chartData.value.map(d => ({ x: parseUTC(d.ts), y: d.ph })) },
  { name: 'TSS',   data: chartData.value.map(d => ({ x: parseUTC(d.ts), y: d.tss })) },
  { name: 'COD',   data: chartData.value.map(d => ({ x: parseUTC(d.ts), y: d.cod })) },
  { name: 'NH3-N', data: chartData.value.map(d => ({ x: parseUTC(d.ts), y: d.nh3n })) },
]);

const electricalOptions = computed(() => ({
  chart: { type: 'line', toolbar: { show: false }, zoom: { enabled: false }, animations: { enabled: true, speed: 800 }, fontFamily: 'Inter, sans-serif' },
  colors: [colors.voltage, colors.current],
  dataLabels: { enabled: false },
  stroke: { curve: 'smooth', width: 2.5 },
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
  { name: 'Voltage', data: chartData.value.map(d => ({ x: parseUTC(d.ts), y: d.voltage })) },
  { name: 'Current', data: chartData.value.map(d => ({ x: parseUTC(d.ts), y: d.current })) },
]);

// Temperature is dropped entirely (series + axis) when it has no real data,
// leaving a clean single-series Debit chart instead of a flat-zero line.
const debitTempOptions = computed(() => ({
  chart: { type: 'area', toolbar: { show: false }, zoom: { enabled: false }, animations: { enabled: true, speed: 800 }, fontFamily: 'Inter, sans-serif' },
  colors: showTempSeries.value ? [colors.debit, colors.temp] : [colors.debit],
  dataLabels: { enabled: false },
  stroke: { curve: 'smooth', width: 2 },
  fill: { type: 'gradient', gradient: { opacityFrom: 0.35, opacityTo: 0.05 } },
  xaxis: {
    type: 'datetime',
    labels: {
      style: { colors: '#94a3b8', fontSize: '10px' },
      formatter: (val) => new Date(val).toLocaleTimeString('id-ID', { timeZone: siteTz.value, hour: '2-digit', minute: '2-digit' }),
    },
    axisBorder: { show: false },
    axisTicks: { show: false },
  },
  yaxis: showTempSeries.value ? [
    { title: { text: 'L/min', style: { fontSize: '11px' } }, labels: { style: { colors: '#94a3b8', fontSize: '10px' } } },
    { opposite: true, title: { text: '°C', style: { fontSize: '11px' } }, labels: { style: { colors: '#94a3b8', fontSize: '10px' } } },
  ] : [
    { title: { text: 'L/min', style: { fontSize: '11px' } }, labels: { style: { colors: '#94a3b8', fontSize: '10px' } } },
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

const debitTempSeries = computed(() => {
  const series = [{ name: 'Debit', data: chartData.value.map(d => ({ x: parseUTC(d.ts), y: d.debit })) }];
  if (showTempSeries.value) {
    series.push({ name: 'Temperature', data: chartData.value.map(d => ({ x: parseUTC(d.ts), y: d.temp })) });
  }
  return series;
});

const debitCardTitle = computed(() => showTempSeries.value ? 'Debit & Temperatur' : 'Debit');
const debitCardSubtitle = computed(() => showTempSeries.value ? 'Laju alir & suhu air' : 'Laju alir air');

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
  if (selected) {
    currentSite.value = selected;
    await Promise.all([loadLatestData(), loadDevices(), loadChartData(), loadSensorHealth(), loadAlertRules(), loadStats()]);
  }
};

const loadLatestData = async () => {
  if (!currentSite.value) return;
  try {
    if (latestData.value) previousData.value = { ...latestData.value };
    latestData.value = await getLatestData(currentSite.value.uid);
    lastUpdated.value = new Date();
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

const loadChartData = async () => {
  if (!currentSite.value) return;
  try {
    const now = new Date();
    let dateFrom;
    if (chartPeriod.value === 'today')  dateFrom = new Date(now.setHours(0, 0, 0, 0));
    else if (chartPeriod.value === 'week') dateFrom = new Date(now.setDate(now.getDate() - 7));
    else dateFrom = new Date(now.setMonth(now.getMonth() - 1));

    const response = await getData({
      site_uid: currentSite.value.uid,
      date_from: dateFrom.toISOString(),
      fields: 'ph,tss,cod,nh3n,debit,voltage,current,temp',
      per_page: 100,
      order: 'asc',
    });
    chartData.value = response?.items || (Array.isArray(response) ? response : []);
  } catch (e) {
    logger.error('Failed to load chart data:', e);
  }
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
const loadStats = async () => {
  const siteUid = selectedSiteUid.value || null;
  try {
    complianceKpi.value = await getCompliance(30, siteUid);
  } catch (e) {
    logger.error('Failed to load compliance stats:', e);
  }
  try {
    completenessKpi.value = await getCompleteness(24, siteUid);
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
  await Promise.all([loadLatestData(), loadSensorHealth(), loadStats(), loadSitesStatus()]);
  isRefreshing.value = false;
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
  await loadSites();
  await Promise.all([loadLatestData(), loadDevices(), loadChartData(), loadSensorHealth(), loadAlertRules(), loadStats()]);
  loadSitesStatus();
  refreshInterval = setInterval(() => {
    loadLatestData();
    loadSensorHealth();
    loadStats();
    loadSitesStatus();
  }, 30000);
});

onUnmounted(() => {
  if (refreshInterval) clearInterval(refreshInterval);
});
</script>

<style scoped>
.fade-enter-active, .fade-leave-active { transition: opacity 0.2s ease; }
.fade-enter-from, .fade-leave-to       { opacity: 0; }
</style>
