<template>
  <AppLayout>
    <div class="space-y-6">
      <!-- Page Header -->
      <div class="flex justify-between items-center">
        <div>
          <h2 class="text-2xl font-bold text-gray-900">Analisis Data</h2>
          <p class="text-gray-600 text-sm mt-1">
            Analisis mendalam kualitas air limbah dengan visualisasi data
          </p>
        </div>
        <button
          @click="exportReport"
          class="px-4 py-2 bg-primary text-white rounded-lg hover:bg-opacity-90 flex items-center gap-2"
        >
          <i class="fas fa-file-pdf"></i>
          Unduh Laporan PDF
        </button>
      </div>

      <!-- Filter Controls -->
      <div class="bg-white rounded-2xl p-6 shadow-sm">
        <h3 class="text-lg font-semibold text-gray-900 mb-4">
          <i class="fas fa-sliders-h text-primary mr-2"></i>
          Pengaturan Analisis
        </h3>

        <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-2">
              <i class="fas fa-map-marker-alt text-primary mr-1"></i>
              Lokasi
            </label>
            <select
              v-model="filters.siteUid"
              @change="loadAnalytics"
              class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary"
            >
              <option value="">Pilih Lokasi</option>
              <option v-for="site in sites" :key="site.uid" :value="site.uid">
                {{ site.name }} - {{ site.company_name }}
              </option>
            </select>
          </div>

          <div>
            <label class="block text-sm font-medium text-gray-700 mb-2">Periode</label>
            <select
              v-model="filters.period"
              @change="loadAnalytics"
              class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary"
            >
              <option value="day">Harian</option>
              <option value="week">Mingguan</option>
              <option value="month">Bulanan</option>
              <option value="year">Tahunan</option>
            </select>
          </div>

          <div>
            <label class="block text-sm font-medium text-gray-700 mb-2">Dari Tanggal</label>
            <input
              v-model="filters.dateFrom"
              type="date"
              @change="loadAnalytics"
              class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary"
            />
          </div>

          <div>
            <label class="block text-sm font-medium text-gray-700 mb-2">Sampai Tanggal</label>
            <input
              v-model="filters.dateTo"
              type="date"
              @change="loadAnalytics"
              class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary"
            />
          </div>
        </div>
      </div>

      <!-- Loading State -->
      <div v-if="loading" class="flex justify-center items-center py-12">
        <div class="text-center">
          <i class="fas fa-spinner fa-spin text-4xl text-primary mb-4"></i>
          <p class="text-gray-600">Memuat data analisis...</p>
        </div>
      </div>

      <!-- Empty State -->
      <div v-else-if="!filters.siteUid" class="bg-white rounded-2xl p-12 shadow-sm text-center">
        <i class="fas fa-chart-bar text-6xl text-gray-300 mb-4"></i>
        <h3 class="text-xl font-semibold text-gray-700 mb-2">Pilih Lokasi</h3>
        <p class="text-gray-500">Silakan pilih lokasi untuk melihat analisis data</p>
      </div>

      <!-- Statistics Cards -->
      <div v-else class="grid grid-cols-1 md:grid-cols-4 gap-6">
        <div class="bg-white rounded-2xl p-6 shadow-sm">
          <div class="flex items-center justify-between mb-2">
            <span class="text-sm text-gray-600">Rata-rata pH</span>
            <i class="fas fa-flask text-blue-500"></i>
          </div>
          <div class="text-2xl font-bold text-gray-900">{{ formatNumber(stats.ph.avg, 2) }}</div>
          <div class="text-xs text-gray-500 mt-1">
            Min: {{ formatNumber(stats.ph.min, 2) }} | Max: {{ formatNumber(stats.ph.max, 2) }}
          </div>
        </div>

        <div class="bg-white rounded-2xl p-6 shadow-sm">
          <div class="flex items-center justify-between mb-2">
            <span class="text-sm text-gray-600">Rata-rata TSS</span>
            <i class="fas fa-filter text-amber-500"></i>
          </div>
          <div class="text-2xl font-bold text-gray-900">{{ formatNumber(stats.tss.avg, 1) }} mg/L</div>
          <div class="text-xs text-gray-500 mt-1">
            Min: {{ formatNumber(stats.tss.min, 1) }} | Max: {{ formatNumber(stats.tss.max, 1) }}
          </div>
        </div>

        <div class="bg-white rounded-2xl p-6 shadow-sm">
          <div class="flex items-center justify-between mb-2">
            <span class="text-sm text-gray-600">Rata-rata COD</span>
            <i class="fas fa-vial text-purple-500"></i>
          </div>
          <div class="text-2xl font-bold text-gray-900">{{ formatNumber(stats.cod.avg, 1) }} mg/L</div>
          <div class="text-xs text-gray-500 mt-1">
            Min: {{ formatNumber(stats.cod.min, 1) }} | Max: {{ formatNumber(stats.cod.max, 1) }}
          </div>
        </div>

        <div class="bg-white rounded-2xl p-6 shadow-sm">
          <div class="flex items-center justify-between mb-2">
            <span class="text-sm text-gray-600">Rata-rata NH3-N</span>
            <i class="fas fa-atom text-green-500"></i>
          </div>
          <div class="text-2xl font-bold text-gray-900">{{ formatNumber(stats.nh3n.avg, 2) }} mg/L</div>
          <div class="text-xs text-gray-500 mt-1">
            Min: {{ formatNumber(stats.nh3n.min, 2) }} | Max: {{ formatNumber(stats.nh3n.max, 2) }}
          </div>
        </div>
      </div>

      <!-- Charts Grid -->
      <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <!-- Trend Chart -->
        <div class="bg-white rounded-2xl p-6 shadow-sm">
          <h3 class="text-lg font-semibold text-gray-900 mb-4">Tren Parameter</h3>
          <div class="relative h-80">
            <canvas ref="trendChartCanvas"></canvas>
          </div>
        </div>

        <!-- Bar Chart Comparison -->
        <div class="bg-white rounded-2xl p-6 shadow-sm">
          <h3 class="text-lg font-semibold text-gray-900 mb-4">Perbandingan Rata-rata</h3>
          <div class="relative h-80">
            <canvas ref="barChartCanvas"></canvas>
          </div>
        </div>
      </div>

      <!-- Compliance Analysis -->
      <div class="bg-white rounded-2xl p-6 shadow-sm">
        <h3 class="text-lg font-semibold text-gray-900 mb-4">Analisis Kepatuhan Baku Mutu</h3>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <h4 class="text-sm font-medium text-gray-700 mb-3">Parameter pH</h4>
            <div class="space-y-2">
              <div class="flex justify-between items-center">
                <span class="text-sm text-gray-600">Baku Mutu: 6.0 - 9.0</span>
                <span :class="['text-sm font-medium', getComplianceColor(stats.ph.compliance)]">
                  {{ stats.ph.compliance }}% Sesuai
                </span>
              </div>
              <div class="w-full bg-gray-200 rounded-full h-2">
                <div
                  :class="['h-2 rounded-full', getComplianceColor(stats.ph.compliance)]"
                  :style="{ width: `${stats.ph.compliance}%` }"
                ></div>
              </div>
            </div>
          </div>

          <div>
            <h4 class="text-sm font-medium text-gray-700 mb-3">Parameter TSS</h4>
            <div class="space-y-2">
              <div class="flex justify-between items-center">
                <span class="text-sm text-gray-600">Baku Mutu: &lt; 100 mg/L</span>
                <span :class="['text-sm font-medium', getComplianceColor(stats.tss.compliance)]">
                  {{ stats.tss.compliance }}% Sesuai
                </span>
              </div>
              <div class="w-full bg-gray-200 rounded-full h-2">
                <div
                  :class="['h-2 rounded-full', getComplianceColor(stats.tss.compliance)]"
                  :style="{ width: `${stats.tss.compliance}%` }"
                ></div>
              </div>
            </div>
          </div>

          <div>
            <h4 class="text-sm font-medium text-gray-700 mb-3">Parameter COD</h4>
            <div class="space-y-2">
              <div class="flex justify-between items-center">
                <span class="text-sm text-gray-600">Baku Mutu: &lt; 200 mg/L</span>
                <span :class="['text-sm font-medium', getComplianceColor(stats.cod.compliance)]">
                  {{ stats.cod.compliance }}% Sesuai
                </span>
              </div>
              <div class="w-full bg-gray-200 rounded-full h-2">
                <div
                  :class="['h-2 rounded-full', getComplianceColor(stats.cod.compliance)]"
                  :style="{ width: `${stats.cod.compliance}%` }"
                ></div>
              </div>
            </div>
          </div>

          <div>
            <h4 class="text-sm font-medium text-gray-700 mb-3">Parameter NH3-N</h4>
            <div class="space-y-2">
              <div class="flex justify-between items-center">
                <span class="text-sm text-gray-600">Baku Mutu: &lt; 10 mg/L</span>
                <span :class="['text-sm font-medium', getComplianceColor(stats.nh3n.compliance)]">
                  {{ stats.nh3n.compliance }}% Sesuai
                </span>
              </div>
              <div class="w-full bg-gray-200 rounded-full h-2">
                <div
                  :class="['h-2 rounded-full', getComplianceColor(stats.nh3n.compliance)]"
                  :style="{ width: `${stats.nh3n.compliance}%` }"
                ></div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </AppLayout>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue';
import { Chart, registerables } from 'chart.js';
import AppLayout from '@/Layouts/AppLayout.vue';
import { useApi } from '@/Composables/useApi';
import { useAuth } from '@/Composables/useAuth';
import { formatNumber } from '@/Utils/helpers';

Chart.register(...registerables);

const { getSites, getSiteMetrics } = useApi();
const { filterSitesByUser } = useAuth();

// State
const sites = ref([]);
const loading = ref(false);
const filters = ref({
  siteUid: '',
  period: 'week',
  dateFrom: getDefaultDateFrom(),
  dateTo: getDefaultDateTo(),
});

const stats = ref({
  ph: { avg: 0, min: 0, max: 0, compliance: 0 },
  tss: { avg: 0, min: 0, max: 0, compliance: 0 },
  cod: { avg: 0, min: 0, max: 0, compliance: 0 },
  nh3n: { avg: 0, min: 0, max: 0, compliance: 0 },
});

// Chart refs
const trendChartCanvas = ref(null);
const barChartCanvas = ref(null);
let trendChart = null;
let barChart = null;

function getDefaultDateFrom() {
  const date = new Date();
  date.setDate(date.getDate() - 7);
  return date.toISOString().split('T')[0];
}

function getDefaultDateTo() {
  return new Date().toISOString().split('T')[0];
}

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
      // Handle { data: [...] } structure
      sitesList = Array.isArray(response.data) ? response.data : [];
    } else {
      sitesList = [];
      console.warn('Unexpected API response format:', response);
    }

    // Filter sites based on user permissions
    sites.value = filterSitesByUser(sitesList);

    // Auto-select first site and load analytics
    if (sites.value.length > 0 && !filters.value.siteUid) {
      filters.value.siteUid = sites.value[0].uid;
      await loadAnalytics();
    }
  } catch (error) {
    console.error('Failed to load sites:', error);
    sites.value = [];
  }
};

const loadAnalytics = async () => {
  if (!filters.value.siteUid) return;

  loading.value = true;
  try {
    const params = {
      date_from: filters.value.dateFrom,
      // Add 1 day to include all data from end date
      date_to: (() => {
        const endDate = new Date(filters.value.dateTo);
        endDate.setDate(endDate.getDate() + 1);
        return endDate.toISOString().split('T')[0];
      })(),
      fields: 'ph,tss,cod,nh3n',
    };

    const metrics = await getSiteMetrics(filters.value.siteUid, params);

    // Update stats
    stats.value = {
      ph: {
        avg: metrics.metrics?.ph?.avg || 0,
        min: metrics.metrics?.ph?.min || 0,
        max: metrics.metrics?.ph?.max || 0,
        compliance: calculateCompliance('ph', metrics.metrics?.ph),
      },
      tss: {
        avg: metrics.metrics?.tss?.avg || 0,
        min: metrics.metrics?.tss?.min || 0,
        max: metrics.metrics?.tss?.max || 0,
        compliance: calculateCompliance('tss', metrics.metrics?.tss),
      },
      cod: {
        avg: metrics.metrics?.cod?.avg || 0,
        min: metrics.metrics?.cod?.min || 0,
        max: metrics.metrics?.cod?.max || 0,
        compliance: calculateCompliance('cod', metrics.metrics?.cod),
      },
      nh3n: {
        avg: metrics.metrics?.nh3n?.avg || 0,
        min: metrics.metrics?.nh3n?.min || 0,
        max: metrics.metrics?.nh3n?.max || 0,
        compliance: calculateCompliance('nh3n', metrics.metrics?.nh3n),
      },
    };

    updateCharts();
  } catch (error) {
    console.error('Failed to load analytics:', error);
  } finally {
    loading.value = false;
  }
};

const calculateCompliance = (parameter, data) => {
  if (!data) return 0;

  // Simple compliance calculation based on standards
  const standards = {
    ph: { min: 6.0, max: 9.0 },
    tss: { max: 100 },
    cod: { max: 200 },
    nh3n: { max: 10 },
  };

  const std = standards[parameter];
  if (!std) return 100;

  if (std.min !== undefined && std.max !== undefined) {
    // Range check (pH)
    return data.avg >= std.min && data.avg <= std.max ? 95 : 70;
  } else {
    // Max check
    return data.avg <= std.max ? 95 : 70;
  }
};

const getComplianceColor = (compliance) => {
  if (compliance >= 90) return 'text-green-600 bg-green-600';
  if (compliance >= 70) return 'text-yellow-600 bg-yellow-600';
  return 'text-red-600 bg-red-600';
};

const updateCharts = () => {
  updateTrendChart();
  updateBarChart();
};

const updateTrendChart = () => {
  if (!trendChartCanvas.value) return;

  if (trendChart) trendChart.destroy();

  const ctx = trendChartCanvas.value.getContext('2d');
  trendChart = new Chart(ctx, {
    type: 'line',
    data: {
      labels: ['Min', 'Avg', 'Max'],
      datasets: [
        {
          label: 'pH',
          data: [stats.value.ph.min, stats.value.ph.avg, stats.value.ph.max],
          borderColor: '#3b82f6',
          backgroundColor: 'rgba(59, 130, 246, 0.1)',
        },
        {
          label: 'TSS',
          data: [stats.value.tss.min, stats.value.tss.avg, stats.value.tss.max],
          borderColor: '#f59e0b',
          backgroundColor: 'rgba(245, 158, 11, 0.1)',
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
    },
  });
};

const updateBarChart = () => {
  if (!barChartCanvas.value) return;

  if (barChart) barChart.destroy();

  const ctx = barChartCanvas.value.getContext('2d');
  barChart = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: ['pH', 'TSS', 'COD', 'NH3-N'],
      datasets: [
        {
          label: 'Rata-rata',
          data: [
            stats.value.ph.avg,
            stats.value.tss.avg,
            stats.value.cod.avg,
            stats.value.nh3n.avg,
          ],
          backgroundColor: ['#3b82f6', '#f59e0b', '#a855f7', '#10b981'],
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
    },
  });
};

const exportReport = () => {
  alert('Fitur export PDF akan segera tersedia');
};

onMounted(async () => {
  await loadSites();
  await loadAnalytics();
});

onUnmounted(() => {
  if (trendChart) trendChart.destroy();
  if (barChart) barChart.destroy();
});
</script>
