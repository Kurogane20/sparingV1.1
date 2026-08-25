<template>
  <AppLayout>
    <PageHeader title="Command Center" subtitle="Pemantauan semua lokasi secara real-time (khusus admin)">
      <template #actions>
        <div class="flex items-center gap-2 text-[11px] text-[#617377]">
          <span class="inline-flex items-center gap-1.5">
            <span class="w-1.5 h-1.5 rounded-full bg-success animate-pulse"></span>
            Diperbarui otomatis tiap 30 dtk
          </span>
          <span v-if="lastUpdated" class="font-mono">· {{ lastUpdated }}</span>
        </div>
      </template>
    </PageHeader>

    <!-- Totals strip -->
    <div class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-3 md:gap-4 mb-4">
      <div class="sensor-card" style="border-left-color:#0E7C86; border-left-width:4px;">
        <p class="text-[10px] font-bold text-[#617377] uppercase tracking-[0.12em] mb-2">Total Lokasi</p>
        <div class="font-mono text-2xl font-bold text-ink leading-none">{{ totals?.site_count ?? '—' }}</div>
      </div>
      <div class="sensor-card" style="border-left-color:#1F7A4D; border-left-width:4px;">
        <p class="text-[10px] font-bold text-[#617377] uppercase tracking-[0.12em] mb-2">Online</p>
        <div class="font-mono text-2xl font-bold text-success leading-none">{{ totals?.online_count ?? '—' }}<span class="text-xs font-sans text-[#617377]"> / {{ totals?.site_count ?? '—' }}</span></div>
      </div>
      <div class="sensor-card" :style="`border-left-color:${(totals?.total_active_alarms) ? '#B03030' : '#D7E0E1'}; border-left-width:4px;`">
        <p class="text-[10px] font-bold text-[#617377] uppercase tracking-[0.12em] mb-2">Alarm Aktif</p>
        <div class="font-mono text-2xl font-bold leading-none" :class="(totals?.total_active_alarms) ? 'text-danger' : 'text-ink'">{{ totals?.total_active_alarms ?? '—' }}</div>
      </div>
      <div class="sensor-card" :style="`border-left-color:${(totals?.sites_with_danger) ? '#B03030' : '#D7E0E1'}; border-left-width:4px;`">
        <p class="text-[10px] font-bold text-[#617377] uppercase tracking-[0.12em] mb-2">Lokasi Bahaya</p>
        <div class="font-mono text-2xl font-bold leading-none" :class="(totals?.sites_with_danger) ? 'text-danger' : 'text-ink'">{{ totals?.sites_with_danger ?? '—' }}</div>
      </div>
      <div class="sensor-card col-span-2 md:col-span-1" style="border-left-color:#9A6B00; border-left-width:4px;">
        <p class="text-[10px] font-bold text-[#617377] uppercase tracking-[0.12em] mb-2">Rata-rata Kepatuhan</p>
        <div class="font-mono text-2xl font-bold text-ink leading-none">{{ totals?.avg_compliance_pct != null ? formatNumber(totals.avg_compliance_pct, 1) + '%' : '—' }}</div>
      </div>
    </div>

    <!-- Aggregate comparison chart -->
    <div v-if="sites.length" class="bg-white border border-[#D7E0E1] rounded-lg p-4 mb-4">
      <h3 class="text-sm font-bold text-ink mb-1">Perbandingan Antar-Lokasi</h3>
      <p class="text-[11px] text-[#617377] mb-3">Kepatuhan 24 jam vs kelengkapan data hari ini per lokasi.</p>
      <apexchart type="bar" height="260" :options="barOptions" :series="barSeries" />
    </div>

    <!-- Loading -->
    <div v-if="loading && !sites.length" class="bg-white border border-[#D7E0E1] rounded-lg p-12 text-center text-sm text-[#617377]">
      <i class="fas fa-spinner fa-spin mr-2"></i>Memuat status lokasi...
    </div>

    <!-- Video-wall grid -->
    <div v-else class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3 md:gap-4">
      <div
        v-for="s in sites"
        :key="s.uid"
        class="bg-white border rounded-lg p-4 relative overflow-hidden"
        :class="s.danger_alarms ? 'border-danger/40' : 'border-[#D7E0E1]'"
        :style="`border-left:4px solid ${statusColor(s.status)}`"
      >
        <!-- Header -->
        <div class="flex items-start justify-between gap-2 mb-3">
          <div class="min-w-0">
            <div class="font-bold text-ink text-sm truncate">{{ s.name }}</div>
            <div class="text-[10px] text-[#8FA0A3] font-mono">{{ s.uid }}</div>
          </div>
          <span class="shrink-0 inline-flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-wide px-2 py-0.5 rounded"
                :style="`background:${statusBg(s.status)}; color:${statusColor(s.status)}`">
            <span class="w-1.5 h-1.5 rounded-full" :style="`background:${statusColor(s.status)}`"></span>
            {{ statusLabel(s.status) }}
          </span>
        </div>

        <!-- Kepatuhan + Alarm -->
        <div class="grid grid-cols-2 gap-2 mb-3">
          <div class="rounded-md bg-[#F7FAFA] border border-[#EEF2F3] px-2.5 py-2">
            <div class="text-[9px] font-bold text-[#617377] uppercase tracking-wide">Kepatuhan 24j</div>
            <div class="font-mono text-lg font-bold leading-tight" :class="complianceColor(s.compliance_pct)">
              {{ s.compliance_pct != null ? formatNumber(s.compliance_pct, 0) + '%' : '—' }}
            </div>
          </div>
          <div class="rounded-md px-2.5 py-2 border"
               :class="s.active_alarms ? 'bg-[#FBEAEA] border-[#F0C6C6]' : 'bg-[#F7FAFA] border-[#EEF2F3]'">
            <div class="text-[9px] font-bold uppercase tracking-wide" :class="s.active_alarms ? 'text-danger' : 'text-[#617377]'">Alarm Aktif</div>
            <div class="font-mono text-lg font-bold leading-tight" :class="s.active_alarms ? 'text-danger' : 'text-ink'">
              {{ s.active_alarms }}<span v-if="s.danger_alarms" class="text-[10px] font-sans"> ({{ s.danger_alarms }} bahaya)</span>
            </div>
          </div>
        </div>

        <!-- Kelengkapan hari ini -->
        <div class="mb-3">
          <div class="flex items-center justify-between text-[10px] mb-1">
            <span class="font-bold text-[#617377] uppercase tracking-wide">Kelengkapan hari ini</span>
            <span class="font-mono font-bold text-ink">{{ formatNumber(s.completeness_pct, 0) }}%</span>
          </div>
          <div class="w-full bg-[#EEF2F3] rounded-full h-1.5">
            <div class="h-1.5 rounded-full transition-all duration-700"
                 :style="`width:${s.completeness_pct}%; background:${completenessColor(s.completeness_pct)}`"></div>
          </div>
        </div>

        <!-- Sparkline tren terbaru (SVG inline) -->
        <div v-if="s._spark" class="mb-2">
          <div class="flex items-center justify-between text-[9px] text-[#8FA0A3] mb-0.5">
            <span class="font-bold uppercase tracking-wide">Tren {{ SPARK_LABEL[s.spark_field] || s.spark_field }}</span>
            <span class="font-mono">{{ s.spark.length }} data terakhir</span>
          </div>
          <svg :viewBox="`0 0 ${SPARK_W} ${SPARK_H}`" preserveAspectRatio="none" class="w-full h-10">
            <polygon :points="s._spark.area" :fill="s._sparkColor" fill-opacity="0.12" />
            <polyline :points="s._spark.line" fill="none" :stroke="s._sparkColor" stroke-width="1.2"
                      stroke-linejoin="round" stroke-linecap="round" vector-effect="non-scaling-stroke" />
          </svg>
        </div>

        <!-- Nilai parameter terakhir -->
        <div class="grid grid-cols-5 gap-1 mb-2">
          <div v-for="f in PARAMS" :key="f.key" class="text-center">
            <div class="text-[8px] font-bold text-[#8FA0A3] uppercase">{{ f.label }}</div>
            <div class="font-mono text-[11px] font-semibold text-ink leading-tight">
              {{ fmtVal(s.last_values?.[f.key], f.dec) }}
            </div>
          </div>
        </div>

        <!-- Footer -->
        <div class="flex items-center justify-between text-[10px] text-[#8FA0A3] pt-2 border-t border-[#EEF2F3]">
          <span>
            <i class="fas fa-hard-drive mr-1"></i>
            <span :class="loggerColor(s.logger_state)">{{ loggerLabel(s.logger_state) }}</span>
          </span>
          <span class="font-mono">{{ s.last_seen ? getRelativeTime(s.last_seen) : 'tak ada data' }}</span>
        </div>
      </div>
    </div>
  </AppLayout>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue';
import VueApexCharts from 'vue3-apexcharts';
import AppLayout from '@/Layouts/AppLayout.vue';
import PageHeader from '@/Components/PageHeader.vue';
import { useApi } from '@/Composables/useApi';
import { formatNumber, getRelativeTime } from '@/Utils/helpers';
import logger from '@/Utils/logger';

const apexchart = VueApexCharts;

const { getOverview } = useApi();

const loading = ref(false);
const sites = ref([]);
const totals = ref(null);
const generatedAt = ref(null);
let timer = null;

const PARAMS = [
  { key: 'ph', label: 'pH', dec: 2 },
  { key: 'tss', label: 'TSS', dec: 1 },
  { key: 'cod', label: 'COD', dec: 1 },
  { key: 'nh3n', label: 'NH3', dec: 2 },
  { key: 'debit', label: 'Debit', dec: 1 },
];

const SPARK_LABEL = { ph: 'pH', tss: 'TSS', cod: 'COD', nh3n: 'NH3-N', debit: 'Debit' };

// Aggregate comparison bar chart (per-site compliance vs completeness)
const barSeries = computed(() => [
  { name: 'Kepatuhan 24j', data: sites.value.map((s) => s.compliance_pct ?? 0) },
  { name: 'Kelengkapan', data: sites.value.map((s) => s.completeness_pct ?? 0) },
]);
const barOptions = computed(() => ({
  chart: { type: 'bar', toolbar: { show: false }, fontFamily: 'Inter, sans-serif', animations: { enabled: false } },
  colors: ['#0E7C86', '#9A6B00'],
  plotOptions: { bar: { horizontal: false, columnWidth: '60%', borderRadius: 3 } },
  dataLabels: { enabled: false },
  stroke: { width: 0 },
  grid: { borderColor: '#EEF2F3', strokeDashArray: 4 },
  xaxis: {
    categories: sites.value.map((s) => s.name),
    labels: { style: { colors: '#12333B', fontSize: '11px' } },
  },
  yaxis: {
    min: 0, max: 100,
    labels: { style: { colors: '#617377', fontSize: '10px' }, formatter: (v) => `${Math.round(v)}%` },
  },
  legend: { position: 'top', horizontalAlign: 'right', fontSize: '11px', labels: { colors: '#617377' } },
  tooltip: { y: { formatter: (v) => `${formatNumber(v, 1)}%` } },
}));

// Per-card sparkline rendered as inline SVG (no chart library) — a video wall of
// many ApexCharts instances is heavy and, on v5, prone to update crashes. A tiny
// polyline is lighter and can't throw.
const sparkColor = (s) => s.danger_alarms ? '#B03030' : s.status === 'offline' ? '#8FA0A3' : '#0E7C86';
const SPARK_W = 100;
const SPARK_H = 28;
function buildSpark(values) {
  if (!values || values.length < 2) return null;
  const min = Math.min(...values);
  const max = Math.max(...values);
  const span = max - min || 1;
  const step = SPARK_W / (values.length - 1);
  const pts = values.map((v, i) => {
    const x = +(i * step).toFixed(2);
    const y = +(SPARK_H - ((v - min) / span) * (SPARK_H - 4) - 2).toFixed(2);
    return `${x},${y}`;
  });
  return { line: pts.join(' '), area: `0,${SPARK_H} ${pts.join(' ')} ${SPARK_W},${SPARK_H}` };
}

const lastUpdated = computed(() => generatedAt.value ? getRelativeTime(generatedAt.value) : '');

const fmtVal = (v, dec) => (v == null ? '—' : formatNumber(v, dec));

const statusColor = (s) => ({ online: '#1F7A4D', warning: '#9A6B00', offline: '#B03030' }[s] || '#8FA0A3');
const statusBg = (s) => ({ online: '#E6F2EC', warning: '#F7EFDD', offline: '#FBEAEA' }[s] || '#EEF2F3');
const statusLabel = (s) => ({ online: 'Online', warning: 'Waspada', offline: 'Offline' }[s] || 'Tak diketahui');

const complianceColor = (c) => c == null ? 'text-[#8FA0A3]' : c >= 90 ? 'text-success' : c >= 70 ? 'text-warning' : 'text-danger';
const completenessColor = (c) => c >= 90 ? '#1F7A4D' : c >= 60 ? '#9A6B00' : '#B03030';

const loggerLabel = (st) => {
  if (!st) return 'logger —';
  return { alive: 'logger alive', down: 'logger down' }[st] || `logger ${st}`;
};
const loggerColor = (st) => st === 'down' ? 'text-danger' : st === 'alive' ? 'text-success' : 'text-[#8FA0A3]';

const load = async () => {
  loading.value = true;
  try {
    const res = await getOverview();
    // Precompute each card's sparkline config once so its options object stays
    // referentially stable between renders.
    sites.value = (res?.sites || []).map((s) => ({
      ...s,
      _spark: buildSpark(s.spark),
      _sparkColor: sparkColor(s),
    }));
    totals.value = res?.totals || null;
    generatedAt.value = res?.generated_at || null;
  } catch (e) {
    logger.error('Failed to load overview:', e);
  } finally {
    loading.value = false;
  }
};

onMounted(() => {
  load();
  timer = setInterval(load, 30000);
});
onUnmounted(() => { if (timer) clearInterval(timer); });
</script>
