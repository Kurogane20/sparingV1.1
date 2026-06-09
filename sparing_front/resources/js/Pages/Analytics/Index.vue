<template>
  <AppLayout>
    <div ref="reportContent" class="space-y-4 md:space-y-6">
      <!-- Page Header -->
      <div class="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3">
        <div>
          <h2 class="text-xl font-bold text-slate-800">Analisis Data</h2>
          <p class="text-slate-500 text-sm mt-0.5">Analisis mendalam kualitas air limbah</p>
        </div>
        <div class="flex gap-2">
          <button
            @click="exportCsv"
            :disabled="!chartData.length || !filters.siteUid"
            class="btn-secondary flex items-center gap-2 text-sm disabled:opacity-50 disabled:cursor-not-allowed"
            style="color:#059669; border-color:#6ee7b7;"
          >
            <i class="fas fa-file-csv"></i>CSV
          </button>
          <button
            @click="exportReport"
            :disabled="exporting || !filters.siteUid"
            class="btn-primary flex items-center gap-2 text-sm disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <i :class="exporting ? 'fas fa-spinner fa-spin' : 'fas fa-file-pdf'"></i>
            {{ exporting ? 'Mengunduh...' : 'PDF' }}
          </button>
        </div>
      </div>

      <!-- Filter Controls -->
      <div class="card p-4 md:p-5">
        <h3 class="card-title mb-4">Pengaturan Analisis</h3>
        <div class="grid grid-cols-2 md:grid-cols-4 gap-3 md:gap-4">
          <div>
            <label class="block text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1.5">Lokasi</label>
            <select v-model="filters.siteUid" @change="loadAnalytics" class="form-input text-sm">
              <option value="">Pilih Lokasi</option>
              <option v-for="site in sites" :key="site.uid" :value="site.uid">{{ site.name }}</option>
            </select>
          </div>
          <div>
            <label class="block text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1.5">Periode</label>
            <select v-model="filters.period" @change="loadAnalytics" class="form-input text-sm">
              <option value="day">Harian</option>
              <option value="week">Mingguan</option>
              <option value="month">Bulanan</option>
            </select>
          </div>
          <div>
            <label class="block text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1.5">Dari</label>
            <input v-model="filters.dateFrom" type="date" @change="loadAnalytics" class="form-input text-sm" />
          </div>
          <div>
            <label class="block text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1.5">Sampai</label>
            <input v-model="filters.dateTo" type="date" @change="loadAnalytics" class="form-input text-sm" />
          </div>
        </div>
      </div>

      <!-- Loading State -->
      <div v-if="loading" class="flex justify-center items-center py-12">
        <div class="text-center">
          <i class="fas fa-spinner fa-spin text-4xl text-primary mb-4"></i>
          <p class="text-slate-400 text-sm">Memuat data analisis...</p>
        </div>
      </div>

      <!-- Statistics Cards -->
      <div v-else-if="filters.siteUid" class="grid grid-cols-2 md:grid-cols-4 gap-3 md:gap-4">
        <!-- pH -->
        <div class="sensor-card" style="border-left-color:#3b82f6; border-left-width:4px;">
          <div class="absolute bottom-2 right-3 pointer-events-none select-none opacity-[0.07]" style="color:#3b82f6;">
            <i class="fas fa-flask text-4xl"></i>
          </div>
          <p class="text-[10px] font-bold text-slate-400 uppercase tracking-[0.12em] mb-2">Rata-rata pH</p>
          <div class="font-mono text-2xl font-bold text-slate-800 leading-none mb-1">{{ formatNumber(stats.ph.avg, 2) }}</div>
          <div class="text-[10px] text-slate-400 font-mono">
            ↓ {{ formatNumber(stats.ph.min, 2) }} &nbsp;·&nbsp; ↑ {{ formatNumber(stats.ph.max, 2) }}
          </div>
        </div>
        <!-- TSS -->
        <div class="sensor-card" style="border-left-color:#0ea5e9; border-left-width:4px;">
          <div class="absolute bottom-2 right-3 pointer-events-none select-none opacity-[0.07]" style="color:#0ea5e9;">
            <i class="fas fa-filter text-4xl"></i>
          </div>
          <p class="text-[10px] font-bold text-slate-400 uppercase tracking-[0.12em] mb-2">Rata-rata TSS</p>
          <div class="font-mono text-2xl font-bold text-slate-800 leading-none mb-1">{{ formatNumber(stats.tss.avg, 1) }} <span class="text-xs font-sans font-medium text-slate-400">mg/L</span></div>
          <div class="text-[10px] text-slate-400 font-mono">
            ↓ {{ formatNumber(stats.tss.min, 1) }} &nbsp;·&nbsp; ↑ {{ formatNumber(stats.tss.max, 1) }}
          </div>
        </div>
        <!-- COD -->
        <div class="sensor-card" style="border-left-color:#6366f1; border-left-width:4px;">
          <div class="absolute bottom-2 right-3 pointer-events-none select-none opacity-[0.07]" style="color:#6366f1;">
            <i class="fas fa-vial text-4xl"></i>
          </div>
          <p class="text-[10px] font-bold text-slate-400 uppercase tracking-[0.12em] mb-2">Rata-rata COD</p>
          <div class="font-mono text-2xl font-bold text-slate-800 leading-none mb-1">{{ formatNumber(stats.cod.avg, 1) }} <span class="text-xs font-sans font-medium text-slate-400">mg/L</span></div>
          <div class="text-[10px] text-slate-400 font-mono">
            ↓ {{ formatNumber(stats.cod.min, 1) }} &nbsp;·&nbsp; ↑ {{ formatNumber(stats.cod.max, 1) }}
          </div>
        </div>
        <!-- NH3-N -->
        <div class="sensor-card" style="border-left-color:#10b981; border-left-width:4px;">
          <div class="absolute bottom-2 right-3 pointer-events-none select-none opacity-[0.07]" style="color:#10b981;">
            <i class="fas fa-atom text-4xl"></i>
          </div>
          <p class="text-[10px] font-bold text-slate-400 uppercase tracking-[0.12em] mb-2">Rata-rata NH3-N</p>
          <div class="font-mono text-2xl font-bold text-slate-800 leading-none mb-1">{{ formatNumber(stats.nh3n.avg, 2) }} <span class="text-xs font-sans font-medium text-slate-400">mg/L</span></div>
          <div class="text-[10px] text-slate-400 font-mono">
            ↓ {{ formatNumber(stats.nh3n.min, 2) }} &nbsp;·&nbsp; ↑ {{ formatNumber(stats.nh3n.max, 2) }}
          </div>
        </div>
      </div>

      <!-- Empty State -->
      <div v-else class="card p-12 text-center">
        <svg class="w-28 h-20 mx-auto mb-5" viewBox="0 0 140 100" fill="none" xmlns="http://www.w3.org/2000/svg">
          <rect x="8" y="8" width="124" height="78" rx="6" fill="#f1f5f9" stroke="#e2e8f0" stroke-width="1.5"/>
          <rect x="14" y="14" width="112" height="60" rx="3" fill="white"/>
          <polyline points="22,65 38,50 55,56 72,38 89,44 106,28 118,33"
            stroke="#cbd5e1" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
          <polyline points="22,65 38,50 55,56 72,38 89,44 106,28 118,33"
            fill="none" stroke="#bfdbfe" stroke-width="1.5" stroke-linecap="round" stroke-dasharray="3,3"/>
          <circle cx="72" cy="38" r="3.5" fill="#bfdbfe" stroke="#93c5fd" stroke-width="1"/>
          <circle cx="106" cy="28" r="3.5" fill="#bfdbfe" stroke="#93c5fd" stroke-width="1"/>
          <rect x="55" y="88" width="30" height="4" rx="2" fill="#e2e8f0"/>
          <rect x="67" y="84" width="6" height="6" rx="1" fill="#e2e8f0"/>
        </svg>
        <h3 class="text-base font-bold text-slate-700 mb-1">Pilih Lokasi Terlebih Dahulu</h3>
        <p class="text-sm text-slate-400">Data analisis akan tampil setelah lokasi dipilih</p>
      </div>

      <!-- Charts Grid -->
      <div v-if="filters.siteUid && !loading" class="grid grid-cols-1 lg:grid-cols-2 gap-4 md:gap-5">
        <div class="card p-4 md:p-5">
          <h3 class="card-title mb-4">Tren Parameter Air</h3>
          <div class="h-64 md:h-72">
            <apexchart v-if="trendOptions" type="area" height="100%" :options="trendOptions" :series="trendSeries" />
          </div>
        </div>
        <div class="card p-4 md:p-5">
          <h3 class="card-title mb-4">Perbandingan Rata-rata</h3>
          <div class="h-64 md:h-72">
            <apexchart v-if="barOptions" type="bar" height="100%" :options="barOptions" :series="barSeries" />
          </div>
        </div>
      </div>

      <!-- Compliance Analysis -->
      <div v-if="filters.siteUid && !loading" class="card p-4 md:p-5">
        <h3 class="card-title mb-5">Kepatuhan Baku Mutu KLHK</h3>
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-5">
          <div v-for="param in complianceParams" :key="param.key">
            <div class="flex items-center justify-between mb-2">
              <span class="text-xs font-bold text-slate-600">{{ param.label }}</span>
              <span :class="['text-xs font-bold font-mono', getComplianceColor(param.compliance)]">{{ param.compliance }}%</span>
            </div>
            <div class="w-full bg-slate-100 rounded-full h-1.5 mb-1.5">
              <div
                :class="['h-1.5 rounded-full transition-all duration-700', getComplianceBgColor(param.compliance)]"
                :style="{ width: `${param.compliance}%` }"
              ></div>
            </div>
            <div class="text-[10px] text-slate-400">{{ param.standard }}</div>
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
import AppLayout from '@/Layouts/AppLayout.vue';
import { useApi } from '@/Composables/useApi';
import { useAuth } from '@/Composables/useAuth';
import { useToast } from '@/Composables/useToast';
import { formatNumber, parseUTC, formatDate } from '@/Utils/helpers';
import logger from '@/Utils/logger';

const apexchart = VueApexCharts;
const toast = useToast();

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
    labels: {
      style: { colors: '#64748b', fontSize: '10px' },
      formatter: (val) => new Date(val).toLocaleTimeString('id-ID', { timeZone: siteTz.value, hour: '2-digit', minute: '2-digit' }),
    },
  },
  yaxis: { labels: { style: { colors: '#64748b' } } },
  legend: { position: 'top', fontSize: '11px' },
  tooltip: {
    x: {
      formatter: (val) => new Date(val).toLocaleString('id-ID', { timeZone: siteTz.value, day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' }),
    },
  },
  grid: { borderColor: '#e2e8f0', strokeDashArray: 4 },
  responsive: [{ breakpoint: 768, options: { legend: { fontSize: '10px' } } }],
}));

const trendSeries = computed(() => [
  { name: 'pH', data: chartData.value.map(d => ({ x: parseUTC(d.ts), y: d.ph })) },
  { name: 'TSS', data: chartData.value.map(d => ({ x: parseUTC(d.ts), y: d.tss })) },
  { name: 'COD', data: chartData.value.map(d => ({ x: parseUTC(d.ts), y: d.cod })) },
  { name: 'NH3-N', data: chartData.value.map(d => ({ x: parseUTC(d.ts), y: d.nh3n })) },
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

const siteTz = computed(() => {
  const site = sites.value.find(s => s.uid === filters.value.siteUid);
  return site?.timezone || 'Asia/Jakarta';
});

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
    logger.error('Failed to load sites:', error);
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
    logger.error('Failed to load analytics:', error);
  } finally {
    loading.value = false;
  }
};

const exportCsv = () => {
  if (!chartData.value.length) return;

  const siteName = sites.value.find(s => s.uid === filters.value.siteUid)?.name || 'data';
  const cols = ['ts', 'ph', 'tss', 'cod', 'nh3n', 'debit', 'temp', 'rh', 'voltage', 'current'];
  const headers = ['Waktu', 'pH', 'TSS (mg/L)', 'COD (mg/L)', 'NH3N (mg/L)', 'Debit (m³/s)', 'Suhu (°C)', 'Kelembaban (%)', 'Tegangan (V)', 'Arus (A)'];

  const rows = chartData.value.map(row =>
    cols.map(k => {
      if (k === 'ts') return `"${parseUTC(row[k]).toLocaleString('id-ID', { timeZone: siteTz.value, day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit', second: '2-digit' })}"`;
      return row[k] ?? '';
    }).join(',')
  );

  const csv = [headers.join(','), ...rows].join('\n');
  const blob = new Blob(['﻿' + csv], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `data-${siteName}-${filters.value.dateFrom}.csv`;
  a.click();
  URL.revokeObjectURL(url);
  toast.success('Data berhasil diekspor ke CSV');
};

const exportReport = async () => {
  if (!chartData.value.length || exporting.value) return;
  
  exporting.value = true;
  try {
    // Import analysis functions
    const { generateFullAnalysis, paramLabels, standards } = await import('@/Utils/analysis.js');
    
    // Get site name
    const siteName = sites.value.find(s => s.uid === filters.value.siteUid)?.name || 'Unknown';
    
    // Generate analysis
    const { analyses, summary } = generateFullAnalysis(chartData.value);
    
    // Create PDF
    const pdf = new jsPDF({
      orientation: 'portrait',
      unit: 'mm',
      format: 'a4',
    });
    
    const pageWidth = pdf.internal.pageSize.getWidth();
    const pageHeight = pdf.internal.pageSize.getHeight();
    let y = 15;
    
    // Helper function for new page
    const checkNewPage = (requiredSpace) => {
      if (y + requiredSpace > pageHeight - 15) {
        pdf.addPage();
        y = 15;
        return true;
      }
      return false;
    };
    
    // ===== HEADER =====
    pdf.setFontSize(20);
    pdf.setTextColor(30, 64, 175);
    pdf.text('LAPORAN ANALISIS KUALITAS AIR LIMBAH', pageWidth / 2, y, { align: 'center' });
    y += 8;
    
    pdf.setFontSize(10);
    pdf.setTextColor(100);
    pdf.text(`Lokasi: ${siteName}`, pageWidth / 2, y, { align: 'center' });
    y += 5;
    pdf.text(`Periode: ${filters.value.dateFrom} s/d ${filters.value.dateTo}`, pageWidth / 2, y, { align: 'center' });
    y += 5;
    pdf.text(`Dicetak: ${new Date().toLocaleString('id-ID')}`, pageWidth / 2, y, { align: 'center' });
    y += 10;
    
    // ===== EXECUTIVE SUMMARY =====
    pdf.setFillColor(241, 245, 249);
    pdf.roundedRect(10, y, pageWidth - 20, 35, 3, 3, 'F');
    y += 8;
    
    pdf.setFontSize(14);
    pdf.setTextColor(30, 64, 175);
    pdf.text('RINGKASAN EKSEKUTIF', 15, y);
    y += 8;
    
    pdf.setFontSize(10);
    pdf.setTextColor(60);
    
    const statusLabel = summary.overallStatus === 'good' ? '✅ BAIK' : 
                        summary.overallStatus === 'warning' ? '⚠️ PERHATIAN' : '❌ KRITIS';
    pdf.text(`Status Keseluruhan: ${statusLabel}`, 15, y);
    y += 5;
    pdf.text(`Tingkat Kepatuhan Rata-rata: ${summary.overallCompliance}%`, 15, y);
    y += 5;
    pdf.text(`Total Data Dianalisis: ${summary.dataPoints} titik data`, 15, y);
    y += 5;
    pdf.text(`Parameter Kritis: ${summary.criticalCount} | Perlu Perhatian: ${summary.warningCount}`, 15, y);
    y += 5;
    pdf.text(`Total Anomali Terdeteksi: ${summary.totalAnomalies}`, 15, y);
    y += 12;
    
    // ===== PARAMETER ANALYSIS =====
    pdf.setFontSize(14);
    pdf.setTextColor(30, 64, 175);
    pdf.text('ANALISIS PARAMETER', 15, y);
    y += 8;
    
    const waterParams = ['ph', 'tss', 'cod', 'nh3n'];
    const otherParams = ['debit', 'voltage', 'current', 'temp'];
    
    for (const field of [...waterParams, ...otherParams]) {
      const analysis = analyses[field];
      if (!analysis || !analysis.stats) continue;
      
      checkNewPage(45);
      
      // Parameter header with status
      pdf.setFillColor(
        analysis.status.status === 'good' ? 220 : analysis.status.status === 'warning' ? 254 : 254,
        analysis.status.status === 'good' ? 252 : analysis.status.status === 'warning' ? 243 : 226,
        analysis.status.status === 'good' ? 231 : analysis.status.status === 'warning' ? 199 : 226
      );
      pdf.roundedRect(10, y, pageWidth - 20, 40, 2, 2, 'F');
      y += 6;
      
      pdf.setFontSize(12);
      pdf.setTextColor(30, 64, 175);
      pdf.text(`${analysis.label}`, 15, y);
      
      // Status badge
      pdf.setFontSize(9);
      const statusColor = analysis.status.status === 'good' ? [16, 185, 129] : 
                          analysis.status.status === 'warning' ? [245, 158, 11] : [239, 68, 68];
      pdf.setTextColor(...statusColor);
      pdf.text(`[${analysis.status.label}]`, 50, y);
      y += 6;
      
      pdf.setFontSize(9);
      pdf.setTextColor(60);
      
      // Statistics
      const std = analysis.standard;
      const stdText = std.min !== undefined && std.max !== undefined ? 
        `${std.min} - ${std.max} ${std.unit}` : 
        std.max !== undefined ? `< ${std.max} ${std.unit}` : '-';
      
      pdf.text(`Baku Mutu: ${stdText}`, 15, y);
      pdf.text(`Rata-rata: ${analysis.stats.avg.toFixed(2)}`, 80, y);
      pdf.text(`Min: ${analysis.stats.min.toFixed(2)} | Max: ${analysis.stats.max.toFixed(2)}`, 130, y);
      y += 5;
      
      // Trend & Compliance
      pdf.text(`Tren: ${analysis.trendInfo.label}`, 15, y);
      pdf.text(`Kepatuhan: ${analysis.compliance.percentage}% (${analysis.compliance.compliantCount}/${analysis.compliance.total})`, 80, y);
      y += 5;
      
      // Anomalies
      if (analysis.anomalies.hasAnomalies) {
        pdf.setTextColor(239, 68, 68);
        pdf.text(`Anomali: ${analysis.anomalies.count} data terdeteksi`, 15, y);
        pdf.setTextColor(60);
      } else {
        pdf.text(`Anomali: Tidak ada`, 15, y);
      }
      y += 5;
      
      // Recommendations
      if (analysis.recommendations.length > 0) {
        const rec = analysis.recommendations[0];
        const recColor = rec.type === 'success' ? [16, 185, 129] : 
                         rec.type === 'warning' ? [245, 158, 11] : 
                         rec.type === 'danger' ? [239, 68, 68] : [59, 130, 246];
        pdf.setTextColor(...recColor);
        pdf.text(`→ ${rec.text}`, 15, y, { maxWidth: pageWidth - 30 });
        pdf.setTextColor(60);
      }
      y += 10;
    }
    
    // ===== RECOMMENDATIONS SUMMARY =====
    checkNewPage(50);
    
    pdf.setFontSize(14);
    pdf.setTextColor(30, 64, 175);
    pdf.text('REKOMENDASI TINDAKAN', 15, y);
    y += 8;
    
    let recCount = 0;
    for (const field of [...waterParams, ...otherParams]) {
      const analysis = analyses[field];
      if (!analysis) continue;
      
      for (const rec of analysis.recommendations) {
        if (recCount >= 10) break;
        checkNewPage(8);
        
        const icon = rec.type === 'danger' ? '❌' : rec.type === 'warning' ? '⚠️' : rec.type === 'success' ? '✅' : 'ℹ️';
        pdf.setFontSize(9);
        pdf.setTextColor(60);
        pdf.text(`${icon} [${analysis.label}] ${rec.text}`, 15, y, { maxWidth: pageWidth - 30 });
        y += 6;
        recCount++;
      }
    }
    
    if (recCount === 0) {
      pdf.setFontSize(9);
      pdf.setTextColor(16, 185, 129);
      pdf.text('✅ Semua parameter dalam kondisi optimal. Tidak ada tindakan khusus diperlukan.', 15, y);
    }
    
    // ===== FOOTER =====
    const totalPages = pdf.internal.getNumberOfPages();
    for (let i = 1; i <= totalPages; i++) {
      pdf.setPage(i);
      pdf.setFontSize(8);
      pdf.setTextColor(150);
      pdf.text(`SPARING - Sistem Pemantauan Lingkungan | Halaman ${i} dari ${totalPages}`, pageWidth / 2, pageHeight - 8, { align: 'center' });
    }
    
    // Save PDF
    const filename = `laporan-analisis-${siteName}-${filters.value.dateFrom}.pdf`;
    pdf.save(filename);
  } catch (error) {
    logger.error('Failed to export PDF:', error);
    toast.error('Gagal mengekspor PDF. Silakan coba lagi.');
  } finally {
    exporting.value = false;
  }
};

onMounted(async () => {
  await loadSites();
  await loadAnalytics();
});
</script>
