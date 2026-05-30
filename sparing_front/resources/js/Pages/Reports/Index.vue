<template>
  <AppLayout>
    <div class="space-y-6">
      <!-- Page Header -->
      <div class="flex justify-between items-center">
        <div>
          <h2 class="text-xl font-bold text-slate-800">Laporan Regulasi</h2>
          <p class="text-slate-500 text-sm mt-0.5">Generate laporan kepatuhan baku mutu untuk pelaporan KLHK</p>
        </div>
        <div v-if="report" class="flex gap-2">
          <button @click="exportExcel" class="btn-secondary flex items-center gap-2 text-sm" style="color:#059669;border-color:#6ee7b7;">
            <i class="fas fa-file-excel"></i>Excel
          </button>
          <button @click="exportPdf" :disabled="exportingPdf" class="btn-primary flex items-center gap-2 text-sm disabled:opacity-50">
            <i :class="exportingPdf ? 'fas fa-spinner fa-spin' : 'fas fa-file-pdf'"></i>
            {{ exportingPdf ? 'Mengunduh...' : 'PDF' }}
          </button>
        </div>
      </div>

      <!-- Form Card -->
      <div class="card p-5 md:p-6">
        <h3 class="card-title mb-4">Parameter Laporan</h3>
        <div class="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
          <div>
            <label class="block text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1.5">Lokasi</label>
            <select v-model="form.siteUid" class="form-input text-sm">
              <option value="">Pilih Lokasi</option>
              <option v-for="site in sites" :key="site.uid" :value="site.uid">{{ site.name }} — {{ site.company_name }}</option>
            </select>
          </div>
          <div>
            <label class="block text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1.5">Tipe Periode</label>
            <select v-model="form.periodType" class="form-input text-sm">
              <option value="monthly">Bulanan</option>
              <option value="custom">Custom</option>
            </select>
          </div>
          <div v-if="form.periodType === 'monthly'" class="grid grid-cols-2 gap-2">
            <div>
              <label class="block text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1.5">Bulan</label>
              <select v-model="form.month" class="form-input text-sm">
                <option v-for="(m, i) in MONTHS" :key="i" :value="i+1">{{ m }}</option>
              </select>
            </div>
            <div>
              <label class="block text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1.5">Tahun</label>
              <select v-model="form.year" class="form-input text-sm">
                <option v-for="y in years" :key="y" :value="y">{{ y }}</option>
              </select>
            </div>
          </div>
          <div v-else class="grid grid-cols-2 gap-2">
            <div>
              <label class="block text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1.5">Dari</label>
              <input v-model="form.dateFrom" type="date" class="form-input text-sm" />
            </div>
            <div>
              <label class="block text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1.5">Sampai</label>
              <input v-model="form.dateTo" type="date" class="form-input text-sm" />
            </div>
          </div>
        </div>
        <button @click="doGenerateReport" :disabled="loading || !form.siteUid" class="btn-primary text-sm disabled:opacity-50 flex items-center gap-2">
          <i :class="loading ? 'fas fa-spinner fa-spin' : 'fas fa-chart-bar'" class="text-xs"></i>
          {{ loading ? 'Memproses...' : 'Generate Laporan' }}
        </button>
      </div>

      <!-- Report Preview -->
      <div v-if="report" ref="reportRef" class="space-y-5">
        <!-- Report Header -->
        <div class="card p-6 text-center border-t-4 border-primary">
          <div class="text-xs text-slate-400 uppercase tracking-widest mb-1">Laporan Pemantauan Kualitas Air Limbah</div>
          <h2 class="text-lg font-bold text-slate-800">{{ report.site.company_name }}</h2>
          <p class="text-slate-600 font-medium">{{ report.site.name }}</p>
          <div class="flex items-center justify-center gap-4 mt-3 text-xs text-slate-400 font-mono">
            <span>Periode: {{ report.period.label }}</span>
            <span>·</span>
            <span>Dibuat: {{ new Date(report.generated_at).toLocaleDateString('id-ID', { day: '2-digit', month: 'long', year: 'numeric' }) }}</span>
          </div>
        </div>

        <!-- Ringkasan Kepatuhan -->
        <div class="card p-5">
          <h3 class="card-title mb-4">Ringkasan Kepatuhan</h3>
          <div class="grid grid-cols-3 gap-4 mb-4">
            <div class="text-center p-4 rounded-xl" :class="statusBgClass(report.summary.overall_status)">
              <div class="text-3xl font-bold font-mono" :class="statusTextClass(report.summary.overall_status)">
                {{ report.summary.compliance_overall }}%
              </div>
              <div class="text-xs mt-1 font-semibold uppercase tracking-wide" :class="statusTextClass(report.summary.overall_status)">
                {{ statusLabel(report.summary.overall_status) }}
              </div>
            </div>
            <div class="text-center p-4 rounded-xl bg-slate-50">
              <div class="text-3xl font-bold font-mono text-slate-800">{{ report.summary.total_records.toLocaleString('id-ID') }}</div>
              <div class="text-xs text-slate-400 mt-1">Total Data</div>
            </div>
            <div class="text-center p-4 rounded-xl bg-slate-50">
              <div class="text-3xl font-bold font-mono text-slate-800">{{ report.violations.length }}</div>
              <div class="text-xs text-slate-400 mt-1">Pelanggaran</div>
            </div>
          </div>
          <div class="h-2 bg-slate-100 rounded-full overflow-hidden">
            <div class="h-full rounded-full transition-all duration-500" :class="statusBgBarClass(report.summary.overall_status)"
              :style="{ width: report.summary.compliance_overall + '%' }"></div>
          </div>
        </div>

        <!-- Tabel Hasil Pengukuran -->
        <div class="card overflow-hidden">
          <div class="px-5 py-4 border-b border-slate-100">
            <h3 class="card-title">Tabel Hasil Pengukuran</h3>
          </div>
          <div class="overflow-x-auto">
            <table class="w-full text-sm">
              <thead class="bg-slate-50">
                <tr>
                  <th class="text-left px-4 py-3 text-[10px] font-bold text-slate-500 uppercase tracking-wider">Parameter</th>
                  <th class="text-center px-4 py-3 text-[10px] font-bold text-slate-500 uppercase tracking-wider">Baku Mutu</th>
                  <th class="text-right px-4 py-3 text-[10px] font-bold text-slate-500 uppercase tracking-wider">Min</th>
                  <th class="text-right px-4 py-3 text-[10px] font-bold text-slate-500 uppercase tracking-wider">Rata-Rata</th>
                  <th class="text-right px-4 py-3 text-[10px] font-bold text-slate-500 uppercase tracking-wider">Maks</th>
                  <th class="text-right px-4 py-3 text-[10px] font-bold text-slate-500 uppercase tracking-wider">Kepatuhan</th>
                  <th class="text-center px-4 py-3 text-[10px] font-bold text-slate-500 uppercase tracking-wider">Tren</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-slate-50">
                <tr v-for="p in report.parameters" :key="p.field" class="hover:bg-blue-50/30">
                  <td class="px-4 py-3 font-semibold text-slate-800">
                    {{ p.label }}
                    <span class="text-[10px] text-slate-400 font-mono ml-1">{{ p.baku_mutu.unit }}</span>
                  </td>
                  <td class="px-4 py-3 text-center text-xs font-mono text-slate-600">
                    <span v-if="p.baku_mutu.min !== null && p.baku_mutu.max !== null">{{ p.baku_mutu.min }} – {{ p.baku_mutu.max }}</span>
                    <span v-else-if="p.baku_mutu.max !== null">≤ {{ p.baku_mutu.max }}</span>
                    <span v-else-if="p.baku_mutu.min !== null">≥ {{ p.baku_mutu.min }}</span>
                    <span v-else>—</span>
                  </td>
                  <td class="px-4 py-3 text-right font-mono text-slate-700">{{ p.stats.min !== null ? p.stats.min.toFixed(2) : '—' }}</td>
                  <td class="px-4 py-3 text-right font-mono font-semibold text-slate-800">{{ p.stats.avg !== null ? p.stats.avg.toFixed(2) : '—' }}</td>
                  <td class="px-4 py-3 text-right font-mono text-slate-700">{{ p.stats.max !== null ? p.stats.max.toFixed(2) : '—' }}</td>
                  <td class="px-4 py-3 text-right">
                    <span :class="['font-bold font-mono text-sm', p.compliance_pct >= 90 ? 'text-emerald-600' : p.compliance_pct >= 70 ? 'text-amber-500' : 'text-red-500']">
                      {{ p.compliance_pct }}%
                    </span>
                  </td>
                  <td class="px-4 py-3 text-center">
                    <span class="text-xs font-semibold" :class="trendClass(p.trend)">
                      <i :class="trendIcon(p.trend)"></i>
                      {{ trendLabel(p.trend) }}
                    </span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <!-- Grafik Tren -->
        <div class="card p-5">
          <h3 class="card-title mb-4">Grafik Tren Harian</h3>
          <VueApexCharts
            v-if="trendChartOptions && report.daily_summary.length"
            type="line"
            height="280"
            :options="trendChartOptions"
            :series="trendChartSeries"
          />
          <div v-else class="text-center text-sm text-slate-400 py-6">Tidak ada data harian untuk ditampilkan.</div>
        </div>

        <!-- Daftar Pelanggaran -->
        <div v-if="report.violations.length" class="card overflow-hidden">
          <div class="px-5 py-4 border-b border-slate-100 flex items-center justify-between">
            <h3 class="card-title">Daftar Pelanggaran</h3>
            <span class="text-xs font-mono text-slate-400">{{ report.violations.length }} kejadian</span>
          </div>
          <div class="overflow-x-auto max-h-64 overflow-y-auto">
            <table class="w-full text-sm">
              <thead class="bg-slate-50 sticky top-0">
                <tr>
                  <th class="text-left px-4 py-2.5 text-[10px] font-bold text-slate-500 uppercase tracking-wider">Waktu</th>
                  <th class="text-left px-4 py-2.5 text-[10px] font-bold text-slate-500 uppercase tracking-wider">Parameter</th>
                  <th class="text-right px-4 py-2.5 text-[10px] font-bold text-slate-500 uppercase tracking-wider">Nilai</th>
                  <th class="text-right px-4 py-2.5 text-[10px] font-bold text-slate-500 uppercase tracking-wider">Batas</th>
                  <th class="text-center px-4 py-2.5 text-[10px] font-bold text-slate-500 uppercase tracking-wider">Jenis</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-slate-50">
                <tr v-for="v in report.violations" :key="`${v.ts}-${v.field}`" class="hover:bg-red-50/20">
                  <td class="px-4 py-2 font-mono text-xs text-slate-500">{{ new Date(v.ts).toLocaleString('id-ID', { dateStyle: 'short', timeStyle: 'short' }) }}</td>
                  <td class="px-4 py-2 font-semibold text-slate-700">{{ PARAM_LABELS[v.field] || v.field }}</td>
                  <td class="px-4 py-2 text-right font-mono text-red-600 font-bold">{{ v.value.toFixed(2) }}</td>
                  <td class="px-4 py-2 text-right font-mono text-slate-500">{{ v.limit.toFixed(2) }}</td>
                  <td class="px-4 py-2 text-center">
                    <span :class="['text-[10px] font-bold px-2 py-0.5 rounded uppercase', v.limit_type === 'above_max' ? 'bg-red-50 text-red-700' : 'bg-amber-50 text-amber-700']">
                      {{ v.limit_type === 'above_max' ? 'Melewati' : 'Di bawah' }}
                    </span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
        <div v-else class="card p-4 text-center text-sm text-emerald-600 font-semibold">
          <i class="fas fa-check-circle mr-2"></i>Tidak ada pelanggaran baku mutu pada periode ini.
        </div>

        <!-- Rekomendasi -->
        <div class="card p-5">
          <h3 class="card-title mb-4">Rekomendasi</h3>
          <div class="space-y-2">
            <div v-for="(rec, i) in recommendations" :key="i"
              :class="['flex items-start gap-3 p-3 rounded-lg text-sm', recBgClass(rec.type)]">
              <i :class="['shrink-0 mt-0.5', recIcon(rec.type)]"></i>
              <span>{{ rec.text }}</span>
            </div>
            <div v-if="!recommendations.length" class="text-sm text-slate-400 text-center py-2">
              Semua parameter dalam kondisi baik.
            </div>
          </div>
        </div>
      </div>
    </div>
  </AppLayout>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { jsPDF } from 'jspdf';
import * as XLSX from 'xlsx';
import VueApexCharts from 'vue3-apexcharts';
import AppLayout from '@/Layouts/AppLayout.vue';
import { useApi } from '@/Composables/useApi';
import { useAuth } from '@/Composables/useAuth';
import { useToast } from '@/Composables/useToast';
import { generateRecommendations } from '@/Utils/analysis';

const { getSites, generateReport: apiGenerateReport } = useApi();
const { filterSitesByUser } = useAuth();
const toast = useToast();

const MONTHS = ['Januari','Februari','Maret','April','Mei','Juni','Juli','Agustus','September','Oktober','November','Desember'];
const PARAM_LABELS = { ph: 'pH', tss: 'TSS', cod: 'COD', nh3n: 'NH3-N', debit: 'Debit', temp: 'Temperatur' };

const sites = ref([]);
const report = ref(null);
const loading = ref(false);
const exportingPdf = ref(false);
const reportRef = ref(null);

const now = new Date();
const form = ref({
  siteUid: '',
  periodType: 'monthly',
  month: now.getMonth() + 1,
  year: now.getFullYear(),
  dateFrom: '',
  dateTo: '',
});

const years = computed(() => {
  const y = now.getFullYear();
  return [y, y - 1, y - 2, y - 3];
});

const getPeriodDates = () => {
  if (form.value.periodType === 'monthly') {
    const lastDay = new Date(form.value.year, form.value.month, 0).getDate();
    const m = String(form.value.month).padStart(2, '0');
    return { from: `${form.value.year}-${m}-01`, to: `${form.value.year}-${m}-${lastDay}` };
  }
  return { from: form.value.dateFrom, to: form.value.dateTo };
};

const doGenerateReport = async () => {
  if (!form.value.siteUid) return;
  const { from, to } = getPeriodDates();
  if (!from || !to) { toast.error('Pilih periode terlebih dahulu'); return; }
  loading.value = true;
  try {
    report.value = await apiGenerateReport({ site_uid: form.value.siteUid, period_from: from, period_to: to });
    toast.success('Laporan berhasil dibuat');
  } catch {
    toast.error('Gagal membuat laporan');
    report.value = null;
  } finally {
    loading.value = false;
  }
};

// Recommendations using existing analysis utility
const recommendations = computed(() => {
  if (!report.value) return [];
  const recs = [];
  for (const p of report.value.parameters) {
    if (p.stats.count === 0) continue;
    const stats = { avg: p.stats.avg, min: p.stats.min, max: p.stats.max, stdDev: p.stats.std_dev, count: p.stats.count };
    const compliance = { percentage: p.compliance_pct, compliantCount: Math.round(p.stats.count * p.compliance_pct / 100), total: p.stats.count };
    const trend = { direction: p.trend, percentage: 0 };
    const anomalies = { hasAnomalies: false, anomalies: [], count: 0 };
    const paramRecs = generateRecommendations(p.field, stats, compliance, trend, anomalies);
    recs.push(...paramRecs);
  }
  return recs.slice(0, 8);
});

// Status helpers
const statusLabel = (s) => s === 'good' ? 'BAIK' : s === 'warning' ? 'PERHATIAN' : 'KRITIS';
const statusBgClass = (s) => s === 'good' ? 'bg-emerald-50' : s === 'warning' ? 'bg-amber-50' : 'bg-red-50';
const statusTextClass = (s) => s === 'good' ? 'text-emerald-600' : s === 'warning' ? 'text-amber-600' : 'text-red-600';
const statusBgBarClass = (s) => s === 'good' ? 'bg-emerald-500' : s === 'warning' ? 'bg-amber-400' : 'bg-red-500';

const trendLabel = (t) => t === 'increasing' ? 'Naik' : t === 'decreasing' ? 'Turun' : 'Stabil';
const trendIcon = (t) => t === 'increasing' ? 'fas fa-arrow-up' : t === 'decreasing' ? 'fas fa-arrow-down' : 'fas fa-minus';
const trendClass = (t) => t === 'increasing' ? 'text-red-500' : t === 'decreasing' ? 'text-blue-500' : 'text-slate-400';

const recBgClass = (type) => ({ danger: 'bg-red-50 text-red-700', warning: 'bg-amber-50 text-amber-700', info: 'bg-blue-50 text-blue-700', success: 'bg-emerald-50 text-emerald-700' }[type] || 'bg-slate-50 text-slate-600');
const recIcon = (type) => ({ danger: 'fas fa-exclamation-circle text-red-500', warning: 'fas fa-exclamation-triangle text-amber-500', info: 'fas fa-info-circle text-blue-500', success: 'fas fa-check-circle text-emerald-500' }[type] || 'fas fa-circle text-slate-400');

// Trend chart
const TREND_COLORS = { ph: '#3b82f6', tss: '#0ea5e9', cod: '#6366f1', nh3n: '#10b981', debit: '#14b8a6', temp: '#f97316' };

const trendChartSeries = computed(() => {
  if (!report.value?.daily_summary?.length) return [];
  return Object.entries(PARAM_LABELS).map(([field, label]) => ({
    name: label,
    data: report.value.daily_summary.map(d => d[`${field}_avg`] ?? null),
  })).filter(s => s.data.some(v => v !== null));
});

const trendChartOptions = computed(() => {
  if (!report.value?.daily_summary?.length) return null;
  return {
    chart: { type: 'line', toolbar: { show: false }, zoom: { enabled: false }, background: 'transparent' },
    colors: Object.values(TREND_COLORS),
    stroke: { curve: 'smooth', width: 2 },
    xaxis: {
      categories: report.value.daily_summary.map(d => d.date),
      labels: { style: { fontSize: '10px' }, rotate: -30 },
    },
    yaxis: { labels: { style: { fontSize: '10px' } } },
    legend: { position: 'top', fontSize: '11px' },
    tooltip: { shared: true, intersect: false },
    grid: { borderColor: '#f1f5f9' },
  };
});

// Export Excel
const exportExcel = () => {
  if (!report.value) return;
  const rows = report.value.daily_summary.map(d => ({
    'Tanggal': d.date,
    'pH': d.ph_avg,
    'TSS (mg/L)': d.tss_avg,
    'COD (mg/L)': d.cod_avg,
    'NH3-N (mg/L)': d.nh3n_avg,
    'Debit (L/min)': d.debit_avg,
    'Temperatur (°C)': d.temp_avg,
  }));
  const ws = XLSX.utils.json_to_sheet(rows);
  const wb = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(wb, ws, 'Data Harian');
  const filename = `laporan-${report.value.site.uid}-${report.value.period.from}.xlsx`;
  XLSX.writeFile(wb, filename);
  toast.success('File Excel berhasil diunduh');
};

// Export PDF using jsPDF
const exportPdf = async () => {
  if (!report.value || exportingPdf.value) return;
  exportingPdf.value = true;
  try {
    const pdf = new jsPDF({ orientation: 'portrait', unit: 'mm', format: 'a4' });
    const pageW = pdf.internal.pageSize.getWidth();
    let y = 20;

    pdf.setFontSize(14);
    pdf.setFont(undefined, 'bold');
    pdf.text('LAPORAN PEMANTAUAN KUALITAS AIR LIMBAH', pageW / 2, y, { align: 'center' });
    y += 7;
    pdf.setFontSize(11);
    pdf.text(report.value.site.company_name, pageW / 2, y, { align: 'center' });
    y += 5;
    pdf.setFont(undefined, 'normal');
    pdf.setFontSize(9);
    pdf.text(`Lokasi: ${report.value.site.name}  |  Periode: ${report.value.period.label}`, pageW / 2, y, { align: 'center' });
    y += 5;
    pdf.text(`Dibuat: ${new Date(report.value.generated_at).toLocaleDateString('id-ID', { dateStyle: 'long' })}`, pageW / 2, y, { align: 'center' });
    y += 10;

    pdf.setFont(undefined, 'bold');
    pdf.setFontSize(11);
    pdf.text('Ringkasan Kepatuhan', 15, y);
    y += 6;
    pdf.setFont(undefined, 'normal');
    pdf.setFontSize(9);
    pdf.text(`Kepatuhan Keseluruhan: ${report.value.summary.compliance_overall}% (${statusLabel(report.value.summary.overall_status)})`, 15, y);
    y += 5;
    pdf.text(`Total Data: ${report.value.summary.total_records.toLocaleString('id-ID')} records  |  Pelanggaran: ${report.value.violations.length}`, 15, y);
    y += 10;

    pdf.setFont(undefined, 'bold');
    pdf.setFontSize(11);
    pdf.text('Tabel Hasil Pengukuran', 15, y);
    y += 6;
    pdf.setFontSize(8);
    const headers = ['Parameter', 'Baku Mutu', 'Min', 'Rata-Rata', 'Maks', 'Kepatuhan', 'Tren'];
    const colWidths = [28, 28, 20, 22, 20, 22, 18];
    let x = 15;
    pdf.setFont(undefined, 'bold');
    headers.forEach((h, i) => { pdf.text(h, x, y); x += colWidths[i]; });
    y += 5;
    pdf.setFont(undefined, 'normal');
    for (const p of report.value.parameters) {
      if (y > 260) { pdf.addPage(); y = 20; }
      x = 15;
      const bm = p.baku_mutu.max !== null ? `<= ${p.baku_mutu.max}` : p.baku_mutu.min !== null ? `>= ${p.baku_mutu.min}` : '-';
      const row = [
        `${p.label} (${p.baku_mutu.unit})`,
        bm,
        p.stats.min !== null ? p.stats.min.toFixed(2) : '-',
        p.stats.avg !== null ? p.stats.avg.toFixed(2) : '-',
        p.stats.max !== null ? p.stats.max.toFixed(2) : '-',
        `${p.compliance_pct}%`,
        trendLabel(p.trend),
      ];
      row.forEach((v, i) => { pdf.text(String(v), x, y); x += colWidths[i]; });
      y += 5;
    }

    const filename = `laporan-${report.value.site.uid}-${report.value.period.from}.pdf`;
    pdf.save(filename);
    toast.success('PDF berhasil diunduh');
  } catch {
    toast.error('Gagal membuat PDF');
  } finally {
    exportingPdf.value = false;
  }
};

onMounted(async () => {
  try {
    const res = await getSites({ per_page: 100 });
    const list = Array.isArray(res) ? res : (res?.items || res?.data || []);
    sites.value = filterSitesByUser(list);
    if (sites.value.length > 0) form.value.siteUid = sites.value[0].uid;
  } catch {
    sites.value = [];
  }
});
</script>
