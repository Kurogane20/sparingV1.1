<template>
  <AppLayout>
    <div ref="reportContent" class="space-y-4 md:space-y-6">
      <!-- Page Header -->
      <PageHeader
        :crumb="['Beranda', 'Data', 'Analisis Data']"
        title="Analisis Data"
        subtitle="Analisis mendalam kualitas air limbah"
      >
        <template #actions>
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
        </template>
      </PageHeader>

      <!-- Filter Controls -->
      <div class="bg-white border border-[#D7E0E1] rounded-lg p-4 md:p-5">
        <h3 class="text-sm font-bold text-ink mb-4">Pengaturan Analisis</h3>
        <div class="grid grid-cols-2 md:grid-cols-4 gap-3 md:gap-4">
          <div>
            <label class="block text-xs font-semibold text-[#617377] uppercase tracking-wide mb-1.5">Lokasi</label>
            <select v-model="filters.siteUid" @change="loadAnalytics" class="form-input text-sm">
              <option value="">Pilih Lokasi</option>
              <option v-for="site in sites" :key="site.uid" :value="site.uid">{{ site.name }}</option>
            </select>
          </div>
          <div>
            <label class="block text-xs font-semibold text-[#617377] uppercase tracking-wide mb-1.5">Periode</label>
            <select v-model="filters.period" @change="loadAnalytics" class="form-input text-sm">
              <option value="day">Harian</option>
              <option value="week">Mingguan</option>
              <option value="month">Bulanan</option>
            </select>
          </div>
          <div>
            <label class="block text-xs font-semibold text-[#617377] uppercase tracking-wide mb-1.5">Dari</label>
            <input v-model="filters.dateFrom" type="date" @change="loadAnalytics" class="form-input text-sm" />
          </div>
          <div>
            <label class="block text-xs font-semibold text-[#617377] uppercase tracking-wide mb-1.5">Sampai</label>
            <input v-model="filters.dateTo" type="date" @change="loadAnalytics" class="form-input text-sm" />
          </div>
        </div>
      </div>

      <!-- Loading State -->
      <div v-if="loading" class="flex justify-center items-center py-12">
        <div class="text-center">
          <i class="fas fa-spinner fa-spin text-4xl text-primary mb-4"></i>
          <p class="text-[#617377] text-sm">Memuat data analisis...</p>
        </div>
      </div>

      <!-- Statistics Cards (per parameter) -->
      <div v-else-if="filters.siteUid" class="grid grid-cols-2 md:grid-cols-4 gap-3 md:gap-4">
        <!-- pH -->
        <div class="sensor-card" style="border-left-color:#3b82f6; border-left-width:4px;">
          <div class="absolute bottom-2 right-3 pointer-events-none select-none opacity-[0.07]" style="color:#3b82f6;">
            <i class="fas fa-flask text-4xl"></i>
          </div>
          <p class="text-[10px] font-bold text-[#617377] uppercase tracking-[0.12em] mb-2">Rata-rata pH</p>
          <div class="font-mono text-2xl font-bold text-ink leading-none mb-1">{{ formatNumber(stats.ph.avg, 2) }}</div>
          <div class="text-[10px] text-[#617377] font-mono">
            ↓ {{ formatNumber(stats.ph.min, 2) }} &nbsp;·&nbsp; ↑ {{ formatNumber(stats.ph.max, 2) }}
          </div>
        </div>
        <!-- TSS -->
        <div class="sensor-card" style="border-left-color:#0ea5e9; border-left-width:4px;">
          <div class="absolute bottom-2 right-3 pointer-events-none select-none opacity-[0.07]" style="color:#0ea5e9;">
            <i class="fas fa-filter text-4xl"></i>
          </div>
          <p class="text-[10px] font-bold text-[#617377] uppercase tracking-[0.12em] mb-2">Rata-rata TSS</p>
          <div class="font-mono text-2xl font-bold text-ink leading-none mb-1">{{ formatNumber(stats.tss.avg, 1) }} <span class="text-xs font-sans font-medium text-[#617377]">mg/L</span></div>
          <div class="text-[10px] text-[#617377] font-mono">
            ↓ {{ formatNumber(stats.tss.min, 1) }} &nbsp;·&nbsp; ↑ {{ formatNumber(stats.tss.max, 1) }}
          </div>
        </div>
        <!-- COD -->
        <div class="sensor-card" style="border-left-color:#6366f1; border-left-width:4px;">
          <div class="absolute bottom-2 right-3 pointer-events-none select-none opacity-[0.07]" style="color:#6366f1;">
            <i class="fas fa-vial text-4xl"></i>
          </div>
          <p class="text-[10px] font-bold text-[#617377] uppercase tracking-[0.12em] mb-2">Rata-rata COD</p>
          <div class="font-mono text-2xl font-bold text-ink leading-none mb-1">{{ formatNumber(stats.cod.avg, 1) }} <span class="text-xs font-sans font-medium text-[#617377]">mg/L</span></div>
          <div class="text-[10px] text-[#617377] font-mono">
            ↓ {{ formatNumber(stats.cod.min, 1) }} &nbsp;·&nbsp; ↑ {{ formatNumber(stats.cod.max, 1) }}
          </div>
        </div>
        <!-- NH3-N -->
        <div class="sensor-card" style="border-left-color:#10b981; border-left-width:4px;">
          <div class="absolute bottom-2 right-3 pointer-events-none select-none opacity-[0.07]" style="color:#10b981;">
            <i class="fas fa-atom text-4xl"></i>
          </div>
          <p class="text-[10px] font-bold text-[#617377] uppercase tracking-[0.12em] mb-2">Rata-rata NH3-N</p>
          <div class="font-mono text-2xl font-bold text-ink leading-none mb-1">{{ formatNumber(stats.nh3n.avg, 2) }} <span class="text-xs font-sans font-medium text-[#617377]">mg/L</span></div>
          <div class="text-[10px] text-[#617377] font-mono">
            ↓ {{ formatNumber(stats.nh3n.min, 2) }} &nbsp;·&nbsp; ↑ {{ formatNumber(stats.nh3n.max, 2) }}
          </div>
        </div>
      </div>

      <!-- Empty State -->
      <div v-else class="bg-white border border-[#D7E0E1] rounded-lg p-12 text-center">
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
        <h3 class="text-base font-bold text-ink mb-1">Pilih Lokasi Terlebih Dahulu</h3>
        <p class="text-sm text-[#617377]">Data analisis akan tampil setelah lokasi dipilih</p>
      </div>

      <!-- Ringkasan Operasional: Total Volume (#16) + Data Gap (#6) -->
      <div v-if="filters.siteUid && !loading" class="grid grid-cols-2 md:grid-cols-3 gap-3 md:gap-4">
        <div class="sensor-card" style="border-left-color:#0891b2; border-left-width:4px;">
          <p class="text-[10px] font-bold text-[#617377] uppercase tracking-[0.12em] mb-2">Total Volume Air</p>
          <div class="font-mono text-2xl font-bold text-ink leading-none mb-1">
            {{ volume ? formatNumber(volume.total_m3, 2) : '—' }} <span class="text-xs font-sans font-medium text-[#617377]">m³</span>
          </div>
          <div class="text-[10px] text-[#617377] font-mono">{{ volume ? formatNumber(volume.total_liters, 0) + ' L' : 'dari debit terintegrasi' }}</div>
        </div>
        <div class="sensor-card" style="border-left-color:#9A6B00; border-left-width:4px;">
          <p class="text-[10px] font-bold text-[#617377] uppercase tracking-[0.12em] mb-2">Data Hilang (Gap)</p>
          <div class="font-mono text-2xl font-bold text-ink leading-none mb-1">
            {{ gaps ? gaps.gap_count : '—' }} <span class="text-xs font-sans font-medium text-[#617377]">gap</span>
          </div>
          <div class="text-[10px] text-[#617377] font-mono">{{ gaps ? '≈ ' + gaps.total_missing_estimate + ' data hilang' : 'periode terpilih' }}</div>
        </div>
        <div class="sensor-card col-span-2 md:col-span-1" style="border-left-color:#1F7A4D; border-left-width:4px;">
          <p class="text-[10px] font-bold text-[#617377] uppercase tracking-[0.12em] mb-2">Pengukuran Diterima</p>
          <div class="font-mono text-2xl font-bold text-ink leading-none mb-1">{{ gaps ? gaps.reading_count : '—' }}</div>
          <div class="text-[10px] text-[#617377] font-mono">pada periode terpilih</div>
        </div>
      </div>

      <!-- Ketersediaan (#20) + Transmisi (#21) -->
      <div v-if="filters.siteUid && !loading" class="grid grid-cols-2 md:grid-cols-3 gap-3 md:gap-4">
        <div class="sensor-card" style="border-left-color:#0E7C86; border-left-width:4px;">
          <p class="text-[10px] font-bold text-[#617377] uppercase tracking-[0.12em] mb-2">Ketersediaan Logger</p>
          <div class="font-mono text-2xl font-bold text-ink leading-none mb-1">
            {{ availability && availability.logger_uptime_pct != null ? formatNumber(availability.logger_uptime_pct, 1) + '%' : '—' }}
          </div>
          <div class="text-[10px] text-[#617377] font-mono">
            Internet: {{ availability && availability.internet_uptime_pct != null ? formatNumber(availability.internet_uptime_pct, 1) + '%' : '—' }}
          </div>
        </div>
        <div class="sensor-card" style="border-left-color:#617377; border-left-width:4px;">
          <p class="text-[10px] font-bold text-[#617377] uppercase tracking-[0.12em] mb-2">Transmisi (estimasi)</p>
          <div class="font-mono text-2xl font-bold text-ink leading-none mb-1">
            {{ transmission ? formatNumber(transmission.estimated_success_rate, 1) + '%' : '—' }}
          </div>
          <div class="text-[10px] text-[#617377] font-mono">{{ transmission ? transmission.failure_count + ' gagal · buffer ' + (transmission.buffer_depth ?? '—') : 'estimasi terhadap cadence' }}</div>
        </div>
        <div class="sensor-card col-span-2 md:col-span-1" style="border-left-color:#9A6B00; border-left-width:4px;">
          <p class="text-[10px] font-bold text-[#617377] uppercase tracking-[0.12em] mb-2">Status Kirim Terakhir</p>
          <div class="text-sm font-bold text-ink leading-tight mb-1">
            MM: <span :class="transmission?.last_send_ok_mm ? 'text-success' : 'text-danger'">{{ transmission ? (transmission.last_send_ok_mm ? 'OK' : 'Gagal') : '—' }}</span>
            &nbsp;·&nbsp;
            KLHK: <span :class="transmission?.last_send_ok_klhk ? 'text-success' : 'text-danger'">{{ transmission ? (transmission.last_send_ok_klhk ? 'OK' : 'Gagal') : '—' }}</span>
          </div>
          <div class="text-[10px] text-[#617377] font-mono">Terkirim hari ini: {{ transmission?.daily_sent ?? '—' }}</div>
        </div>
      </div>

      <!-- Main Grid: Trend Chart + Statistik/Catatan -->
      <div v-if="filters.siteUid && !loading" class="grid lg:grid-cols-[2fr_1fr] gap-3">
        <!-- Left: Trend Chart (preserved) -->
        <div class="bg-white border border-[#D7E0E1] rounded-lg p-4">
          <h3 class="text-sm font-bold text-ink mb-4">Tren Parameter Air</h3>
          <div class="h-64 md:h-72">
            <apexchart v-if="trendOptions" type="area" height="100%" :options="trendOptions" :series="trendSeries" />
          </div>
        </div>

        <!-- Right: Statistik + Catatan sistem -->
        <div class="flex flex-col gap-3">
          <div class="bg-white border border-[#D7E0E1] rounded-lg p-4">
            <h3 class="text-sm font-bold text-ink mb-3">Statistik</h3>
            <div class="space-y-2.5">
              <div v-for="row in statRows" :key="row.field" class="border-b border-[#EEF2F3] pb-2 last:border-0 last:pb-0">
                <div class="text-[11px] font-semibold text-[#617377] uppercase tracking-wide mb-1">{{ row.label }}</div>
                <div class="grid grid-cols-2 gap-x-2 gap-y-0.5 text-[12px] font-mono text-ink">
                  <span>Rerata: {{ row.avg }}</span>
                  <span>Simpangan baku: {{ row.stdDev }}</span>
                  <span>Min: {{ row.min }}</span>
                  <span>Maks: {{ row.max }}</span>
                  <span>Median: {{ row.median }}</span>
                  <span>P95: {{ row.p95 }}</span>
                  <span>P99: {{ row.p99 }}</span>
                </div>
              </div>
              <div class="pt-1 flex items-center justify-between text-[12.5px]">
                <span class="text-[#617377]">Kelengkapan data</span>
                <span class="font-mono font-bold text-ink">{{ completenessPct }}</span>
              </div>
            </div>
          </div>

          <div class="bg-white border border-[#D7E0E1] rounded-lg p-4">
            <h3 class="text-sm font-bold text-ink mb-3">Catatan sistem</h3>
            <div v-if="systemNotes.length" class="space-y-2">
              <div
                v-for="(note, i) in systemNotes"
                :key="i"
                class="pl-2.5 text-[12.5px] text-ink leading-snug"
                :style="`border-left:3px solid ${note.color}`"
              >
                {{ note.text }}
              </div>
            </div>
            <p v-else class="text-[12.5px] text-[#617377]">Belum ada catatan untuk periode ini.</p>
          </div>
        </div>
      </div>

      <!-- Secondary Charts: Comparison + Compliance -->
      <div v-if="filters.siteUid && !loading" class="grid grid-cols-1 lg:grid-cols-2 gap-4 md:gap-5">
        <div class="bg-white border border-[#D7E0E1] rounded-lg p-4 md:p-5">
          <h3 class="text-sm font-bold text-ink mb-4">Perbandingan Rata-rata</h3>
          <div class="h-64 md:h-72">
            <apexchart v-if="barOptions" type="bar" height="100%" :options="barOptions" :series="barSeries" />
          </div>
        </div>
        <div class="bg-white border border-[#D7E0E1] rounded-lg p-4 md:p-5">
          <h3 class="text-sm font-bold text-ink mb-5">Kepatuhan Baku Mutu KLHK</h3>
          <div class="grid grid-cols-1 md:grid-cols-2 gap-5">
            <div v-for="param in complianceParams" :key="param.key">
              <div class="flex items-center justify-between mb-2">
                <span class="text-xs font-bold text-[#12333B]">{{ param.label }}</span>
                <span :class="['text-xs font-bold font-mono', getComplianceColor(param.compliance)]">{{ param.compliance == null ? '—' : param.compliance + '%' }}</span>
              </div>
              <div class="w-full bg-[#EEF2F3] rounded-full h-1.5 mb-1.5">
                <div
                  :class="['h-1.5 rounded-full transition-all duration-700', getComplianceBgColor(param.compliance)]"
                  :style="{ width: `${param.compliance ?? 0}%` }"
                ></div>
              </div>
              <div class="text-[10px] text-[#617377]">{{ param.standard }}</div>
            </div>
          </div>
        </div>
      </div>

      <!-- Compliance Heatmap -->
      <div class="bg-white border border-[#D7E0E1] rounded-lg p-4 md:p-5">
        <div class="flex items-center justify-between gap-3 mb-1 flex-wrap">
          <h3 class="text-sm font-bold text-ink">Rekap kepatuhan harian</h3>
          <input
            v-model="complianceMonth"
            @change="loadComplianceDaily"
            type="month"
            class="form-input text-sm w-auto"
          />
        </div>
        <p class="text-[12px] text-[#617377] mb-3">Status kepatuhan harian terhadap baku mutu untuk bulan terpilih.</p>
        <ComplianceHeatmap :days="heatmapDays" />
      </div>
    </div>
  </AppLayout>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import VueApexCharts from 'vue3-apexcharts';
import { jsPDF } from 'jspdf';
import AppLayout from '@/Layouts/AppLayout.vue';
import PageHeader from '@/Components/PageHeader.vue';
import ComplianceHeatmap from '@/Components/ComplianceHeatmap.vue';
import { useApi } from '@/Composables/useApi';
import { useAuth } from '@/Composables/useAuth';
import { useToast } from '@/Composables/useToast';
import { formatNumber, parseUTC, formatDate } from '@/Utils/helpers';
import { calculateStats, analyzeParameter, paramLabels, standards as defaultStandards } from '@/Utils/analysis.js';
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

const { getSites, getSiteMetrics, getData, getCompleteness, getComplianceDaily, getAlertRules, getDataGaps, getTotalVolume, getStatistics, getAvailability, getTransmission } = useApi();
const { filterSitesByUser } = useAuth();

// Baku mutu thresholds come from the backend AlertRule (single source of truth,
// same as the Dashboard and /stats/compliance) — never hardcoded here.
const rulesByField = ref({});
const FIELD_UNITS = { ph: '', tss: 'mg/L', cod: 'mg/L', nh3n: 'mg/L', debit: 'L/min', temp: '°C' };

// AlertRule bounds shaped like analysis.js `standards`, for the shared analysis/
// PDF path. A field WITH a rule is fully described by that rule (danger_min/max);
// a field WITHOUT a rule falls back to the system default baku mutu — mirroring
// the backend's get_baku_mutu().
const stdsFromRules = computed(() => {
  const out = { ...defaultStandards };
  Object.entries(rulesByField.value).forEach(([field, r]) => {
    const s = {};
    if (r.danger_min != null) s.min = r.danger_min;
    if (r.danger_max != null) s.max = r.danger_max;
    out[field] = s;
  });
  return out;
});

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

// Completeness (kelengkapan data)
const completeness = ref(null);
const completenessPct = computed(() => {
  if (!completeness.value || completeness.value.pct == null) return '—';
  return `${formatNumber(completeness.value.pct, 1)}%`;
});

// Operational summary (Priority 2): total volume + data gaps for the range
const volume = ref(null);
const gaps = ref(null);

// Priority 3: full-range statistics + availability + transmission
const statistics = ref(null);
const availability = ref(null);
const transmission = ref(null);

// Compliance heatmap
const heatmapDays = ref([]);
const complianceMonth = ref(getDefaultMonth());

function getDefaultMonth() {
  const now = new Date();
  const y = now.getFullYear();
  const m = String(now.getMonth() + 1).padStart(2, '0');
  return `${y}-${m}`;
}

function getDefaultDateFrom() {
  const date = new Date();
  date.setDate(date.getDate() - 7);
  return date.toISOString().split('T')[0];
}

function getDefaultDateTo() {
  return new Date().toISOString().split('T')[0];
}

// Extended per-parameter stats (rerata/min/max/p95/simpangan baku) from raw chartData
function percentile95(values) {
  if (!values || values.length === 0) return null;
  const sorted = [...values].sort((a, b) => a - b);
  const idx = Math.floor(0.95 * (sorted.length - 1));
  return sorted[idx];
}

const statRows = computed(() => {
  const fields = ['ph', 'tss', 'cod', 'nh3n'];
  return fields.map((field) => {
    // Prefer backend full-range statistics (#18); fall back to client-side over
    // the loaded chart sample only when the endpoint hasn't answered.
    const be = statistics.value?.fields?.[field];
    if (be) {
      return {
        field, label: paramLabels[field] || field,
        avg: formatNumber(be.avg, 2), min: formatNumber(be.min, 2),
        max: formatNumber(be.max, 2), stdDev: formatNumber(be.std_dev, 2),
        median: formatNumber(be.median, 2), p95: formatNumber(be.p95, 2),
        p99: formatNumber(be.p99, 2),
      };
    }
    const s = calculateStats(chartData.value, field);
    const values = chartData.value.map((d) => d[field]).filter((v) => v != null);
    const p95 = percentile95(values);
    return {
      field, label: paramLabels[field] || field,
      avg: s ? formatNumber(s.avg, 2) : '—',
      min: s ? formatNumber(s.min, 2) : '—',
      max: s ? formatNumber(s.max, 2) : '—',
      stdDev: s ? formatNumber(s.stdDev, 2) : '—',
      median: s ? formatNumber(s.median, 2) : '—',
      p95: p95 != null ? formatNumber(p95, 2) : '—',
      p99: '—',
    };
  });
});

// Catatan sistem — reuse generateRecommendations via analyzeParameter
const systemNotes = computed(() => {
  const fields = ['ph', 'tss', 'cod', 'nh3n'];
  const notes = [];
  fields.forEach((field) => {
    const analysis = analyzeParameter(chartData.value, field, stdsFromRules.value);
    analysis.recommendations.forEach((rec) => {
      notes.push({
        text: rec.text,
        color: rec.type === 'warning' || rec.type === 'danger' ? '#9A6B00' : '#0E7C86',
      });
    });
  });
  return notes.slice(0, 8);
});

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

// Compliance params — thresholds and labels derived from the site's AlertRules.
const bakuLabel = (param) => {
  const rule = rulesByField.value[param];
  if (!rule) return 'Baku: —';
  const u = FIELD_UNITS[param] || '';
  const suffix = u ? ` ${u}` : '';
  if (rule.danger_min != null && rule.danger_max != null) return `Baku: ${rule.danger_min} – ${rule.danger_max}${suffix}`;
  if (rule.danger_max != null) return `Baku: ≤ ${rule.danger_max}${suffix}`;
  if (rule.danger_min != null) return `Baku: ≥ ${rule.danger_min}${suffix}`;
  return 'Baku: —';
};

const complianceParams = computed(() =>
  ['ph', 'tss', 'cod', 'nh3n'].map((key) => ({
    key,
    label: paramLabels[key] || key,
    standard: bakuLabel(key),
    compliance: calculateCompliance(key),
  }))
);

const siteTz = computed(() => {
  const site = sites.value.find(s => s.uid === filters.value.siteUid);
  return site?.timezone || 'Asia/Jakarta';
});

// Real compliance %: share of actual readings within the AlertRule danger band.
// Returns null when there is no data or no threshold — the card then shows '—'
// instead of a fabricated number.
const calculateCompliance = (param) => {
  const rule = rulesByField.value[param];
  const values = chartData.value.map((d) => d[param]).filter((v) => v != null);
  if (!values.length) return null;
  if (!rule || (rule.danger_min == null && rule.danger_max == null)) return null;
  const within = values.filter((v) =>
    (rule.danger_min == null || v >= rule.danger_min) &&
    (rule.danger_max == null || v <= rule.danger_max)
  ).length;
  return Math.round((within / values.length) * 1000) / 10;
};

const getComplianceColor = (c) => c == null ? 'text-[#8FA0A3]' : c >= 90 ? 'text-emerald-600' : c >= 70 ? 'text-amber-600' : 'text-red-600';
const getComplianceBgColor = (c) => c == null ? 'bg-[#D7E0E1]' : c >= 90 ? 'bg-emerald-500' : c >= 70 ? 'bg-amber-500' : 'bg-red-500';

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

    // Load this site's baku-mutu thresholds (AlertRules) for the compliance card.
    try {
      const rulesRes = await getAlertRules(filters.value.siteUid);
      const rulesList = rulesRes?.items || (Array.isArray(rulesRes) ? rulesRes : rulesRes?.data || []);
      const map = {};
      rulesList.forEach((r) => { map[r.field] = r; });
      rulesByField.value = map;
    } catch (e) {
      logger.error('Failed to load alert rules:', e);
      rulesByField.value = {};
    }

    // Operational summary: total volume + data gaps over the selected range.
    const rangeParams = {
      date_from: filters.value.dateFrom,
      date_to: endDate.toISOString().split('T')[0],
    };
    try {
      volume.value = await getTotalVolume(filters.value.siteUid, rangeParams);
    } catch (e) {
      logger.error('Failed to load volume:', e);
      volume.value = null;
    }
    try {
      gaps.value = await getDataGaps(filters.value.siteUid, rangeParams);
    } catch (e) {
      logger.error('Failed to load gaps:', e);
      gaps.value = null;
    }
    try {
      statistics.value = await getStatistics(filters.value.siteUid, rangeParams);
    } catch (e) {
      logger.error('Failed to load statistics:', e);
      statistics.value = null;
    }
    try {
      availability.value = await getAvailability(filters.value.siteUid, rangeParams);
    } catch (e) {
      logger.error('Failed to load availability:', e);
      availability.value = null;
    }
    try {
      transmission.value = await getTransmission(filters.value.siteUid, rangeParams);
    } catch (e) {
      logger.error('Failed to load transmission:', e);
      transmission.value = null;
    }
  } catch (error) {
    logger.error('Failed to load analytics:', error);
  } finally {
    loading.value = false;
  }
};

const loadCompleteness = async () => {
  try {
    completeness.value = await getCompleteness(24);
  } catch (error) {
    logger.error('Failed to load completeness:', error);
    completeness.value = null;
  }
};

const loadComplianceDaily = async () => {
  try {
    const response = await getComplianceDaily(complianceMonth.value);
    heatmapDays.value = response?.days || [];
  } catch (error) {
    logger.error('Failed to load compliance daily:', error);
    heatmapDays.value = [];
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
    // Import analysis functions. Thresholds come from the site's AlertRules
    // (stdsFromRules), not the hardcoded defaults — same source as the on-screen
    // compliance card and the backend.
    const { generateFullAnalysis, paramLabels } = await import('@/Utils/analysis.js');
    const stds = stdsFromRules.value;

    // Get site name
    const siteName = sites.value.find(s => s.uid === filters.value.siteUid)?.name || 'Unknown';

    // Generate analysis
    const { analyses, summary } = generateFullAnalysis(chartData.value, stds);

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
  await loadCompleteness();
  await loadComplianceDaily();
});
</script>
