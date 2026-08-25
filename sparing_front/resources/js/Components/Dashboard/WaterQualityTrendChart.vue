<script setup>
import { computed } from 'vue';
import ApexChart from 'vue3-apexcharts';
import ChartState from './ChartState.vue';
import ChartSummary from './ChartSummary.vue';
import {
  buildApexSeries,
  buildEventAnnotations,
  buildThresholdAnnotations,
  formatDashboardTimestamp,
  getFieldSummary,
  getTssScale,
} from '@/Utils/dashboardTimeseries.js';

const props = defineProps({
  snapshot: { type: Object, default: null },
  state: { type: String, default: 'idle' },
  stale: { type: Boolean, default: false },
  focusedEventId: { type: [String, Number], default: null },
  reducedMotion: { type: Boolean, default: false },
});

const emit = defineEmits(['retry']);

const chartKey = 'water-quality:ph|tss:v1';
const chartId = 'dashboard-water-quality';
const chartGroup = 'dashboard-monitoring-time';
const safeSnapshot = computed(() => props.snapshot && typeof props.snapshot === 'object' ? props.snapshot : {});
const timezone = computed(() => safeSnapshot.value?.meta?.timezone || 'Asia/Jakarta');
const phSummary = computed(() => getFieldSummary(safeSnapshot.value, 'ph'));
const tssSummary = computed(() => getFieldSummary(safeSnapshot.value, 'tss'));
const tssScale = computed(() => getTssScale(safeSnapshot.value));
const chartState = computed(() => props.stale && props.state === 'ready' ? 'stale' : props.state);
const partialReasons = computed(() => Array.isArray(safeSnapshot.value?.meta?.partial_reasons) ? safeSnapshot.value.meta.partial_reasons : []);
const availability = computed(() => safeSnapshot.value?.meta?.availability_pct);
const tssPrecision = computed(() => {
  const precision = safeSnapshot.value?.series?.tss?.precision;
  return Number.isInteger(precision) && precision >= 0 && precision <= 4 ? precision : 2;
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

function pointForTimestamp(field, timestamp) {
  const points = safeSnapshot.value?.series?.[field]?.points;
  if (!Array.isArray(points) || timestamp === null) return {};
  return points.find((point) => timestampValue(point?.ts) === timestamp) ?? {};
}

function formatValue(value, decimals, unit = '') {
  const numeric = finite(value);
  return numeric === null ? 'Data Tidak Tersedia' : `${numeric.toFixed(decimals)}${unit ? ` ${unit}` : ''}`;
}

function isLiveRange(meta) {
  const end = Date.parse(meta?.date_to);
  const generated = Date.parse(meta?.generated_at);
  return Number.isFinite(end) && Number.isFinite(generated) && Math.abs(generated - end) <= 15 * 60 * 1000;
}

function localDate(timestamp) {
  const formatted = formatDashboardTimestamp(timestamp, timezone.value);
  return formatted === '—' ? 'Tanggal tidak tersedia' : formatted.slice(0, -8);
}

function formatResolution(seconds) {
  const value = finite(seconds);
  if (value === null || value <= 0) return 'tidak tersedia';
  const wholeSeconds = Math.round(value);
  if (wholeSeconds % 3600 === 0) return `${wholeSeconds / 3600} jam`;
  if (wholeSeconds % 60 === 0) return `${wholeSeconds / 60} menit`;
  return `${wholeSeconds} detik`;
}

const latestMeasurementTs = computed(() => {
  const values = [phSummary.value?.current_ts, tssSummary.value?.current_ts]
    .filter((timestamp) => Number.isFinite(Date.parse(timestamp)));
  return values.sort((left, right) => Date.parse(right) - Date.parse(left))[0] ?? null;
});

const subtitle = computed(() => {
  const meta = safeSnapshot.value?.meta ?? {};
  if (isLiveRange(meta)) {
    if (!latestMeasurementTs.value) return 'Real-time • Waktu pembacaan belum tersedia';
    const formatted = formatDashboardTimestamp(latestMeasurementTs.value, timezone.value);
    const date = formatted.slice(0, -8);
    const time = formatted.slice(-5);
    return [date, 'Real-time', `Update terakhir ${time}`].join(' \u2022 ');
  }
  const start = localDate(meta.date_from);
  const end = localDate(meta.date_to);
  return [`Periode ${start} – ${end}`, `Resolusi ${formatResolution(meta.resolution_seconds)}`].join(' \u2022 ');
});

function isWaterEvent(event) {
  if (!event || typeof event !== 'object') return false;
  const field = typeof event.field === 'string' ? event.field.toLowerCase() : '';
  const type = typeof event.type === 'string' ? event.type.toLowerCase() : '';
  if (field === 'debit' || ['flow_drop', 'no_flow', 'flow_restored', 'low_flow_tss_check'].includes(type)) return false;
  return field === 'ph' || field === 'tss' || !field || ['data_gap', 'gap', 'logger_offline', 'logger_online', 'op_status', 'sensor_fail', 'sensor_recover'].includes(type);
}

function fieldIndex(field) {
  return field === 'tss' ? 1 : 0;
}

function eventLabel(event) {
  return typeof event?.label === 'string' && event.label.trim()
    ? event.label : (typeof event?.message === 'string' && event.message.trim() ? event.message : 'Event pemantauan');
}

const waterEvents = computed(() => (Array.isArray(safeSnapshot.value?.events) ? safeSnapshot.value.events : []).filter(isWaterEvent));

const eventAnnotations = computed(() => waterEvents.value.flatMap((event) => {
  const field = typeof event.field === 'string' ? event.field.toLowerCase() : '';
  if (field !== 'ph' && field !== 'tss') return [];
  const index = fieldIndex(field);
  return buildEventAnnotations({ events: [event] }).map((annotation) => ({
    ...annotation,
    id: event.id,
    seriesIndex: index,
    yAxisIndex: index,
    marker: {
      ...annotation.marker,
      size: String(event.id) === String(props.focusedEventId) ? 9 : 6,
      fillColor: String(event.id) === String(props.focusedEventId) ? '#0f766e' : '#475569',
    },
  }));
}));

const globalEventAnnotations = computed(() => waterEvents.value.flatMap((event) => {
  const field = typeof event.field === 'string' ? event.field.toLowerCase() : '';
  const x = Date.parse(event.ts);
  if ((field === 'ph' || field === 'tss') || !Number.isFinite(x)) return [];
  const focused = String(event.id) === String(props.focusedEventId);
  return [{
    id: event.id,
    x,
    borderColor: focused ? '#0f766e' : '#94a3b8',
    strokeDashArray: 3,
    label: { text: eventLabel(event), style: { color: focused ? '#0f766e' : '#475569', fontWeight: focused ? 700 : 500 } },
  }];
}));

const currentAnnotations = computed(() => [
  { field: 'ph', summary: phSummary.value, color: '#0f766e' },
  { field: 'tss', summary: tssSummary.value, color: '#7c3aed' },
].flatMap(({ field, summary, color }) => {
  const x = Date.parse(summary?.current_ts);
  const y = finite(summary?.current);
  if (!Number.isFinite(x) || y === null) return [];
  return [{
    id: `current-${field}`,
    x,
    y,
    seriesIndex: fieldIndex(field),
    yAxisIndex: fieldIndex(field),
    marker: { size: 7, fillColor: color, strokeColor: '#ffffff', strokeWidth: 2 },
  }];
}));

const series = computed(() => buildApexSeries(safeSnapshot.value, ['ph', 'tss']));

function hoveredTimestamp({ seriesIndex = 0, dataPointIndex = 0, w } = {}) {
  const point = w?.config?.series?.[seriesIndex]?.data?.[dataPointIndex];
  return timestampValue(point?.x);
}

function responseUnit(field) {
  const unit = safeSnapshot.value?.series?.[field]?.unit;
  if (typeof unit === 'string' && unit.trim()) return unit.trim();
  return field === 'tss' ? 'mg/L' : '';
}

function displayStatus(point, summary) {
  return point?.status_label ?? point?.status ?? summary?.status_label ?? summary?.status ?? 'Tidak Tersedia';
}

function displayQuality(point) {
  return point?.quality_label ?? point?.quality ?? 'Tidak Tersedia';
}

function pointBucketDetails(point, decimals, unit) {
  const minimum = finite(point?.bucket_min ?? point?.min);
  const maximum = finite(point?.bucket_max ?? point?.max);
  const count = finite(point?.bucket_count ?? point?.count);
  return [
    minimum === null ? '' : `<div>Minimum: ${escapeHtml(formatValue(minimum, decimals, unit))}</div>`,
    maximum === null ? '' : `<div>Maksimum: ${escapeHtml(formatValue(maximum, decimals, unit))}</div>`,
    count === null ? '' : `<div>Jumlah bucket: ${escapeHtml(count)}</div>`,
  ].join('');
}

function eventContextDetails(event) {
  const context = event?.context && typeof event.context === 'object' ? event.context : {};
  const numeric = (label, value) => finite(value) === null ? '' : `<div>${label}: ${escapeHtml(value)}</div>`;
  const interval = finite(context.interval_seconds);
  const reason = typeof context.reason === 'string' && context.reason.trim() ? `<div>Alasan: ${escapeHtml(context.reason)}</div>` : '';
  return [
    `<div>Event: ${escapeHtml(eventLabel(event))}</div>`,
    numeric('Nilai saat ini', context.current),
    numeric('Baseline', context.baseline),
    numeric('Perubahan', context.delta),
    finite(context.percent) === null ? '' : `<div>Persentase: ${escapeHtml(context.percent)}%</div>`,
    interval === null ? '' : `<div>Interval: ${escapeHtml(formatResolution(interval))}</div>`,
    numeric('TSS event', context.tss?.current ?? context.tss?.value),
    numeric('Debit event', context.debit?.value),
    reason,
  ].join('');
}

function matchingEventDetails(timestamp) {
  if (timestamp === null) return '';
  return waterEvents.value
    .filter((event) => timestampValue(event?.ts) === timestamp)
    .map(eventContextDetails)
    .join('');
}

function tooltipHtml(context = {}) {
  const timestamp = hoveredTimestamp(context);
  const phPoint = pointForTimestamp('ph', timestamp);
  const tssPoint = pointForTimestamp('tss', timestamp);
  const dateTime = formatDashboardTimestamp(timestamp, timezone.value);
  const line = (label, point, summary, decimals, unit) => [
    `<div><strong>${label}:</strong> ${escapeHtml(formatValue(point.value, decimals, unit))}</div>`,
    `<div>Status: ${escapeHtml(displayStatus(point, summary))}</div>`,
    `<div>Kualitas: ${escapeHtml(displayQuality(point))}</div>`,
    pointBucketDetails(point, decimals, unit),
  ].join('');
  const resolution = formatResolution(safeSnapshot.value?.meta?.resolution_seconds);
  const resolutionDetail = resolution === 'tidak tersedia' ? '' : `<div>Resolusi: ${escapeHtml(resolution)}</div>`;
  return `<div class="dashboard-chart-tooltip"><div><strong>${escapeHtml(dateTime)}</strong></div>${resolutionDetail}${line('pH', phPoint, phSummary.value, 2)}${line('TSS', tssPoint, tssSummary.value, tssPrecision.value, responseUnit('tss'))}${matchingEventDetails(timestamp)}</div>`;
}

const options = computed(() => ({
  chart: {
    id: chartId,
    group: chartGroup,
    toolbar: { show: false },
    animations: { enabled: !props.reducedMotion, speed: props.reducedMotion ? 0 : 180 },
  },
  colors: ['#0f766e', '#7c3aed'],
  stroke: { curve: 'straight', width: 2 },
  fill: { type: 'solid', opacity: [0.12, 0.08] },
  dataLabels: { enabled: false },
  markers: { size: 0 },
  grid: { borderColor: '#e2e8f0', strokeDashArray: 3, padding: { left: 4, right: 8 } },
  legend: { position: 'top', horizontalAlign: 'left', fontSize: '12px', markers: { width: 8, height: 8 } },
  xaxis: {
    type: 'datetime', tickAmount: 6,
    labels: { datetimeUTC: false, format: 'HH:mm', style: { fontSize: '11px' } },
  },
  yaxis: [
    { seriesName: 'pH', min: 0, max: 14, title: { text: 'pH' }, decimalsInFloat: 2 },
    { seriesName: 'TSS', min: tssScale.value.min, max: tssScale.value.max, opposite: true, title: { text: 'TSS (mg/L)' } },
  ],
  annotations: {
    yaxis: [
      ...buildThresholdAnnotations(safeSnapshot.value, 'ph').map((annotation) => ({ ...annotation, yAxisIndex: 0 })),
      ...buildThresholdAnnotations(safeSnapshot.value, 'tss').map((annotation) => ({ ...annotation, yAxisIndex: 1 })),
    ],
    points: [...eventAnnotations.value, ...currentAnnotations.value],
    xaxis: globalEventAnnotations.value,
  },
  tooltip: { shared: true, intersect: false, custom: tooltipHtml },
  responsive: [{
    breakpoint: 640,
    options: {
      legend: { position: 'bottom', horizontalAlign: 'center', fontSize: '11px' },
      xaxis: { tickAmount: 3, labels: { style: { fontSize: '10px' } } },
    },
  }],
}));

const accessibilitySummary = computed(() => {
  const describe = (label, summary, decimals, unit) => `${label}: saat ini ${formatValue(summary?.current, decimals, unit)}, status ${summary?.status_label ?? summary?.status ?? 'tidak tersedia'}, ketersediaan ${finite(summary?.availability_pct) ?? 'tidak tersedia'}%.`;
  return `Ringkasan aksesibilitas. ${describe('pH', phSummary.value, 2)} ${describe('TSS', tssSummary.value, tssPrecision.value, 'mg/L')}`;
});

function retry() {
  emit('retry');
}
</script>

<template>
  <ChartState
    :state="chartState"
    :message="safeSnapshot?.meta?.message || ''"
    :partial-reasons="partialReasons"
    :availability="availability"
    @retry="retry"
  >
    <section class="sensor-card rounded-lg border border-slate-200 bg-white p-4">
      <div class="mb-4 flex flex-wrap items-start justify-between gap-2">
        <div>
          <h3 class="text-base font-semibold text-[#12333B]">Tren Kualitas Air Limbah</h3>
          <p class="mt-1 text-sm text-slate-500">{{ subtitle }}</p>
        </div>
      </div>

      <div class="mb-4 grid gap-3 md:grid-cols-2">
        <ChartSummary field="ph" label="pH" :summary="phSummary" :decimals="2" />
        <ChartSummary field="tss" label="TSS" unit="mg/L" :summary="tssSummary" :decimals="tssPrecision" />
      </div>

      <p class="sr-only">{{ accessibilitySummary }}</p>
      <div role="img" aria-label="Grafik tren pH dan TSS">
        <ApexChart :key="chartKey" type="area" height="320" :options="options" :series="series" />
      </div>
    </section>
  </ChartState>
</template>
