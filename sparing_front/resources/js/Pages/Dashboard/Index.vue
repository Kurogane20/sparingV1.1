<template>
  <AppLayout>
    <!-- Site Selector -->
    <div class="mb-6 bg-white rounded-2xl p-4 shadow-sm">
      <div class="flex items-center gap-4">
        <label class="text-sm font-medium text-gray-700">Pilih Lokasi:</label>
        <select
          v-model="selectedSiteUid"
          @change="onSiteChange"
          class="flex-1 max-w-md px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary"
        >
          <option value="">-- Pilih Lokasi --</option>
          <option v-for="site in sites" :key="site.uid" :value="site.uid">
            {{ site.name }} - {{ site.company_name }}
          </option>
        </select>
        <div v-if="currentSite" class="text-sm text-gray-600">
          <i class="fas fa-map-marker-alt text-primary"></i>
          {{ currentSite.lat }}, {{ currentSite.lon }}
        </div>
      </div>
    </div>

    <!-- Sensor Cards Grid - Wastewater Parameters -->
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-6">
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
        icon-class="bg-amber-100 text-amber-600"
        :trend="getTrend('tss')"
        field="tss"
        :decimals="1"
      />

      <SensorCard
        label="COD"
        :value="latestData?.cod"
        unit="mg/L"
        icon="fas fa-vial"
        icon-class="bg-purple-100 text-purple-600"
        :trend="getTrend('cod')"
        field="cod"
        :decimals="1"
      />

      <SensorCard
        label="NH3-N"
        :value="latestData?.nh3n"
        unit="mg/L"
        icon="fas fa-atom"
        icon-class="bg-green-100 text-green-600"
        :trend="getTrend('nh3n')"
        field="nh3n"
        :decimals="2"
      />
    </div>

    <!-- Additional Parameters -->
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-6">
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
        icon-class="bg-yellow-100 text-yellow-600"
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

    <!-- Charts and Analytics Grid -->
    <div class="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
      <!-- Main Chart - pH & TSS Trend -->
      <div class="lg:col-span-2 bg-white rounded-2xl p-6 shadow-sm">
        <div class="flex justify-between items-center mb-4">
          <h3 class="text-lg font-semibold text-gray-900">
            Tren Parameter Air Limbah (24 Jam)
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
        <div class="relative h-80">
          <canvas ref="mainChartCanvas"></canvas>
        </div>
      </div>

      <!-- Right Side Analytics -->
      <div class="flex flex-col gap-6">
        <!-- Water Quality Distribution -->
        <div class="bg-white rounded-2xl p-6 shadow-sm">
          <h3 class="text-lg font-semibold text-gray-900 mb-4">
            Distribusi Parameter
          </h3>
          <div class="relative h-40">
            <canvas ref="donutChartCanvas"></canvas>
          </div>
          <p class="text-xs text-gray-600 mt-3">
            Monitoring parameter kualitas air limbah
          </p>
        </div>

        <!-- System Status -->
        <div class="bg-primary rounded-2xl p-6 shadow-sm text-white">
          <h3 class="text-base font-semibold opacity-90 mb-2">Status Sistem</h3>
          <div class="text-4xl font-bold mb-2">{{ onlineDevices }}/{{ totalDevices }}</div>
          <p class="text-sm opacity-80">
            Perangkat online dan mengirim data
          </p>
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
          <!-- Device Info -->
          <div class="bg-gray-50 rounded-lg p-4">
            <div class="grid grid-cols-2 gap-4">
              <div>
                <label class="text-sm font-medium text-gray-600">ID Perangkat</label>
                <p class="text-lg font-semibold text-gray-900">#IOT-{{ String(selectedDevice.id).padStart(3, '0') }}</p>
              </div>
              <div>
                <label class="text-sm font-medium text-gray-600">Status</label>
                <div class="mt-1">
                  <StatusBadge
                    :status="getDeviceStatus(selectedDevice)"
                    :label="getDeviceStatusLabel(selectedDevice)"
                  />
                </div>
              </div>
            </div>
          </div>

          <!-- Device Details -->
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label class="block text-sm font-medium text-gray-600 mb-1">Nama Perangkat</label>
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
              <label class="block text-sm font-medium text-gray-600 mb-1">Modbus Address</label>
              <p class="text-gray-900">{{ selectedDevice.modbus_addr }}</p>
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-600 mb-1">Terakhir Update</label>
              <p class="text-gray-900">{{ getRelativeTime(selectedDevice.last_update) }}</p>
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-600 mb-1">Status Aktif</label>
              <p class="text-gray-900">
                <span v-if="selectedDevice.is_active" class="text-green-600">
                  <i class="fas fa-check-circle"></i> Aktif
                </span>
                <span v-else class="text-red-600">
                  <i class="fas fa-times-circle"></i> Nonaktif
                </span>
              </p>
            </div>
          </div>

          <!-- Close Button -->
          <div class="flex justify-end pt-4 border-t">
            <button
              @click="closeDeviceDetailModal"
              class="px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300"
            >
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
import { Chart, registerables } from 'chart.js';
import AppLayout from '@/Layouts/AppLayout.vue';
import SensorCard from '@/Components/SensorCard.vue';
import StatusBadge from '@/Components/StatusBadge.vue';
import DataTable from '@/Components/DataTable.vue';
import { useApi } from '@/Composables/useApi';
import { useAuth } from '@/Composables/useAuth';
import { getRelativeTime, getSensorStatus } from '@/Utils/helpers';

// Register Chart.js components
Chart.register(...registerables);

// Composables
const { getLatestData, getData, getDevices, getSites } = useApi();
const { filterSitesByUser } = useAuth();

// State
const latestData = ref(null);
const previousData = ref(null); // For trend calculation
const chartPeriod = ref('today');
const devices = ref([]);
const devicesLoading = ref(false);
const sites = ref([]);
const currentSite = ref(null);
const selectedSiteUid = ref('');

// Chart refs
const mainChartCanvas = ref(null);
const donutChartCanvas = ref(null);
let mainChart = null;
let donutChart = null;

// Auto-refresh interval
let refreshInterval = null;

// Device table columns
const deviceColumns = [
  { key: 'id', label: 'ID Perangkat', format: (val) => `#IOT-${String(val).padStart(3, '0')}` },
  { key: 'name', label: 'Nama' },
  { key: 'model', label: 'Tipe Sensor' },
  { key: 'last_update', label: 'Terakhir Update' },
  { key: 'status', label: 'Status' },
  { key: 'actions', label: 'Aksi' },
];

// Computed
const onlineDevices = computed(() => {
  return devices.value.filter(d => getDeviceStatus(d) === 'online').length;
});

const totalDevices = computed(() => devices.value.length);

// Load all available sites
const loadSites = async () => {
  try {
    const response = await getSites({ per_page: 100 });
    // Handle different possible response structures
    let sitesList = [];
    if (response && response.items) {
      sitesList = response.items;
    } else if (Array.isArray(response)) {
      sitesList = response;
    } else if (response && response.data) {
      sitesList = Array.isArray(response.data) ? response.data : [];
    } else {
      console.warn('Unexpected sites API response format:', response);
    }

    // Filter sites based on user permissions
    sites.value = filterSitesByUser(sitesList);

    // Auto-select first site if available
    if (sites.value.length > 0) {
      selectedSiteUid.value = sites.value[0].uid;
      currentSite.value = sites.value[0];
    }
  } catch (error) {
    console.error('Failed to load sites:', error);
  }
};

// Handle site selection change
const onSiteChange = async () => {
  const selected = sites.value.find(s => s.uid === selectedSiteUid.value);
  if (selected) {
    currentSite.value = selected;
    // Reload all data for the new site
    await loadLatestData();
    await loadDevices();
    await loadChartData();
    updateDonutChart();
  }
};

// Load latest sensor data
const loadLatestData = async () => {
  if (!currentSite.value) {
    console.warn('No site selected, cannot load latest data');
    return;
  }

  try {
    // Store previous data for trend calculation
    if (latestData.value) {
      previousData.value = { ...latestData.value };
    }

    // Fetch latest data from API
    const data = await getLatestData(currentSite.value.uid);
    console.log('Latest data received:', data);
    latestData.value = data;
  } catch (error) {
    if (error.response?.status === 403) {
      console.error('Access denied: You do not have permission to view this site');
      alert('Akses ditolak: Anda tidak memiliki izin untuk melihat data site ini');
      // Reset to first allowed site
      if (sites.value.length > 0) {
        selectedSiteUid.value = sites.value[0].uid;
        currentSite.value = sites.value[0];
      }
    } else {
      console.error('Failed to load latest data:', error);
    }
  }
};

// Load devices list
const loadDevices = async () => {
  if (!currentSite.value) return;

  devicesLoading.value = true;
  try {
    const response = await getDevices({ site_uid: currentSite.value.uid });
    // Handle different possible response structures
    let devicesList = [];
    if (response && response.items) {
      devicesList = response.items;
    } else if (Array.isArray(response)) {
      devicesList = response;
    } else if (response && response.data) {
      devicesList = Array.isArray(response.data) ? response.data : [];
    } else {
      console.warn('Unexpected devices API response format:', response);
    }

    // Filter only active devices and map with mock last_update for demo
    devices.value = devicesList
      .filter(device => device.is_active !== false)
      .map((device) => ({
        ...device,
        last_update: new Date(Date.now() - Math.random() * 600000).toISOString(),
      }));
  } catch (error) {
    if (error.response?.status === 403) {
      console.warn('Access denied to devices for this site');
      devices.value = [];
    } else {
      console.error('Failed to load devices:', error);
      devices.value = [];
    }
  } finally {
    devicesLoading.value = false;
  }
};

// Load chart data
const loadChartData = async () => {
  if (!currentSite.value) return;

  try {
    // Calculate date range based on period
    const now = new Date();
    let dateFrom;

    if (chartPeriod.value === 'today') {
      dateFrom = new Date(now.setHours(0, 0, 0, 0));
    } else if (chartPeriod.value === 'week') {
      dateFrom = new Date(now.setDate(now.getDate() - 7));
    } else {
      dateFrom = new Date(now.setMonth(now.getMonth() - 1));
    }

    // Fetch historical data from API
    const response = await getData({
      site_uid: currentSite.value.uid,
      date_from: dateFrom.toISOString(),
      fields: 'ph,tss,cod,nh3n',
      per_page: 100,
      order: 'asc',
    });

    // Handle different possible response structures
    let dataList = [];
    if (response && response.items) {
      dataList = response.items;
    } else if (Array.isArray(response)) {
      dataList = response;
    } else if (response && response.data) {
      dataList = Array.isArray(response.data) ? response.data : [];
    }

    updateMainChart(dataList);
  } catch (error) {
    if (error.response?.status === 403) {
      console.warn('Access denied to data for this site');
      updateMainChart([]); // Show empty chart
    } else {
      console.error('Failed to load chart data:', error);
    }
  }
};

// Update main line chart
const updateMainChart = (data) => {
  if (!mainChartCanvas.value) return;

  const labels = data.map((item) => {
    const date = new Date(item.ts);
    return date.toLocaleTimeString('id-ID', { hour: '2-digit', minute: '2-digit' });
  });

  const phData = data.map((item) => item.ph);
  const tssData = data.map((item) => item.tss);
  const codData = data.map((item) => item.cod);
  const nh3nData = data.map((item) => item.nh3n);

  if (mainChart) {
    mainChart.destroy();
  }

  const ctx = mainChartCanvas.value.getContext('2d');
  mainChart = new Chart(ctx, {
    type: 'line',
    data: {
      labels,
      datasets: [
        {
          label: 'pH',
          data: phData,
          borderColor: '#3b82f6',
          backgroundColor: 'rgba(59, 130, 246, 0.1)',
          tension: 0.4,
          fill: false,
        },
        {
          label: 'TSS (mg/L)',
          data: tssData,
          borderColor: '#f59e0b',
          backgroundColor: 'rgba(245, 158, 11, 0.1)',
          tension: 0.4,
          fill: false,
        },
        {
          label: 'COD (mg/L)',
          data: codData,
          borderColor: '#a855f7',
          backgroundColor: 'rgba(168, 85, 247, 0.1)',
          tension: 0.4,
          fill: false,
        },
        {
          label: 'NH3-N (mg/L)',
          data: nh3nData,
          borderColor: '#10b981',
          backgroundColor: 'rgba(16, 185, 129, 0.1)',
          tension: 0.4,
          fill: false,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { position: 'top' },
      },
      scales: {
        y: { beginAtZero: false },
      },
    },
  });
};

// Update donut chart
const updateDonutChart = () => {
  if (!donutChartCanvas.value) return;

  const ctx = donutChartCanvas.value.getContext('2d');

  if (donutChart) {
    donutChart.destroy();
  }

  donutChart = new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels: ['pH', 'TSS', 'COD', 'NH3-N'],
      datasets: [
        {
          data: [
            latestData.value?.ph || 7,
            latestData.value?.tss || 25,
            latestData.value?.cod || 80,
            latestData.value?.nh3n || 5,
          ],
          backgroundColor: ['#3b82f6', '#f59e0b', '#a855f7', '#10b981'],
          borderWidth: 0,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          position: 'right',
          labels: { boxWidth: 10, font: { size: 10 } },
        },
      },
    },
  });
};

// Calculate trend percentage
const getTrend = (field) => {
  if (!latestData.value || !previousData.value) return null;

  const current = latestData.value[field];
  const previous = previousData.value[field];

  if (current == null || previous == null || previous === 0) return null;

  return ((current - previous) / previous) * 100;
};

// Get device status based on last update
const getDeviceStatus = (device) => {
  return getSensorStatus(device.last_update);
};

const getDeviceStatusLabel = (device) => {
  const status = getDeviceStatus(device);
  if (status === 'online') return 'Aktif';
  if (status === 'warning') return 'Sleep';
  return 'Offline';
};

// Device detail modal
const showDeviceDetailModal = ref(false);
const selectedDevice = ref(null);

// View device detail
const viewDeviceDetail = (device) => {
  selectedDevice.value = device;
  showDeviceDetailModal.value = true;
};

const closeDeviceDetailModal = () => {
  showDeviceDetailModal.value = false;
  selectedDevice.value = null;
};

// Initialize dashboard
const initDashboard = async () => {
  await loadSites();
  await loadLatestData();
  await loadDevices();
  await loadChartData();
  updateDonutChart();
};

// Setup auto-refresh
const setupAutoRefresh = () => {
  refreshInterval = setInterval(async () => {
    await loadLatestData();
    updateDonutChart();
  }, 30000); // Refresh every 30 seconds
};

// Lifecycle hooks
onMounted(async () => {
  await initDashboard();
  setupAutoRefresh();
});

onUnmounted(() => {
  if (refreshInterval) {
    clearInterval(refreshInterval);
  }
  if (mainChart) {
    mainChart.destroy();
  }
  if (donutChart) {
    donutChart.destroy();
  }
});
</script>
