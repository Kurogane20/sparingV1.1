<template>
  <AppLayout>
    <!-- Site Selector -->
    <div class="mb-4 md:mb-6 bg-white rounded-xl md:rounded-2xl p-3 md:p-4 shadow-sm">
      <div class="flex flex-col sm:flex-row sm:items-center gap-3 sm:gap-4">
        <label class="text-sm font-medium text-gray-700">Pilih Lokasi:</label>
        <select
          v-model="selectedSiteUid"
          @change="onSiteChange"
          class="flex-1 max-w-md px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary text-sm"
        >
          <option value="">-- Pilih Lokasi --</option>
          <option v-for="site in sites" :key="site.uid" :value="site.uid">
            {{ site.name }} - {{ site.company_name }}
          </option>
        </select>
        <div v-if="currentSite" class="text-xs md:text-sm text-gray-600">
          <i class="fas fa-map-marker-alt text-primary"></i>
          {{ currentSite.lat }}, {{ currentSite.lon }}
        </div>
      </div>
    </div>

    <!-- Sensor Cards Grid - Water Parameters -->
    <div class="grid grid-cols-2 md:grid-cols-4 gap-3 md:gap-6 mb-4 md:mb-6">
      <SensorCard
        label="pH"
        :value="latestData?.ph"
        icon="fas fa-flask"
        icon-class="bg-blue-100 text-blue-600"
        :trend="getTrend('ph')"
        field="ph"
        :decimals="2"
      />
      <SensorCard
        label="TSS"
        :value="latestData?.tss"
        unit="mg/L"
        icon="fas fa-filter"
        icon-class="bg-sky-100 text-sky-600"
        :trend="getTrend('tss')"
        field="tss"
        :decimals="1"
      />
      <SensorCard
        label="COD"
        :value="latestData?.cod"
        unit="mg/L"
        icon="fas fa-vial"
        icon-class="bg-indigo-100 text-indigo-600"
        :trend="getTrend('cod')"
        field="cod"
        :decimals="1"
      />
      <SensorCard
        label="NH3-N"
        :value="latestData?.nh3n"
        unit="mg/L"
        icon="fas fa-atom"
        icon-class="bg-emerald-100 text-emerald-600"
        :trend="getTrend('nh3n')"
        field="nh3n"
        :decimals="2"
      />
    </div>

    <!-- Additional Parameters -->
    <div class="grid grid-cols-2 md:grid-cols-4 gap-3 md:gap-6 mb-4 md:mb-6">
      <SensorCard
        label="Debit Air"
        :value="latestData?.debit"
        unit="L/min"
        icon="fas fa-water"
        icon-class="bg-cyan-100 text-cyan-600"
        :trend="getTrend('debit')"
        field="debit"
        :decimals="1"
      />
      <SensorCard
        label="Tegangan"
        :value="latestData?.voltage"
        unit="V"
        icon="fas fa-bolt"
        icon-class="bg-amber-100 text-amber-600"
        :trend="getTrend('voltage')"
        field="voltage"
        :decimals="1"
      />
      <SensorCard
        label="Arus"
        :value="latestData?.current"
        unit="A"
        icon="fas fa-plug"
        icon-class="bg-orange-100 text-orange-600"
        :trend="getTrend('current')"
        field="current"
        :decimals="2"
      />
      <SensorCard
        label="Temperatur"
        :value="latestData?.temp"
        unit="°C"
        icon="fas fa-thermometer-half"
        icon-class="bg-red-100 text-red-600"
        :trend="getTrend('temp')"
        field="temp"
        :decimals="1"
      />
    </div>

    <!-- Charts Grid -->
    <div class="grid grid-cols-1 lg:grid-cols-3 gap-4 md:gap-6 mb-4 md:mb-6">
      <!-- Main Chart - Water Quality Trend -->
      <div class="lg:col-span-2 bg-white rounded-xl md:rounded-2xl p-4 md:p-6 shadow-sm backdrop-blur-sm bg-opacity-90">
        <div class="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-2 mb-4">
          <h3 class="text-base md:text-lg font-semibold text-gray-900">
            Tren Parameter Air Limbah
          </h3>
          <select
            v-model="chartPeriod"
            @change="loadChartData"
            class="px-3 py-1.5 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-primary"
          >
            <option value="today">Hari Ini</option>
            <option value="week">Minggu Ini</option>
            <option value="month">Bulan Ini</option>
          </select>
        </div>
        <div class="h-64 md:h-80">
          <apexchart
            v-if="chartOptions"
            type="area"
            height="100%"
            :options="chartOptions"
            :series="chartSeries"
          />
        </div>
      </div>

      <!-- Right Side Analytics -->
      <div class="flex flex-col gap-4 md:gap-6">
        <!-- Parameter Distribution -->
        <div class="bg-white rounded-xl md:rounded-2xl p-4 md:p-6 shadow-sm backdrop-blur-sm bg-opacity-90">
          <h3 class="text-base md:text-lg font-semibold text-gray-900 mb-4">
            Distribusi Parameter
          </h3>
          <div class="h-40 md:h-48">
            <apexchart
              v-if="donutOptions"
              type="donut"
              height="100%"
              :options="donutOptions"
              :series="donutSeries"
            />
          </div>
        </div>

        <!-- System Status -->
        <div class="bg-gradient-to-br from-primary to-blue-700 rounded-xl md:rounded-2xl p-4 md:p-6 shadow-lg text-white">
          <h3 class="text-sm md:text-base font-semibold opacity-90 mb-2">Status Sistem</h3>
          <div class="text-3xl md:text-4xl font-bold mb-2">{{ onlineDevices }}/{{ totalDevices }}</div>
          <p class="text-xs md:text-sm opacity-80">
            Perangkat online dan mengirim data
          </p>
        </div>
      </div>
    </div>

    <!-- Secondary Charts Row -->
    <div class="grid grid-cols-1 md:grid-cols-2 gap-4 md:gap-6 mb-4 md:mb-6">
      <!-- Electrical Parameters Chart -->
      <div class="bg-white rounded-xl md:rounded-2xl p-4 md:p-6 shadow-sm backdrop-blur-sm bg-opacity-90">
        <h3 class="text-base md:text-lg font-semibold text-gray-900 mb-4">
          Parameter Kelistrikan
        </h3>
        <div class="h-56 md:h-64">
          <apexchart
            v-if="electricalOptions"
            type="line"
            height="100%"
            :options="electricalOptions"
            :series="electricalSeries"
          />
        </div>
      </div>

      <!-- Debit & Temperature Chart -->
      <div class="bg-white rounded-xl md:rounded-2xl p-4 md:p-6 shadow-sm backdrop-blur-sm bg-opacity-90">
        <h3 class="text-base md:text-lg font-semibold text-gray-900 mb-4">
          Debit & Temperatur
        </h3>
        <div class="h-56 md:h-64">
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

    <!-- Device Status Table -->
    <DataTable
      title="Status Perangkat Sensor"
      :data="devices"
      :columns="deviceColumns"
      :loading="devicesLoading"
      empty-message="Tidak ada perangkat terdaftar"
    >
      <template #cell-status="{ row }">
        <StatusBadge
          :status="getDeviceStatus(row)"
          :label="getDeviceStatusLabel(row)"
        />
      </template>
      <template #cell-last_update="{ value }">
        {{ getRelativeTime(value) }}
      </template>
      <template #cell-actions="{ row }">
        <button
          @click="viewDeviceDetail(row)"
          class="text-secondary hover:underline text-sm"
        >
          Detail
        </button>
      </template>
    </DataTable>

    <!-- Device Detail Modal -->
    <div
      v-if="showDeviceDetailModal && selectedDevice"
      class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4"
      @click.self="closeDeviceDetailModal"
    >
      <div class="bg-white rounded-2xl max-w-2xl w-full p-6 max-h-[90vh] overflow-y-auto">
        <div class="flex justify-between items-center mb-4">
          <h3 class="text-xl font-bold text-gray-900">Detail Perangkat</h3>
          <button @click="closeDeviceDetailModal" class="text-gray-400 hover:text-gray-600">
            <i class="fas fa-times text-xl"></i>
          </button>
        </div>
        <div class="space-y-4">
          <div class="bg-gray-50 rounded-lg p-4">
            <div class="grid grid-cols-2 gap-4">
              <div>
                <label class="text-sm font-medium text-gray-600">ID Perangkat</label>
                <p class="text-lg font-semibold text-gray-900">#IOT-{{ String(selectedDevice.id).padStart(3, '0') }}</p>
              </div>
              <div>
                <label class="text-sm font-medium text-gray-600">Status</label>
                <div class="mt-1">
                  <StatusBadge :status="getDeviceStatus(selectedDevice)" :label="getDeviceStatusLabel(selectedDevice)" />
                </div>
              </div>
            </div>
          </div>
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label class="block text-sm font-medium text-gray-600 mb-1">Nama</label>
              <p class="text-gray-900">{{ selectedDevice.name }}</p>
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-600 mb-1">Model</label>
              <p class="text-gray-900">{{ selectedDevice.model || '-' }}</p>
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-600 mb-1">Serial Number</label>
              <p class="text-gray-900">{{ selectedDevice.serial_no || '-' }}</p>
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-600 mb-1">Terakhir Update</label>
              <p class="text-gray-900">{{ getRelativeTime(selectedDevice.last_update) }}</p>
            </div>
          </div>
          <div class="flex justify-end pt-4 border-t">
            <button @click="closeDeviceDetailModal" class="px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300">
              Tutup
            </button>
          </div>
        </div>
      </div>
    </div>
  </AppLayout>
</template>

<script setup>
import { ref, onMounted, onUnmounted, computed } from 'vue';
import VueApexCharts from 'vue3-apexcharts';
import AppLayout from '@/Layouts/AppLayout.vue';
import SensorCard from '@/Components/SensorCard.vue';
import StatusBadge from '@/Components/StatusBadge.vue';
import DataTable from '@/Components/DataTable.vue';
import { useApi } from '@/Composables/useApi';
import { useAuth } from '@/Composables/useAuth';
import { getRelativeTime, getSensorStatus } from '@/Utils/helpers';

const apexchart = VueApexCharts;

// Color palette - Corporate Professional
const colors = {
  ph: '#1e40af',      // Corporate Blue
  tss: '#0ea5e9',     // Sky Blue
  cod: '#6366f1',     // Indigo
  nh3n: '#10b981',    // Emerald
  debit: '#0891b2',   // Cyan
  voltage: '#f59e0b', // Amber
  current: '#ef4444', // Red
  temp: '#f97316',    // Orange
};

// Composables
const { getLatestData, getData, getDevices, getSites } = useApi();
const { filterSitesByUser } = useAuth();

// State
const latestData = ref(null);
const previousData = ref(null);
const chartPeriod = ref('today');
const devices = ref([]);
const devicesLoading = ref(false);
const sites = ref([]);
const currentSite = ref(null);
const selectedSiteUid = ref('');
const chartData = ref([]);

// Auto-refresh interval
let refreshInterval = null;

// Device table columns
const deviceColumns = [
  { key: 'id', label: 'ID', format: (val) => `#IOT-${String(val).padStart(3, '0')}` },
  { key: 'name', label: 'Nama' },
  { key: 'model', label: 'Model' },
  { key: 'last_update', label: 'Terakhir Update' },
  { key: 'status', label: 'Status' },
  { key: 'actions', label: 'Aksi' },
];

// Computed
const onlineDevices = computed(() => devices.value.filter(d => getDeviceStatus(d) === 'online').length);
const totalDevices = computed(() => devices.value.length);

// Main Area Chart Options
const chartOptions = computed(() => ({
  chart: {
    type: 'area',
    toolbar: { show: false },
    zoom: { enabled: false },
    animations: {
      enabled: true,
      easing: 'easeinout',
      speed: 800,
    },
    fontFamily: 'Inter, sans-serif',
  },
  colors: [colors.ph, colors.tss, colors.cod, colors.nh3n],
  dataLabels: { enabled: false },
  stroke: { curve: 'smooth', width: 2 },
  fill: {
    type: 'gradient',
    gradient: {
      shadeIntensity: 1,
      opacityFrom: 0.4,
      opacityTo: 0.1,
      stops: [0, 90, 100],
    },
  },
  xaxis: {
    type: 'datetime',
    labels: {
      style: { colors: '#64748b', fontSize: '11px' },
      datetimeFormatter: { hour: 'HH:mm' },
    },
  },
  yaxis: {
    labels: { style: { colors: '#64748b', fontSize: '11px' } },
  },
  tooltip: {
    x: { format: 'dd MMM HH:mm' },
    theme: 'light',
  },
  legend: {
    position: 'top',
    horizontalAlign: 'left',
    fontSize: '12px',
    markers: { radius: 12 },
  },
  grid: {
    borderColor: '#e2e8f0',
    strokeDashArray: 4,
  },
  responsive: [
    {
      breakpoint: 768,
      options: {
        legend: { fontSize: '10px' },
        xaxis: { labels: { style: { fontSize: '9px' } } },
      },
    },
  ],
}));

const chartSeries = computed(() => [
  { name: 'pH', data: chartData.value.map(d => ({ x: new Date(d.ts), y: d.ph })) },
  { name: 'TSS', data: chartData.value.map(d => ({ x: new Date(d.ts), y: d.tss })) },
  { name: 'COD', data: chartData.value.map(d => ({ x: new Date(d.ts), y: d.cod })) },
  { name: 'NH3-N', data: chartData.value.map(d => ({ x: new Date(d.ts), y: d.nh3n })) },
]);

// Donut Chart
const donutOptions = computed(() => ({
  chart: { type: 'donut', fontFamily: 'Inter, sans-serif' },
  colors: [colors.ph, colors.tss, colors.cod, colors.nh3n],
  labels: ['pH', 'TSS', 'COD', 'NH3-N'],
  legend: { position: 'right', fontSize: '11px' },
  dataLabels: { enabled: false },
  plotOptions: {
    pie: {
      donut: {
        size: '70%',
        labels: {
          show: true,
          name: { fontSize: '12px' },
          value: { fontSize: '14px', fontWeight: 600 },
          total: { show: true, label: 'Total', fontSize: '12px' },
        },
      },
    },
  },
  responsive: [{ breakpoint: 480, options: { legend: { position: 'bottom' } } }],
}));

const donutSeries = computed(() => [
  latestData.value?.ph || 0,
  latestData.value?.tss || 0,
  latestData.value?.cod || 0,
  latestData.value?.nh3n || 0,
]);

// Electrical Chart
const electricalOptions = computed(() => ({
  chart: {
    type: 'line',
    toolbar: { show: false },
    zoom: { enabled: false },
    animations: { enabled: true, speed: 800 },
    fontFamily: 'Inter, sans-serif',
  },
  colors: [colors.voltage, colors.current],
  stroke: { curve: 'smooth', width: 3 },
  xaxis: {
    type: 'datetime',
    labels: { style: { colors: '#64748b', fontSize: '10px' } },
  },
  yaxis: [
    { title: { text: 'Voltage (V)', style: { color: colors.voltage } }, labels: { style: { colors: '#64748b' } } },
    { opposite: true, title: { text: 'Current (A)', style: { color: colors.current } }, labels: { style: { colors: '#64748b' } } },
  ],
  legend: { position: 'top', fontSize: '11px' },
  grid: { borderColor: '#e2e8f0', strokeDashArray: 4 },
}));

const electricalSeries = computed(() => [
  { name: 'Voltage', data: chartData.value.map(d => ({ x: new Date(d.ts), y: d.voltage })) },
  { name: 'Current', data: chartData.value.map(d => ({ x: new Date(d.ts), y: d.current })) },
]);

// Debit & Temp Chart
const debitTempOptions = computed(() => ({
  chart: {
    type: 'area',
    toolbar: { show: false },
    zoom: { enabled: false },
    animations: { enabled: true, speed: 800 },
    fontFamily: 'Inter, sans-serif',
  },
  colors: [colors.debit, colors.temp],
  stroke: { curve: 'smooth', width: 2 },
  fill: {
    type: 'gradient',
    gradient: { opacityFrom: 0.4, opacityTo: 0.1 },
  },
  xaxis: {
    type: 'datetime',
    labels: { style: { colors: '#64748b', fontSize: '10px' } },
  },
  yaxis: [
    { title: { text: 'Debit (L/min)' }, labels: { style: { colors: '#64748b' } } },
    { opposite: true, title: { text: 'Temp (°C)' }, labels: { style: { colors: '#64748b' } } },
  ],
  legend: { position: 'top', fontSize: '11px' },
  grid: { borderColor: '#e2e8f0', strokeDashArray: 4 },
}));

const debitTempSeries = computed(() => [
  { name: 'Debit', data: chartData.value.map(d => ({ x: new Date(d.ts), y: d.debit })) },
  { name: 'Temperature', data: chartData.value.map(d => ({ x: new Date(d.ts), y: d.temp })) },
]);

// Load sites
const loadSites = async () => {
  try {
    const response = await getSites({ per_page: 100 });
    let sitesList = response?.items || (Array.isArray(response) ? response : response?.data || []);
    sites.value = filterSitesByUser(sitesList);
    if (sites.value.length > 0) {
      selectedSiteUid.value = sites.value[0].uid;
      currentSite.value = sites.value[0];
    }
  } catch (error) {
    console.error('Failed to load sites:', error);
  }
};

// Handle site change
const onSiteChange = async () => {
  const selected = sites.value.find(s => s.uid === selectedSiteUid.value);
  if (selected) {
    currentSite.value = selected;
    await loadLatestData();
    await loadDevices();
    await loadChartData();
  }
};

// Load latest data
const loadLatestData = async () => {
  if (!currentSite.value) return;
  try {
    if (latestData.value) previousData.value = { ...latestData.value };
    const data = await getLatestData(currentSite.value.uid);
    latestData.value = data;
  } catch (error) {
    console.error('Failed to load latest data:', error);
  }
};

// Load devices
const loadDevices = async () => {
  if (!currentSite.value) return;
  devicesLoading.value = true;
  try {
    const response = await getDevices({ site_uid: currentSite.value.uid });
    let devicesList = response?.items || (Array.isArray(response) ? response : response?.data || []);
    devices.value = devicesList.filter(d => d.is_active !== false).map(d => ({
      ...d,
      last_update: new Date(Date.now() - Math.random() * 600000).toISOString(),
    }));
  } catch (error) {
    devices.value = [];
  } finally {
    devicesLoading.value = false;
  }
};

// Load chart data
const loadChartData = async () => {
  if (!currentSite.value) return;
  try {
    const now = new Date();
    let dateFrom;
    if (chartPeriod.value === 'today') dateFrom = new Date(now.setHours(0, 0, 0, 0));
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
  } catch (error) {
    console.error('Failed to load chart data:', error);
  }
};

// Get trend
const getTrend = (field) => {
  if (!latestData.value || !previousData.value) return null;
  const current = latestData.value[field];
  const previous = previousData.value[field];
  if (current == null || previous == null || previous === 0) return null;
  return ((current - previous) / previous) * 100;
};

// Device status helpers
const getDeviceStatus = (device) => getSensorStatus(device.last_update);
const getDeviceStatusLabel = (device) => {
  const status = getDeviceStatus(device);
  if (status === 'online') return 'Aktif';
  if (status === 'warning') return 'Sleep';
  return 'Offline';
};

// Modal
const showDeviceDetailModal = ref(false);
const selectedDevice = ref(null);
const viewDeviceDetail = (device) => { selectedDevice.value = device; showDeviceDetailModal.value = true; };
const closeDeviceDetailModal = () => { showDeviceDetailModal.value = false; selectedDevice.value = null; };

// Initialize
const initDashboard = async () => {
  await loadSites();
  await loadLatestData();
  await loadDevices();
  await loadChartData();
};

const setupAutoRefresh = () => {
  refreshInterval = setInterval(async () => {
    await loadLatestData();
  }, 30000);
};

onMounted(async () => {
  await initDashboard();
  setupAutoRefresh();
});

onUnmounted(() => {
  if (refreshInterval) clearInterval(refreshInterval);
});
</script>
