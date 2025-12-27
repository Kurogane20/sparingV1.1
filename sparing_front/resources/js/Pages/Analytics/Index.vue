<template>
  <AppLayout>
    <div ref="reportContent" class="space-y-4 md:space-y-6">
      <!-- Page Header -->
      <div class="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3">
        <div>
          <h2 class="text-xl md:text-2xl font-bold text-gray-900">Analisis Data</h2>
          <p class="text-gray-600 text-xs md:text-sm mt-1">
            Analisis mendalam kualitas air limbah dengan visualisasi data
          </p>
        </div>
        <button
          @click="exportReport"
          :disabled="exporting || !filters.siteUid"
          class="px-4 py-2 bg-primary text-white rounded-lg hover:bg-opacity-90 flex items-center gap-2 text-sm disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <i :class="exporting ? 'fas fa-spinner fa-spin' : 'fas fa-file-pdf'"></i>
          {{ exporting ? 'Mengunduh...' : 'Unduh PDF' }}
        </button>
      </div>

      <!-- Filter Controls -->
      <div class="bg-white rounded-xl md:rounded-2xl p-4 md:p-6 shadow-sm">
        <h3 class="text-base md:text-lg font-semibold text-gray-900 mb-4">
          <i class="fas fa-sliders-h text-primary mr-2"></i>
          Pengaturan Analisis
        </h3>
        <div class="grid grid-cols-2 md:grid-cols-4 gap-3 md:gap-4">
          <div>
            <label class="block text-xs md:text-sm font-medium text-gray-700 mb-2">Lokasi</label>
            <select
              v-model="filters.siteUid"
              @change="loadAnalytics"
              class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary text-sm"
            >
              <option value="">Pilih Lokasi</option>
              <option v-for="site in sites" :key="site.uid" :value="site.uid">
                {{ site.name }}
              </option>
            </select>
          </div>
          <div>
            <label class="block text-xs md:text-sm font-medium text-gray-700 mb-2">Periode</label>
            <select
              v-model="filters.period"
              @change="loadAnalytics"
              class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary text-sm"
            >
              <option value="day">Harian</option>
              <option value="week">Mingguan</option>
              <option value="month">Bulanan</option>
            </select>
          </div>
          <div>
            <label class="block text-xs md:text-sm font-medium text-gray-700 mb-2">Dari</label>
            <input
              v-model="filters.dateFrom"
              type="date"
              @change="loadAnalytics"
              class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary text-sm"
            />
          </div>
          <div>
            <label class="block text-xs md:text-sm font-medium text-gray-700 mb-2">Sampai</label>
            <input
              v-model="filters.dateTo"
              type="date"
              @change="loadAnalytics"
              class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary text-sm"
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

      <!-- Statistics Cards -->
      <div v-else-if="filters.siteUid" class="grid grid-cols-2 md:grid-cols-4 gap-3 md:gap-6">
        <div class="bg-white rounded-xl md:rounded-2xl p-4 md:p-6 shadow-sm">
          <div class="flex items-center justify-between mb-2">
            <span class="text-xs md:text-sm text-gray-600">Rata-rata pH</span>
            <i class="fas fa-flask text-blue-600"></i>
          </div>
          <div class="text-xl md:text-2xl font-bold text-gray-900">{{ formatNumber(stats.ph.avg, 2) }}</div>
          <div class="text-xs text-gray-500 mt-1">
            Min: {{ formatNumber(stats.ph.min, 2) }} | Max: {{ formatNumber(stats.ph.max, 2) }}
          </div>
        </div>

        <div class="bg-white rounded-xl md:rounded-2xl p-4 md:p-6 shadow-sm">
          <div class="flex items-center justify-between mb-2">
            <span class="text-xs md:text-sm text-gray-600">Rata-rata TSS</span>
            <i class="fas fa-filter text-sky-500"></i>
          </div>
          <div class="text-xl md:text-2xl font-bold text-gray-900">{{ formatNumber(stats.tss.avg, 1) }} <span class="text-sm font-normal">mg/L</span></div>
          <div class="text-xs text-gray-500 mt-1">
            Min: {{ formatNumber(stats.tss.min, 1) }} | Max: {{ formatNumber(stats.tss.max, 1) }}
          </div>
        </div>

        <div class="bg-white rounded-xl md:rounded-2xl p-4 md:p-6 shadow-sm">
          <div class="flex items-center justify-between mb-2">
            <span class="text-xs md:text-sm text-gray-600">Rata-rata COD</span>
            <i class="fas fa-vial text-indigo-500"></i>
          </div>
          <div class="text-xl md:text-2xl font-bold text-gray-900">{{ formatNumber(stats.cod.avg, 1) }} <span class="text-sm font-normal">mg/L</span></div>
          <div class="text-xs text-gray-500 mt-1">
            Min: {{ formatNumber(stats.cod.min, 1) }} | Max: {{ formatNumber(stats.cod.max, 1) }}
          </div>
        </div>

        <div class="bg-white rounded-xl md:rounded-2xl p-4 md:p-6 shadow-sm">
          <div class="flex items-center justify-between mb-2">
            <span class="text-xs md:text-sm text-gray-600">Rata-rata NH3-N</span>
            <i class="fas fa-atom text-emerald-500"></i>
          </div>
          <div class="text-xl md:text-2xl font-bold text-gray-900">{{ formatNumber(stats.nh3n.avg, 2) }} <span class="text-sm font-normal">mg/L</span></div>
          <div class="text-xs text-gray-500 mt-1">
            Min: {{ formatNumber(stats.nh3n.min, 2) }} | Max: {{ formatNumber(stats.nh3n.max, 2) }}
          </div>
        </div>
      </div>

      <!-- Empty State -->
      <div v-else class="bg-white rounded-2xl p-12 shadow-sm text-center">
        <i class="fas fa-chart-bar text-6xl text-gray-300 mb-4"></i>
        <h3 class="text-xl font-semibold text-gray-700 mb-2">Pilih Lokasi</h3>
        <p class="text-gray-500">Silakan pilih lokasi untuk melihat analisis data</p>
      </div>

      <!-- Charts Grid -->
      <div v-if="filters.siteUid && !loading" class="grid grid-cols-1 lg:grid-cols-2 gap-4 md:gap-6">
        <!-- Water Quality Trend Chart -->
        <div class="bg-white rounded-xl md:rounded-2xl p-4 md:p-6 shadow-sm">
          <h3 class="text-base md:text-lg font-semibold text-gray-900 mb-4">Tren Parameter Air</h3>
          <div class="h-64 md:h-80">
            <apexchart
              v-if="trendOptions"
              type="area"
              height="100%"
              :options="trendOptions"
              :series="trendSeries"
            />
          </div>
        </div>

        <!-- Comparison Bar Chart -->
        <div class="bg-white rounded-xl md:rounded-2xl p-4 md:p-6 shadow-sm">
          <h3 class="text-base md:text-lg font-semibold text-gray-900 mb-4">Perbandingan Rata-rata</h3>
          <div class="h-64 md:h-80">
            <apexchart
              v-if="barOptions"
              type="bar"
              height="100%"
              :options="barOptions"
              :series="barSeries"
            />
          </div>
        </div>
      </div>

      <!-- Compliance Analysis -->
      <div v-if="filters.siteUid && !loading" class="bg-white rounded-xl md:rounded-2xl p-4 md:p-6 shadow-sm">
        <h3 class="text-base md:text-lg font-semibold text-gray-900 mb-4">Analisis Kepatuhan Baku Mutu</h3>
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 md:gap-6">
          <div v-for="param in complianceParams" :key="param.key">
            <h4 class="text-sm font-medium text-gray-700 mb-3">Parameter {{ param.label }}</h4>
            <div class="space-y-2">
              <div class="flex justify-between items-center">
                <span class="text-xs text-gray-600">{{ param.standard }}</span>
                <span :class="['text-sm font-medium', getComplianceColor(param.compliance)]">
                  {{ param.compliance }}% Sesuai
                </span>
              </div>
              <div class="w-full bg-gray-200 rounded-full h-2">
                <div
                  :class="['h-2 rounded-full transition-all duration-500', getComplianceBgColor(param.compliance)]"
                  :style="{ width: `${param.compliance}%` }"
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
import { ref, computed, onMounted } from 'vue';
import VueApexCharts from 'vue3-apexcharts';
import { jsPDF } from 'jspdf';
import html2canvas from 'html2canvas';
import AppLayout from '@/Layouts/AppLayout.vue';
import { useApi } from '@/Composables/useApi';
import { useAuth } from '@/Composables/useAuth';
import { formatNumber } from '@/Utils/helpers';

const apexchart = VueApexCharts;

// Colors
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

const { getSites, getSiteMetrics, getData } = useApi();
const { filterSitesByUser } = useAuth();

// Refs
const reportContent = ref(null);
const exporting = ref(false);

// State
const sites = ref([]);
const loading = ref(false);
const chartData = ref([]);
const filters = ref({
  siteUid: '',
  period: 'week',
  dateFrom: getDefaultDateFrom(),
  dateTo: getDefaultDateTo(),
});

const stats = ref({
  ph: { avg: 0, min: 0, max: 0 },
  tss: { avg: 0, min: 0, max: 0 },
  cod: { avg: 0, min: 0, max: 0 },
  nh3n: { avg: 0, min: 0, max: 0 },
});

function getDefaultDateFrom() {
  const date = new Date();
  date.setDate(date.getDate() - 7);
  return date.toISOString().split('T')[0];
}

function getDefaultDateTo() {
  return new Date().toISOString().split('T')[0];
}

// Trend Chart Options
const trendOptions = computed(() => ({
  chart: {
    type: 'area',
    toolbar: { show: false },
    zoom: { enabled: false },
    animations: { enabled: true, speed: 800 },
    fontFamily: 'Inter, sans-serif',
  },
  colors: [colors.ph, colors.tss, colors.cod, colors.nh3n],
  dataLabels: { enabled: false },
  stroke: { curve: 'smooth', width: 2 },
  fill: {
    type: 'gradient',
    gradient: { shadeIntensity: 1, opacityFrom: 0.4, opacityTo: 0.1 },
  },
  xaxis: {
    type: 'datetime',
    labels: { style: { colors: '#64748b', fontSize: '10px' } },
  },
  yaxis: { labels: { style: { colors: '#64748b' } } },
  legend: { position: 'top', fontSize: '11px' },
  tooltip: { x: { format: 'dd MMM HH:mm' } },
  grid: { borderColor: '#e2e8f0', strokeDashArray: 4 },
  responsive: [{ breakpoint: 768, options: { legend: { fontSize: '10px' } } }],
}));

const trendSeries = computed(() => [
  { name: 'pH', data: chartData.value.map(d => ({ x: new Date(d.ts), y: d.ph })) },
  { name: 'TSS', data: chartData.value.map(d => ({ x: new Date(d.ts), y: d.tss })) },
  { name: 'COD', data: chartData.value.map(d => ({ x: new Date(d.ts), y: d.cod })) },
  { name: 'NH3-N', data: chartData.value.map(d => ({ x: new Date(d.ts), y: d.nh3n })) },
]);

// Bar Chart Options
const barOptions = computed(() => ({
  chart: {
    type: 'bar',
    toolbar: { show: false },
    fontFamily: 'Inter, sans-serif',
  },
  colors: [colors.ph, colors.tss, colors.cod, colors.nh3n, colors.debit, colors.voltage, colors.current, colors.temp],
  plotOptions: {
    bar: {
      borderRadius: 8,
      horizontal: false,
      columnWidth: '60%',
      distributed: true,
    },
  },
  dataLabels: { enabled: false },
  xaxis: {
    categories: ['pH', 'TSS', 'COD', 'NH3-N', 'Debit', 'Voltage', 'Current', 'Temp'],
    labels: { style: { colors: '#64748b', fontSize: '10px' } },
  },
  yaxis: { labels: { style: { colors: '#64748b' } } },
  legend: { show: false },
  grid: { borderColor: '#e2e8f0' },
}));

const barSeries = computed(() => [{
  name: 'Rata-rata',
  data: [
    stats.value.ph.avg,
    stats.value.tss.avg,
    stats.value.cod.avg,
    stats.value.nh3n.avg,
    stats.value.debit?.avg || 0,
    stats.value.voltage?.avg || 0,
    stats.value.current?.avg || 0,
    stats.value.temp?.avg || 0,
  ],
}]);

// Compliance params
const complianceParams = computed(() => [
  { key: 'ph', label: 'pH', standard: 'Baku: 6.0 - 9.0', compliance: calculateCompliance('ph', stats.value.ph) },
  { key: 'tss', label: 'TSS', standard: 'Baku: < 100 mg/L', compliance: calculateCompliance('tss', stats.value.tss) },
  { key: 'cod', label: 'COD', standard: 'Baku: < 200 mg/L', compliance: calculateCompliance('cod', stats.value.cod) },
  { key: 'nh3n', label: 'NH3-N', standard: 'Baku: < 10 mg/L', compliance: calculateCompliance('nh3n', stats.value.nh3n) },
]);

const calculateCompliance = (param, data) => {
  if (!data || !data.avg) return 0;
  const standards = { ph: { min: 6.0, max: 9.0 }, tss: { max: 100 }, cod: { max: 200 }, nh3n: { max: 10 } };
  const std = standards[param];
  if (!std) return 100;
  if (std.min !== undefined && std.max !== undefined) {
    return data.avg >= std.min && data.avg <= std.max ? 95 : 70;
  }
  return data.avg <= std.max ? 95 : 70;
};

const getComplianceColor = (c) => c >= 90 ? 'text-emerald-600' : c >= 70 ? 'text-amber-600' : 'text-red-600';
const getComplianceBgColor = (c) => c >= 90 ? 'bg-emerald-500' : c >= 70 ? 'bg-amber-500' : 'bg-red-500';

const loadSites = async () => {
  try {
    const response = await getSites({ per_page: 100 });
    let sitesList = response?.items || (Array.isArray(response) ? response : response?.data || []);
    sites.value = filterSitesByUser(sitesList);
    if (sites.value.length > 0 && !filters.value.siteUid) {
      filters.value.siteUid = sites.value[0].uid;
    }
  } catch (error) {
    console.error('Failed to load sites:', error);
  }
};

const loadAnalytics = async () => {
  if (!filters.value.siteUid) return;
  loading.value = true;
  try {
    const endDate = new Date(filters.value.dateTo);
    endDate.setDate(endDate.getDate() + 1);
    
    const metrics = await getSiteMetrics(filters.value.siteUid, {
      date_from: filters.value.dateFrom,
      date_to: endDate.toISOString().split('T')[0],
      fields: 'ph,tss,cod,nh3n,debit,voltage,current,temp',
    });
    
    stats.value = {
      ph: metrics.metrics?.ph || { avg: 0, min: 0, max: 0 },
      tss: metrics.metrics?.tss || { avg: 0, min: 0, max: 0 },
      cod: metrics.metrics?.cod || { avg: 0, min: 0, max: 0 },
      nh3n: metrics.metrics?.nh3n || { avg: 0, min: 0, max: 0 },
      debit: metrics.metrics?.debit || { avg: 0, min: 0, max: 0 },
      voltage: metrics.metrics?.voltage || { avg: 0, min: 0, max: 0 },
      current: metrics.metrics?.current || { avg: 0, min: 0, max: 0 },
      temp: metrics.metrics?.temp || { avg: 0, min: 0, max: 0 },
    };
    
    // Load chart data
    const response = await getData({
      site_uid: filters.value.siteUid,
      date_from: filters.value.dateFrom,
      date_to: endDate.toISOString().split('T')[0],
      fields: 'ph,tss,cod,nh3n',
      per_page: 100,
      order: 'asc',
    });
    chartData.value = response?.items || (Array.isArray(response) ? response : []);
  } catch (error) {
    console.error('Failed to load analytics:', error);
  } finally {
    loading.value = false;
  }
};

const exportReport = async () => {
  if (!reportContent.value || exporting.value) return;
  
  exporting.value = true;
  try {
    // Get site name
    const siteName = sites.value.find(s => s.uid === filters.value.siteUid)?.name || 'Unknown';
    
    // Create canvas from report content
    const canvas = await html2canvas(reportContent.value, {
      scale: 2,
      useCORS: true,
      logging: false,
      backgroundColor: '#f8fafc',
    });
    
    // Create PDF
    const imgData = canvas.toDataURL('image/png');
    const pdf = new jsPDF({
      orientation: 'portrait',
      unit: 'mm',
      format: 'a4',
    });
    
    const pageWidth = pdf.internal.pageSize.getWidth();
    const pageHeight = pdf.internal.pageSize.getHeight();
    const imgWidth = pageWidth - 20;
    const imgHeight = (canvas.height * imgWidth) / canvas.width;
    
    // Add header
    pdf.setFontSize(18);
    pdf.setTextColor(30, 64, 175);
    pdf.text('Laporan Analisis Data', pageWidth / 2, 15, { align: 'center' });
    
    pdf.setFontSize(10);
    pdf.setTextColor(100);
    pdf.text(`Lokasi: ${siteName}`, pageWidth / 2, 22, { align: 'center' });
    pdf.text(`Periode: ${filters.value.dateFrom} s/d ${filters.value.dateTo}`, pageWidth / 2, 27, { align: 'center' });
    pdf.text(`Dicetak: ${new Date().toLocaleString('id-ID')}`, pageWidth / 2, 32, { align: 'center' });
    
    // Add image
    let yPosition = 38;
    if (imgHeight <= pageHeight - yPosition - 10) {
      pdf.addImage(imgData, 'PNG', 10, yPosition, imgWidth, imgHeight);
    } else {
      // Multi-page
      let remainingHeight = imgHeight;
      let sourceY = 0;
      while (remainingHeight > 0) {
        const sliceHeight = Math.min(pageHeight - yPosition - 10, remainingHeight);
        pdf.addImage(imgData, 'PNG', 10, yPosition, imgWidth, imgHeight, undefined, 'FAST', 0);
        remainingHeight -= sliceHeight;
        if (remainingHeight > 0) {
          pdf.addPage();
          yPosition = 10;
        }
      }
    }
    
    // Save PDF
    const filename = `laporan-analisis-${siteName}-${filters.value.dateFrom}.pdf`;
    pdf.save(filename);
  } catch (error) {
    console.error('Failed to export PDF:', error);
    alert('Gagal mengekspor PDF. Silakan coba lagi.');
  } finally {
    exporting.value = false;
  }
};

onMounted(async () => {
  await loadSites();
  await loadAnalytics();
});
</script>
