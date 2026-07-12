<template>
  <AppLayout>

    <!-- ═══════════════════════════════════════════
         Zone 1 — Top Bar: Site selector + Status
         ═══════════════════════════════════════════ -->
    <div class="card px-4 py-3 mb-4 md:mb-5 flex flex-wrap items-center gap-3">
      <!-- Site selector -->
      <div class="flex items-center gap-2 flex-1 min-w-0">
        <i class="fas fa-map-marker-alt text-primary text-sm shrink-0"></i>
        <select
          v-model="selectedSiteUid"
          @change="onSiteChange"
          class="flex-1 min-w-0 max-w-xs px-3 py-1.5 border border-slate-200 rounded-lg text-sm focus:ring-2 focus:ring-primary bg-white"
        >
          <option value="">-- Pilih Lokasi --</option>
          <option v-for="site in sites" :key="site.uid" :value="site.uid">
            {{ site.name }} — {{ site.company_name }}
          </option>
        </select>
      </div>

      <!-- Devices online pill -->
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

      <!-- Last updated -->
      <div class="flex items-center gap-2 text-xs text-slate-400">
        <i class="fas fa-clock"></i>
        <span>{{ lastUpdatedText }}</span>
      </div>

      <!-- Refresh button -->
      <button
        @click="manualRefresh"
        :disabled="isRefreshing"
        class="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium text-slate-600 hover:bg-slate-100 transition-colors disabled:opacity-50"
      >
        <i class="fas fa-sync-alt text-xs" :class="{ 'animate-spin': isRefreshing }"></i>
        Refresh
      </button>
    </div>

    <!-- ═══════════════════════════════════════════
         Zone 2 — KPI Sensor Cards (semua 8 params)
         ═══════════════════════════════════════════ -->
    <div class="grid grid-cols-2 sm:grid-cols-4 gap-3 md:gap-4 mb-4 md:mb-5">
      <SensorCard label="pH"         :value="latestData?.ph"      icon="fas fa-flask"           icon-class="bg-blue-100 text-blue-600"    :trend="getTrend('ph')"      field="ph"      :decimals="2" :health="sensorHealth.ph" />
      <SensorCard label="TSS"        :value="latestData?.tss"     unit="mg/L" icon="fas fa-filter"   icon-class="bg-sky-100 text-sky-600"      :trend="getTrend('tss')"     field="tss"     :decimals="1" :health="sensorHealth.tss" />
      <SensorCard label="COD"        :value="latestData?.cod"     unit="mg/L" icon="fas fa-vial"     icon-class="bg-indigo-100 text-indigo-600" :trend="getTrend('cod')"     field="cod"     :decimals="1" :health="sensorHealth.cod" />
      <SensorCard label="NH3-N"      :value="latestData?.nh3n"    unit="mg/L" icon="fas fa-atom"     icon-class="bg-emerald-100 text-emerald-600" :trend="getTrend('nh3n')"  field="nh3n"    :decimals="2" :health="sensorHealth.nh3n" />
      <SensorCard label="Debit Air"  :value="latestData?.debit"   unit="L/min" icon="fas fa-water"   icon-class="bg-cyan-100 text-cyan-600"    :trend="getTrend('debit')"   field="debit"   :decimals="1" :health="sensorHealth.debit" />
      <SensorCard label="Tegangan"   :value="latestData?.voltage" unit="V"    icon="fas fa-bolt"     icon-class="bg-amber-100 text-amber-600"  :trend="getTrend('voltage')" field="voltage" :decimals="1" />
      <SensorCard label="Arus"       :value="latestData?.current" unit="A"    icon="fas fa-plug"     icon-class="bg-orange-100 text-orange-600" :trend="getTrend('current')" field="current" :decimals="2" />
      <SensorCard label="Temperatur" :value="latestData?.temp"    unit="°C"   icon="fas fa-thermometer-half" icon-class="bg-red-100 text-red-600" :trend="getTrend('temp')" field="temp"    :decimals="1" :health="sensorHealth.temp" />
    </div>

    <!-- ═══════════════════════════════════════════
         Zone 3 — Main Chart + Compliance Status
         ═══════════════════════════════════════════ -->
    <div class="grid grid-cols-1 lg:grid-cols-3 gap-4 md:gap-5 mb-4 md:mb-5">

      <!-- Main Trend Chart (2/3) -->
      <div class="lg:col-span-2 card p-4 md:p-6">
        <div class="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-2 mb-4">
          <div>
            <h3 class="card-title">Tren Parameter Air Limbah</h3>
            <p class="text-xs text-slate-400 mt-0.5">Kualitas air real-time</p>
          </div>
          <select
            v-model="chartPeriod"
            @change="loadChartData"
            class="px-3 py-1.5 border border-slate-200 rounded-lg text-xs focus:ring-2 focus:ring-primary bg-white"
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
          <div v-else class="h-full flex items-center justify-center text-slate-400 text-sm">
            <i class="fas fa-chart-area mr-2"></i> Pilih lokasi untuk melihat data
          </div>
        </div>
      </div>

      <!-- Compliance Status (1/3) -->
      <div class="card p-4 md:p-6 flex flex-col">
        <div class="mb-4">
          <h3 class="card-title">Status Baku Mutu</h3>
          <p class="text-xs text-slate-400 mt-0.5">Permen LH No. 5/2014</p>
        </div>

        <!-- Overall compliance badge -->
        <div class="mb-5 flex items-center gap-3 p-3 rounded-xl"
          :class="overallCompliance === 'ok' ? 'bg-emerald-50 border border-emerald-100'
                : overallCompliance === 'warn' ? 'bg-amber-50 border border-amber-100'
                : 'bg-red-50 border border-red-100'"
        >
          <div class="w-9 h-9 rounded-full flex items-center justify-center shrink-0"
            :class="overallCompliance === 'ok' ? 'bg-emerald-100'
                  : overallCompliance === 'warn' ? 'bg-amber-100' : 'bg-red-100'"
          >
            <i class="text-sm"
              :class="overallCompliance === 'ok' ? 'fas fa-check-circle text-emerald-600'
                    : overallCompliance === 'warn' ? 'fas fa-exclamation-triangle text-amber-600'
                    : 'fas fa-times-circle text-red-600'"
            ></i>
          </div>
          <div>
            <div class="text-xs font-semibold"
              :class="overallCompliance === 'ok' ? 'text-emerald-700'
                    : overallCompliance === 'warn' ? 'text-amber-700' : 'text-red-700'"
            >
              {{ overallCompliance === 'ok' ? 'Semua Parameter Normal'
                : overallCompliance === 'warn' ? 'Ada Peringatan'
                : 'Melebihi Baku Mutu' }}
            </div>
            <div class="text-[10px] text-slate-400 mt-0.5">
              {{ complianceParams.filter(p => p.status === 'normal').length }}/{{ complianceParams.length }} parameter terpenuhi
            </div>
          </div>
        </div>

        <!-- Per-parameter progress bars -->
        <div class="space-y-3 flex-1">
          <div v-for="p in complianceParams" :key="p.label">
            <div class="flex items-center justify-between mb-1">
              <div class="flex items-center gap-1.5">
                <span class="text-xs font-medium text-slate-700">{{ p.label }}</span>
                <span class="text-[10px] text-slate-400">{{ p.limitLabel }}</span>
              </div>
              <div class="flex items-center gap-1.5">
                <span class="text-xs font-semibold" :class="p.valueColor">
                  {{ p.displayValue }}
                </span>
                <i class="text-[10px]"
                  :class="p.status === 'normal' ? 'fas fa-check text-emerald-500'
                        : p.status === 'warning' ? 'fas fa-exclamation text-amber-500'
                        : 'fas fa-times text-red-500'"
                ></i>
              </div>
            </div>
            <div class="h-1.5 bg-slate-100 rounded-full overflow-hidden">
              <div
                class="h-full rounded-full transition-all duration-700"
                :class="p.barColor"
                :style="{ width: p.barWidth }"
              ></div>
            </div>
          </div>
        </div>

        <!-- No data state -->
        <div v-if="!latestData" class="flex-1 flex flex-col items-center justify-center text-slate-400 gap-2 py-4">
          <i class="fas fa-database text-2xl"></i>
          <span class="text-xs">Belum ada data</span>
        </div>
      </div>
    </div>

    <!-- ═══════════════════════════════════════════
         Zone 4 — Secondary Charts
         ═══════════════════════════════════════════ -->
    <div class="grid grid-cols-1 md:grid-cols-2 gap-4 md:gap-5 mb-4 md:mb-5">
      <!-- Electrical -->
      <div class="card p-4 md:p-6">
        <h3 class="card-title mb-1">Parameter Kelistrikan</h3>
        <p class="text-xs text-slate-400 mb-4">Tegangan & Arus</p>
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

      <!-- Debit & Temp -->
      <div class="card p-4 md:p-6">
        <h3 class="card-title mb-1">Debit & Temperatur</h3>
        <p class="text-xs text-slate-400 mb-4">Laju alir & suhu air</p>
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
         Zone 5 — Device Table + Mini Map
         ═══════════════════════════════════════════ -->
    <div class="grid grid-cols-1 lg:grid-cols-3 gap-4 md:gap-5">

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
      <div class="card p-4 flex flex-col">
        <div class="flex items-center gap-2 mb-3">
          <h3 class="card-title flex-1">Peta Lokasi</h3>
          <span class="ml-auto text-xs text-slate-400">{{ sites.length }} site</span>
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
          <div v-else class="h-full flex items-center justify-center text-slate-400 text-xs gap-2">
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
import SensorCard from '@/Components/SensorCard.vue';
import SiteMap from '@/Components/SiteMap.vue';
import StatusBadge from '@/Components/StatusBadge.vue';
import DataTable from '@/Components/DataTable.vue';
import { useApi } from '@/Composables/useApi';
import { useAuth } from '@/Composables/useAuth';
import { getRelativeTime, getSensorStatus, formatNumber, parseUTC } from '@/Utils/helpers';
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

const { getLatestData, getData, getDevices, getSites, getSensorHealth } = useApi();
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

let refreshInterval = null;

// ── Computed ────────────────────────────────────────────────────
const onlineDevices  = computed(() => devices.value.filter(d => getDeviceStatus(d) === 'online').length);
const totalDevices   = computed(() => devices.value.length);

const lastUpdatedText = computed(() => {
  if (!lastUpdated.value) return 'Belum diperbarui';
  return `Diperbarui ${getRelativeTime(lastUpdated.value)}`;
});

// Baku mutu compliance params
const complianceParams = computed(() => {
  const d = latestData.value;
  if (!d) return [];

  const params = [
    {
      label: 'pH',
      field: 'ph',
      value: d.ph,
      min: 6.0,
      max: 9.0,
      unit: '',
      limitLabel: '(6.0–9.0)',
    },
    {
      label: 'TSS',
      field: 'tss',
      value: d.tss,
      max: 200,
      unit: 'mg/L',
      limitLabel: '(≤200)',
    },
    {
      label: 'COD',
      field: 'cod',
      value: d.cod,
      max: 300,
      unit: 'mg/L',
      limitLabel: '(≤300)',
    },
    {
      label: 'NH3-N',
      field: 'nh3n',
      value: d.nh3n,
      max: 10,
      unit: 'mg/L',
      limitLabel: '(≤10)',
    },
  ];

  return params.map(p => {
    const v = p.value;
    let status = 'normal';
    let pct = 0;

    if (v == null) {
      return { ...p, status: 'nodata', displayValue: '-', barWidth: '0%', barColor: 'bg-slate-200', valueColor: 'text-slate-400' };
    }

    if (p.min !== undefined) {
      // Range param (pH)
      const range = p.max - p.min;
      pct = Math.min(100, Math.max(0, ((v - p.min) / range) * 100));
      if (v < 6.0 || v > 9.0) status = 'danger';
      else if (v < 6.5 || v > 8.5) status = 'warning';
    } else {
      // Upper-limit param
      pct = Math.min(100, (v / p.max) * 100);
      if (pct >= 100) status = 'danger';
      else if (pct >= 75) status = 'warning';
    }

    const barColor = status === 'danger' ? 'bg-red-500'
                   : status === 'warning' ? 'bg-amber-400'
                   : 'bg-emerald-500';
    const valueColor = status === 'danger' ? 'text-red-600'
                     : status === 'warning' ? 'text-amber-600'
                     : 'text-emerald-600';
    const displayValue = `${formatNumber(v, p.min !== undefined ? 2 : 1)}${p.unit ? ' ' + p.unit : ''}`;

    return { ...p, status, displayValue, barWidth: `${pct}%`, barColor, valueColor };
  });
});

const overallCompliance = computed(() => {
  if (!complianceParams.value.length) return 'ok';
  if (complianceParams.value.some(p => p.status === 'danger')) return 'danger';
  if (complianceParams.value.some(p => p.status === 'warning')) return 'warn';
  return 'ok';
});

const siteTz = computed(() => currentSite.value?.timezone || 'Asia/Jakarta');

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
  yaxis: { labels: { style: { colors: '#94a3b8', fontSize: '10px' } } },
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

const debitTempOptions = computed(() => ({
  chart: { type: 'area', toolbar: { show: false }, zoom: { enabled: false }, animations: { enabled: true, speed: 800 }, fontFamily: 'Inter, sans-serif' },
  colors: [colors.debit, colors.temp],
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
  yaxis: [
    { title: { text: 'L/min', style: { fontSize: '11px' } }, labels: { style: { colors: '#94a3b8', fontSize: '10px' } } },
    { opposite: true, title: { text: '°C', style: { fontSize: '11px' } }, labels: { style: { colors: '#94a3b8', fontSize: '10px' } } },
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

const debitTempSeries = computed(() => [
  { name: 'Debit',       data: chartData.value.map(d => ({ x: parseUTC(d.ts), y: d.debit })) },
  { name: 'Temperature', data: chartData.value.map(d => ({ x: parseUTC(d.ts), y: d.temp })) },
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
  if (selected) {
    currentSite.value = selected;
    await Promise.all([loadLatestData(), loadDevices(), loadChartData(), loadSensorHealth()]);
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

const manualRefresh = async () => {
  isRefreshing.value = true;
  await Promise.all([loadLatestData(), loadSensorHealth()]);
  isRefreshing.value = false;
};

const getTrend = (field) => {
  if (!latestData.value || !previousData.value) return null;
  const cur = latestData.value[field];
  const prv = previousData.value[field];
  if (cur == null || prv == null || prv === 0) return null;
  return ((cur - prv) / prv) * 100;
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
  await Promise.all([loadLatestData(), loadDevices(), loadChartData(), loadSensorHealth()]);
  refreshInterval = setInterval(() => { loadLatestData(); loadSensorHealth(); }, 30000);
});

onUnmounted(() => {
  if (refreshInterval) clearInterval(refreshInterval);
});
</script>

<style scoped>
.fade-enter-active, .fade-leave-active { transition: opacity 0.2s ease; }
.fade-enter-from, .fade-leave-to       { opacity: 0; }
</style>
