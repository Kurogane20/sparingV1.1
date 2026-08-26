<script setup>
import { computed, ref } from 'vue';
import ApexChart from 'vue3-apexcharts';
import ChartState from './ChartState.vue';
import ChartSummary from './ChartSummary.vue';
import {
  buildApexSeries,
  formatDashboardTimestamp,
  getDebitScale,
  getFieldSummary,
} from '@/Utils/dashboardTimeseries.js';

const props = defineProps({
  snapshot: { type: Object, default: null },
  state: { type: String, default: 'idle' },
  stale: { type: Boolean, default: false },
  focusedEventId: { type: [String, Number], default: null },
  reducedMotion: { type: Boolean, default: false },
});

const emit = defineEmits(['retry']);

const chartKey = 'debit:flow:v1';
const chartId = 'dashboard-debit';
const chartGroup = 'dashboard-monitoring-time';
const scaleMode = ref('normal');
const safeSnapshot = computed(() => props.snapshot && typeof props.snapshot === 'object' ? props.snapshot : {});
const summary = computed(() => getFieldSummary(safeSnapshot.value, 'debit'));
const timezone = computed(() => safeSnapshot.value?.meta?.timezone || 'Asia/Jakarta');
const series = computed(() => buildApexSeries(safeSnapshot.value, ['debit']));
const scale = computed(() => getDebitScale(safeSnapshot.value, scaleMode.value));
const chartState = computed(() => props.stale && props.state === 'ready' ? 'stale' : props.state);
const partialReasons = computed(() => Array.isArray(safeSnapshot.value?.meta?.partial_reasons) ? safeSnapshot.value.meta.partial_reasons : []);
const availability = computed(() => safeSnapshot.value?.meta?.availability_pct);
const precision = computed(() => {
  const value = safeSnapshot.value?.series?.debit?.precision;
  return Number.isInteger(value) && value >= 0 && value <= 4 ? value : 2;
});
const unit = computed(() => {
  const value = safeSnapshot.value?.series?.debit?.unit;
  return typeof value === 'string' && value.trim() ? value.trim() : 'L/min';
});

function finite(value) {
  return typeof value === 'number' && Number.isFinite(value) ? value : null;
}

function escapeHtml(value) {
  return String(value ?? '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;');
}

function timestampValue(value) {
  const timestamp = typeof value === 'number' ? value : Date.parse(value);
  return Number.isFinite(timestamp) ? timestamp : null;
}

function formatXAxisLabel(value, timestamp) {
  const source = Number.isFinite(timestamp) ? timestamp : value;
  return formatDashboardTimestamp(source, timezone.value, true);
}

function formatValue(value) {
  const numeric = finite(value);
  return numeric === null ? 'Data Tidak Tersedia' : `${numeric.toFixed(precision.value)} ${unit.value}`;
}

function formatResolution(seconds) {
  const value = finite(seconds);
  if (value === null || value <= 0) return 'tidak tersedia';
  const rounded = Math.round(value);
  if (rounded % 3600 === 0) return `${rounded / 3600} jam`;
  if (rounded % 60 === 0) return `${rounded / 60} menit`;
  return `${rounded} detik`;
}

function localDate(timestamp) {
  const formatted = formatDashboardTimestamp(timestamp, timezone.value);
  return formatted === '—' ? 'Tanggal tidak tersedia' : formatted.slice(0, -8);
}

function isLiveRange(meta) {
  const end = Date.parse(meta?.date_to);
  const generated = Date.parse(meta?.generated_at);
  return Number.isFinite(end) && Number.isFinite(generated) && Math.abs(generated - end) <= 15 * 60 * 1000;
}

const subtitle = computed(() => {
  const meta = safeSnapshot.value?.meta ?? {};
  if (isLiveRange(meta)) {
    const timestamp = summary.value?.current_ts;
    const formatted = formatDashboardTimestamp(timestamp, timezone.value);
    return formatted === '—'
      ? 'Monitoring laju aliran real-time • Waktu pembacaan belum tersedia'
      : `Monitoring laju aliran real-time • ${formatted.slice(0, -8)} • Update terakhir ${formatted.slice(-5)}`;
  }
  return [
    `Periode ${localDate(meta.date_from)} – ${localDate(meta.date_to)}`,
    `Resolusi ${formatResolution(meta.resolution_seconds)}`,
  ].join(' • ');
});

const flowStateText = computed(() => {
  const labels = {
    flowing: 'Aliran normal',
    low_flow: 'Aliran rendah',
    no_flow: 'Aliran terhenti',
    no_data: 'Tidak ada data aliran',
    sensor_error: 'Kesalahan sensor aliran',
  };
  const explicit = labels[summary.value?.flow_state];
  if (explicit) return explicit;

  const status = typeof summary.value?.status === 'string' ? summary.value.status.toLowerCase() : '';
  const reason = typeof summary.value?.status_reason === 'string' ? summary.value.status_reason.toLowerCase() : '';
  if (status === 'sensor_error' || reason.includes('sensor_error')) return labels.sensor_error;
  if (status === 'no_data' || reason.includes('no_data')) return labels.no_data;
  if (status === 'no_flow' || reason.includes('no_flow') || reason.includes('no flow')) return labels.no_flow;
  if (status === 'low_flow' || reason.includes('low_flow') || reason.includes('low flow')) return labels.low_flow;

  const current = finite(summary.value?.current);
  if (current === null) return labels.no_data;
  if (current === 0) return `Pembacaan debit ${formatValue(current)} terdeteksi; status aliran belum dikonfigurasi`;
  return 'Aliran terdeteksi; status aliran belum dikonfigurasi';
});

function pointForTimestamp(timestamp) {
  const points = safeSnapshot.value?.series?.debit?.points;
  if (!Array.isArray(points) || timestamp === null) return {};
  return points.find((point) => timestampValue(point?.ts) === timestamp) ?? {};
}

function eventLabel(event) {
  return typeof event?.label === 'string' && event.label.trim()
    ? event.label
    : (typeof event?.message === 'string' && event.message.trim() ? event.message : 'Event pemantauan');
}

function isFlowEvent(event) {
  if (!event || typeof event !== 'object') return false;
  const type = typeof event.type === 'string' ? event.type.toLowerCase() : '';
  const field = typeof event.field === 'string' ? event.field.toLowerCase() : '';
  if (isGlobalEvent(event)) return false;
  return field === 'debit' && ['threshold_warning', 'threshold_danger', 'threshold', 'rapid_change', 'sensor_anomaly', 'sensor_error', 'sensor_fail', 'sensor_recover', 'flow_drop', 'no_flow', 'flow_restored', 'low_flow_tss_check'].includes(type);
}

function isGlobalEvent(event) {
  if (!event || typeof event !== 'object') return false;
  const type = typeof event.type === 'string' ? event.type.toLowerCase() : '';
  const field = typeof event.field === 'string' && event.field.trim();
  if (['data_gap', 'gap', 'logger_offline', 'logger_online', 'op_status'].includes(type) || type.startsWith('logger_')) return true;
  return !field && ['sensor_fail', 'sensor_recover', 'sensor_error'].includes(type);
}

function eventValue(event) {
  const context = event?.context && typeof event.context === 'object' ? event.context : {};
  if (event?.type === 'low_flow_tss_check') return finite(context.debit?.value);
  return finite(context.current ?? event?.value ?? context.value ?? context.debit?.value);
}

const allEvents = computed(() => Array.isArray(safeSnapshot.value?.events) ? safeSnapshot.value.events : []);
const pointEventAnnotations = computed(() => allEvents.value.flatMap((event) => {
  if (!isFlowEvent(event)) return [];
  const x = timestampValue(event?.ts);
  const y = eventValue(event);
  if (x === null || y === null) return [];
  const type = typeof event?.type === 'string' ? event.type.toLowerCase() : '';
  const focused = String(event.id) === String(props.focusedEventId);
  const shape = {
    flow_drop: 'triangle',
    no_flow: 'square',
    flow_restored: 'diamond',
    low_flow_tss_check: 'star',
    rapid_change: 'plus',
  }[type] ?? (type.includes('sensor') ? 'circle' : type.includes('threshold') ? 'triangle' : 'circle');
  return [{
    id: event.id,
    x,
    y,
    seriesIndex: 0,
    yAxisIndex: 0,
    marker: { shape, size: focused ? 9 : 6, fillColor: focused ? '#0f766e' : '#475569', strokeColor: '#ffffff', strokeWidth: 1 },
    label: { text: eventLabel(event) },
  }];
}));

const globalEventAnnotations = computed(() => allEvents.value.flatMap((event) => {
  if (!isGlobalEvent(event)) return [];
  const x = timestampValue(event?.ts);
  if (x === null) return [];
  const focused = String(event.id) === String(props.focusedEventId);
  return [{
    id: event.id,
    x,
    borderColor: focused ? '#0f766e' : '#94a3b8',
    strokeDashArray: 3,
    label: { text: eventLabel(event), style: { color: focused ? '#0f766e' : '#475569', fontWeight: focused ? 700 : 500 } },
  }];
}));

const currentAnnotation = computed(() => {
  const x = timestampValue(summary.value?.current_ts);
  const y = finite(summary.value?.current);
  if (x === null || y === null) return [];
  return [{ id: 'current-debit', x, y, seriesIndex: 0, yAxisIndex: 0, marker: { size: 7, fillColor: '#0f766e', strokeColor: '#ffffff', strokeWidth: 2 } }];
});

const outlierAnnotations = computed(() => {
  if (scaleMode.value === 'full') return [];
  return (safeSnapshot.value?.series?.debit?.points ?? []).flatMap((point, index) => {
    const value = finite(point?.value);
    const x = timestampValue(point?.ts);
    if (value === null || x === null || value <= scale.value.max) return [];
    return [{
      id: `outlier-${index}`,
      x,
      y: scale.value.max,
      seriesIndex: 0,
      yAxisIndex: 0,
      marker: { shape: 'triangle', size: 6, fillColor: '#b45309', strokeColor: '#ffffff', strokeWidth: 1 },
      label: { text: 'Di luar skala normal' },
    }];
  });
});

const clippedOutlierCount = computed(() => outlierAnnotations.value.length);

function operationalThresholds() {
  const thresholds = safeSnapshot.value?.thresholds?.debit;
  if (!thresholds || typeof thresholds !== 'object') return [];
  const operational = thresholds.operational_flow ?? thresholds.operational_flow_thresholds ?? thresholds.flow_operational_thresholds;
  if (!operational || typeof operational !== 'object') return [];
  const entry = (names) => names.map((name) => operational[name]).find((value) => value !== undefined);
  const value = (candidate) => finite(typeof candidate === 'object' ? candidate?.value ?? candidate?.threshold : candidate);
  return [
    { name: 'no_flow', text: 'Batas tanpa aliran', color: '#b45309' },
    { name: 'low_flow', text: 'Batas aliran rendah', color: '#d97706' },
  ].flatMap(({ name, text, color }) => {
    const y = value(entry([name, `${name}_threshold`]));
    return y === null ? [] : [{ y, yAxisIndex: 0, borderColor: color, strokeDashArray: 4, label: { text } }];
  });
}

function hoveredTimestamp({ seriesIndex = 0, dataPointIndex = 0, w } = {}) {
  return timestampValue(w?.config?.series?.[seriesIndex]?.data?.[dataPointIndex]?.x);
}

function displayStatus(point) {
  return point?.status_label ?? point?.status ?? summary.value?.status_label ?? summary.value?.status ?? 'Tidak Tersedia';
}

function displayQuality(point) {
  return point?.quality_label ?? point?.quality ?? summary.value?.current_quality ?? 'Tidak Tersedia';
}

function bucketDetails(point) {
  const rows = [
    ['Minimum', finite(point?.bucket_min ?? point?.min)],
    ['Maksimum', finite(point?.bucket_max ?? point?.max)],
    ['Jumlah bucket', finite(point?.bucket_count ?? point?.count)],
  ];
  return rows.map(([label, value]) => value === null ? '' : `<div>${label}: ${escapeHtml(label === 'Jumlah bucket' ? value : formatValue(value))}</div>`).join('');
}

function matchingEventDetails(timestamp) {
  if (timestamp === null) return '';
  return allEvents.value.filter((event) => timestampValue(event?.ts) === timestamp).map((event) => {
    const context = event?.context && typeof event.context === 'object' ? event.context : {};
    const numeric = (label, value, suffix = '') => finite(value) === null ? '' : `<div>${label}: ${escapeHtml(value)}${suffix}</div>`;
    const differs = (left, right) => finite(left) !== null && finite(left) !== finite(right);
    const nestedDebitValue = finite(context.debit?.value);
    const eventCurrent = finite(context.current);
    const interval = finite(context.interval_seconds);
    const reason = typeof context.reason === 'string' && context.reason.trim() ? `<div>Alasan: ${escapeHtml(context.reason)}</div>` : '';
    return [
      `<div>Event: ${escapeHtml(eventLabel(event))}</div>`,
      nestedDebitValue === null || nestedDebitValue === eventCurrent ? '' : `<div>Pengukuran Debit: ${escapeHtml(formatValue(nestedDebitValue))}</div>`,
      interval === null ? '' : `<div>Interval: ${escapeHtml(formatResolution(interval))}</div>`,
      numeric('Baseline event', context.baseline),
      numeric('Nilai event saat ini', context.current),
      numeric('Perubahan event', context.delta),
      numeric('Persentase event', context.percent, '%'),
      numeric('Jumlah titik', context.points),
      typeof context.debit?.flow_state === 'string' && context.debit.flow_state.trim() ? `<div>Status debit: ${escapeHtml(context.debit.flow_state)}</div>` : '',
      differs(context.debit?.baseline, context.baseline) ? numeric('Debit baseline', context.debit.baseline) : '',
      differs(context.debit?.current, context.current) ? numeric('Debit saat ini', context.debit.current) : '',
      differs(context.debit?.delta, context.delta) ? numeric('Debit perubahan', context.debit.delta) : '',
      differs(context.debit?.percent, context.percent) ? numeric('Debit persentase', context.debit.percent, '%') : '',
      numeric('TSS baseline', context.tss?.baseline),
      numeric('TSS saat ini', context.tss?.current ?? context.tss?.value),
      numeric('TSS perubahan', context.tss?.delta),
      numeric('TSS persentase', context.tss?.percent, '%'),
      reason,
    ].join('');
  }).join('');
}

function tooltipHtml(context = {}) {
  const timestamp = hoveredTimestamp(context);
  const point = pointForTimestamp(timestamp);
  const resolution = formatResolution(safeSnapshot.value?.meta?.resolution_seconds);
  return `<div class="dashboard-chart-tooltip"><div><strong>${escapeHtml(formatDashboardTimestamp(timestamp, timezone.value))}</strong></div>${resolution === 'tidak tersedia' ? '' : `<div>Resolusi: ${escapeHtml(resolution)}</div>`}<div><strong>Debit:</strong> ${escapeHtml(formatValue(point?.value))}</div><div>Status: ${escapeHtml(displayStatus(point))}</div><div>Kualitas: ${escapeHtml(displayQuality(point))}</div>${bucketDetails(point)}${matchingEventDetails(timestamp)}</div>`;
}

const options = computed(() => ({
  chart: { id: chartId, group: chartGroup, toolbar: { show: false }, animations: { enabled: !props.reducedMotion, speed: props.reducedMotion ? 0 : 180 } },
  colors: ['#0f766e'],
  stroke: { curve: 'straight', width: 2 },
  fill: { type: 'solid', opacity: 0.1 },
  dataLabels: { enabled: false },
  markers: { size: 0 },
  grid: { borderColor: '#e2e8f0', strokeDashArray: 3, padding: { left: 4, right: 8 } },
  legend: { position: 'top', horizontalAlign: 'left', fontSize: '12px', markers: { width: 8, height: 8 } },
  xaxis: { type: 'datetime', tickAmount: 6, labels: { datetimeUTC: true, formatter: formatXAxisLabel, style: { fontSize: '11px' } } },
  yaxis: [{ seriesName: 'Debit', min: 0, max: scale.value.max, title: { text: unit.value }, decimalsInFloat: precision.value }],
  annotations: { yaxis: operationalThresholds(), points: [...pointEventAnnotations.value, ...currentAnnotation.value, ...outlierAnnotations.value], xaxis: globalEventAnnotations.value },
  tooltip: { shared: true, intersect: false, custom: tooltipHtml },
  responsive: [{ breakpoint: 640, options: { legend: { position: 'bottom', horizontalAlign: 'center', fontSize: '11px' }, xaxis: { tickAmount: 3, labels: { datetimeUTC: true, formatter: formatXAxisLabel, style: { fontSize: '10px' } } } } }],
}));

const accessibilitySummary = computed(() => `Ringkasan aksesibilitas Debit. Saat ini ${formatValue(summary.value?.current)}. Status ${summary.value?.status_label ?? summary.value?.status ?? 'Tidak tersedia'}. Status aliran ${flowStateText.value}. Ketersediaan ${finite(summary.value?.availability_pct) ?? 'tidak tersedia'}%.`);

function setScale(mode) { scaleMode.value = mode; }
function retry() { emit('retry'); }
</script>

<template>
  <ChartState :state="chartState" :message="safeSnapshot?.meta?.message || ''" :partial-reasons="partialReasons" :availability="availability" @retry="retry">
    <section class="sensor-card min-w-0 max-w-full rounded-lg border border-slate-200 bg-white p-4 motion-reduce:hover:transform-none motion-reduce:transition-none">
      <div class="mb-4 flex flex-wrap items-start justify-between gap-3">
        <div class="min-w-0">
          <h3 class="text-base font-semibold text-[#12333B]">Debit Air Limbah</h3>
          <p class="mt-1 text-sm text-slate-500">{{ subtitle }}</p>
        </div>
        <div class="inline-flex rounded-md border border-slate-200 p-0.5" role="group" aria-label="Pilihan skala grafik debit">
          <button type="button" class="rounded px-3 py-1.5 text-xs font-semibold text-slate-700 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-teal-700" :class="scaleMode === 'normal' ? 'bg-teal-50 text-teal-800' : ''" :aria-pressed="scaleMode === 'normal' ? 'true' : 'false'" @click="setScale('normal')">Skala normal</button>
          <button type="button" class="rounded px-3 py-1.5 text-xs font-semibold text-slate-700 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-teal-700" :class="scaleMode === 'full' ? 'bg-teal-50 text-teal-800' : ''" :aria-pressed="scaleMode === 'full' ? 'true' : 'false'" @click="setScale('full')">Skala penuh</button>
        </div>
      </div>

      <div class="mb-4 grid gap-3 md:grid-cols-1">
        <ChartSummary field="debit" label="Debit" :summary="summary" :unit="unit" :decimals="precision" />
      </div>
      <p class="mb-3 text-xs font-semibold text-slate-700">Status aliran: {{ flowStateText }}</p>
      <p v-if="scaleMode === 'normal' && clippedOutlierCount" class="mb-3 text-xs text-amber-800">{{ clippedOutlierCount }} nilai di luar skala normal ditandai pada batas grafik.</p>
      <p class="sr-only">{{ accessibilitySummary }}</p>
      <div class="min-w-0 max-w-full" role="img" aria-label="Grafik tren debit air limbah">
        <ApexChart :key="chartKey" type="area" height="320" :options="options" :series="series" />
      </div>
    </section>
  </ChartState>
</template>
