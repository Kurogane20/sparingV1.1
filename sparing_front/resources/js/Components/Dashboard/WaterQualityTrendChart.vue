<script setup>
import { computed } from 'vue';
import ApexChart from 'vue3-apexcharts';
import ChartState from './ChartState.vue';
import ChartSummary from './ChartSummary.vue';
import {
  buildApexSeries,
  buildEventAnnotations,
  buildThresholdAnnotations,
  eventLegendItems,
  formatDashboardTimestamp,
  formatDecimal,
  formatMeasurement,
  getFieldSummary,
  getPhScale,
  getTssScale,
  timeAxisRange,
} from '@/Utils/dashboardTimeseries.js';

const props = defineProps({
  snapshot: { type: Object, default: null },
  state: { type: String, default: 'idle' },
  stale: { type: Boolean, default: false },
  focusedEventId: { type: [String, Number], default: null },
  reducedMotion: { type: Boolean, default: false },
});

const emit = defineEmits(['retry']);

// pH and TSS are drawn as two charts with one axis each: on a shared chart the
// TSS axis was forced onto pH's 0–14 grid (ticks like 15.71, 31.43) and it was
// unclear which axis a limit line belonged to. The charts must NOT share an
// ApexCharts group — updateOptions() on one grouped chart is applied to every
// chart in the group and overwrote the other charts' axes in production.
const FIELDS = ['ph', 'tss'];
const FIELD_META = {
  ph: { label: 'pH', color: '#0f766e', chartId: 'dashboard-ph', chartKey: 'water-quality:ph:v2' },
  tss: { label: 'TSS', color: '#7c3aed', chartId: 'dashboard-tss', chartKey: 'water-quality:tss:v2' },
};

const safeSnapshot = computed(() => props.snapshot && typeof props.snapshot === 'object' ? props.snapshot : {});
const timezone = computed(() => safeSnapshot.value?.meta?.timezone || 'Asia/Jakarta');
const summaries = computed(() => ({
  ph: getFieldSummary(safeSnapshot.value, 'ph'),
  tss: getFieldSummary(safeSnapshot.value, 'tss'),
}));
const scales = computed(() => ({
  ph: getPhScale(safeSnapshot.value),
  tss: getTssScale(safeSnapshot.value),
}));
const chartState = computed(() => props.stale && props.state === 'ready' ? 'stale' : props.state);
const partialReasons = computed(() => Array.isArray(safeSnapshot.value?.meta?.partial_reasons) ? safeSnapshot.value.meta.partial_reasons : []);
const availability = computed(() => safeSnapshot.value?.meta?.availability_pct);
const tssPrecision = computed(() => {
  const precision = safeSnapshot.value?.series?.tss?.precision;
  return Number.isInteger(precision) && precision >= 0 && precision <= 4 ? precision : 2;
});
const decimalsFor = (field) => (field === 'tss' ? tssPrecision.value : 2);
// Ticks on round local times; fewer on phones.
const timeAxis = computed(() => timeAxisRange(safeSnapshot.value?.meta?.date_from, safeSnapshot.value?.meta?.date_to, timezone.value) ?? {});
const phoneTimeAxis = computed(() => timeAxisRange(safeSnapshot.value?.meta?.date_from, safeSnapshot.value?.meta?.date_to, timezone.value, 4) ?? {});

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

function pointForTimestamp(field, timestamp) {
  const points = safeSnapshot.value?.series?.[field]?.points;
  if (!Array.isArray(points) || timestamp === null) return {};
  return points.find((point) => timestampValue(point?.ts) === timestamp) ?? {};
}

function formatValue(value, decimals, unit = '') {
  const formatted = formatDecimal(value, decimals);
  return formatted === null ? 'Data Tidak Tersedia' : `${formatted}${unit ? ` ${unit}` : ''}`;
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
  const values = FIELDS.map((field) => summaries.value[field]?.current_ts)
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
    return [date, 'Real-time', `Update terakhir ${time}`].join(' • ');
  }
  const start = localDate(meta.date_from);
  const end = localDate(meta.date_to);
  return [`Periode ${start} – ${end}`, `Resolusi ${formatResolution(meta.resolution_seconds)}`].join(' • ');
});

function isWaterEvent(event) {
  if (!event || typeof event !== 'object') return false;
  const field = typeof event.field === 'string' ? event.field.toLowerCase() : '';
  const type = typeof event.type === 'string' ? event.type.toLowerCase() : '';
  if (field === 'debit' || ['flow_drop', 'no_flow', 'flow_restored', 'low_flow_tss_check'].includes(type)) return false;
  return field === 'ph' || field === 'tss' || !field || ['data_gap', 'gap', 'logger_offline', 'logger_online', 'op_status', 'sensor_fail', 'sensor_recover'].includes(type);
}

const eventField = (event) => (typeof event?.field === 'string' ? event.field.toLowerCase() : '');

function eventLabel(event) {
  return typeof event?.label === 'string' && event.label.trim()
    ? event.label : (typeof event?.message === 'string' && event.message.trim() ? event.message : 'Event pemantauan');
}

const waterEvents = computed(() => (Array.isArray(safeSnapshot.value?.events) ? safeSnapshot.value.events : []).filter(isWaterEvent));
const fieldEvents = (field) => waterEvents.value.filter((event) => eventField(event) === field);

// Point labels overlapped badly in production; details live in the tooltip and event list.
const SEVERITY_FILL = { critical: '#B03030', warning: '#9A6B00' };

function eventAnnotations(field) {
  return fieldEvents(field).flatMap((event) => {
    const focused = String(event.id) === String(props.focusedEventId);
    return buildEventAnnotations({ events: [event] }).map(({ label: _label, ...annotation }) => ({
      ...annotation,
      id: event.id,
      seriesIndex: 0,
      yAxisIndex: 0,
      marker: {
        ...annotation.marker,
        size: focused ? 9 : 6,
        fillColor: focused ? '#0f766e' : (SEVERITY_FILL[event.severity] ?? '#475569'),
      },
    }));
  });
}

// Events without a parameter (logger, data gap, operation) are vertical lines on both charts.
const globalEventAnnotations = computed(() => waterEvents.value.flatMap((event) => {
  const field = eventField(event);
  const x = Date.parse(event.ts);
  if ((field === 'ph' || field === 'tss') || !Number.isFinite(x)) return [];
  const focused = String(event.id) === String(props.focusedEventId);
  return [{
    id: event.id,
    x,
    borderColor: focused ? '#0f766e' : '#94a3b8',
    strokeDashArray: 3,
  }];
}));

// Threshold lines keep their colour; their text lives in one legend below the charts.
const thresholdAnnotations = (field) => buildThresholdAnnotations(safeSnapshot.value, field)
  .map((annotation) => ({ ...annotation, yAxisIndex: 0 }));

const thresholdLegend = computed(() => {
  const items = new Map();
  const sources = new Set();
  for (const annotation of [...thresholdAnnotations('ph'), ...thresholdAnnotations('tss')]) {
    const [kind = '', ...source] = (annotation.label?.text ?? '').split(' · ');
    // "Peringatan minimum" / "Peringatan maksimum" share one colour and one entry.
    const name = /^(Peringatan|Bahaya)\b/.exec(kind)?.[1] ?? kind;
    if (name && !items.has(`${annotation.borderColor}|${name}`)) items.set(`${annotation.borderColor}|${name}`, { name, color: annotation.borderColor });
    source.forEach((text) => sources.add(text));
  }
  return { items: [...items.values()], source: [...sources].join(' · ') };
});

const eventLegend = computed(() => eventLegendItems(
  [...fieldEvents('ph'), ...fieldEvents('tss')],
  globalEventAnnotations.value.length > 0,
));

function currentAnnotation(field) {
  const summary = summaries.value[field];
  const x = Date.parse(summary?.current_ts);
  const y = finite(summary?.current);
  if (!Number.isFinite(x) || y === null) return [];
  return [{
    id: `current-${field}`,
    x,
    y,
    seriesIndex: 0,
    yAxisIndex: 0,
    marker: { size: 7, fillColor: FIELD_META[field].color, strokeColor: '#ffffff', strokeWidth: 2 },
  }];
}

const series = computed(() => ({
  ph: buildApexSeries(safeSnapshot.value, ['ph']),
  tss: buildApexSeries(safeSnapshot.value, ['tss']),
}));

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
  const numeric = (label, value) => finite(value) === null ? '' : `<div>${label}: ${escapeHtml(formatMeasurement(value))}</div>`;
  const interval = finite(context.interval_seconds);
  const reason = typeof context.reason === 'string' && context.reason.trim() ? `<div>Alasan: ${escapeHtml(context.reason)}</div>` : '';
  return [
    `<div>Event: ${escapeHtml(eventLabel(event))}</div>`,
    numeric('Nilai saat ini', context.current),
    numeric('Baseline', context.baseline),
    numeric('Perubahan', context.delta),
    finite(context.percent) === null ? '' : `<div>Persentase: ${escapeHtml(formatMeasurement(context.percent))}%</div>`,
    interval === null ? '' : `<div>Interval: ${escapeHtml(formatResolution(interval))}</div>`,
    numeric('TSS event', context.tss?.current ?? context.tss?.value),
    numeric('Debit event', context.debit?.value),
    reason,
  ].join('');
}

function matchingEventDetails(field, timestamp) {
  if (timestamp === null) return '';
  return waterEvents.value
    .filter((event) => [field, ''].includes(eventField(event)) && timestampValue(event?.ts) === timestamp)
    .map(eventContextDetails)
    .join('');
}

function tooltipFor(field) {
  return (context = {}) => {
    const timestamp = hoveredTimestamp(context);
    const point = pointForTimestamp(field, timestamp);
    const unit = responseUnit(field);
    const decimals = decimalsFor(field);
    const resolution = formatResolution(safeSnapshot.value?.meta?.resolution_seconds);
    return [
      '<div class="dashboard-chart-tooltip">',
      `<div><strong>${escapeHtml(formatDashboardTimestamp(timestamp, timezone.value))}</strong></div>`,
      resolution === 'tidak tersedia' ? '' : `<div>Resolusi: ${escapeHtml(resolution)}</div>`,
      `<div><strong>${FIELD_META[field].label}:</strong> ${escapeHtml(formatValue(point.value, decimals, unit))}</div>`,
      `<div>Status: ${escapeHtml(displayStatus(point, summaries.value[field]))}</div>`,
      `<div>Kualitas: ${escapeHtml(displayQuality(point))}</div>`,
      pointBucketDetails(point, decimals, unit),
      matchingEventDetails(field, timestamp),
      '</div>',
    ].join('');
  };
}

function axisTitle(field) {
  return field === 'tss' ? `TSS (${responseUnit('tss')})` : 'pH';
}

function chartOptions(field) {
  const scale = scales.value[field];
  return {
    chart: {
      id: FIELD_META[field].chartId,
      toolbar: { show: false },
      zoom: { enabled: false },
      animations: { enabled: !props.reducedMotion, speed: props.reducedMotion ? 0 : 180 },
    },
    colors: [FIELD_META[field].color],
    stroke: { curve: 'straight', width: 2 },
    dataLabels: { enabled: false },
    markers: { size: 0 },
    grid: { borderColor: '#e2e8f0', strokeDashArray: 3, padding: { left: 4, right: 8 } },
    legend: { show: false },
    xaxis: { type: 'datetime', ...timeAxis.value, labels: { datetimeUTC: true, formatter: formatXAxisLabel, style: { fontSize: '11px' } } },
    yaxis: [{
      seriesName: FIELD_META[field].label,
      min: scale.min,
      max: scale.max,
      tickAmount: scale.tickAmount,
      title: { text: axisTitle(field) },
      labels: { minWidth: 40, formatter: (value) => formatDecimal(value, scale.decimals) ?? '' },
    }],
    annotations: {
      yaxis: thresholdAnnotations(field).map(({ label: _label, ...annotation }) => annotation),
      points: [...eventAnnotations(field), ...currentAnnotation(field)],
      xaxis: globalEventAnnotations.value,
    },
    tooltip: { shared: true, intersect: false, custom: tooltipFor(field) },
    responsive: [{
      breakpoint: 640,
      options: { xaxis: { ...phoneTimeAxis.value, labels: { datetimeUTC: true, formatter: formatXAxisLabel, style: { fontSize: '10px' } } } },
    }],
  };
}

const options = computed(() => ({ ph: chartOptions('ph'), tss: chartOptions('tss') }));

const accessibilitySummary = computed(() => {
  const describe = (label, summary, decimals, unit) => `${label}: saat ini ${formatValue(summary?.current, decimals, unit)}, status ${summary?.status_label ?? summary?.status ?? 'tidak tersedia'}, ketersediaan ${finite(summary?.availability_pct) ?? 'tidak tersedia'}%.`;
  return `Ringkasan aksesibilitas. ${describe('pH', summaries.value.ph, 2)} ${describe('TSS', summaries.value.tss, tssPrecision.value, responseUnit('tss'))}`;
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
    <section class="sensor-card min-w-0 max-w-full rounded-lg border border-slate-200 bg-white p-4 motion-reduce:hover:transform-none motion-reduce:transition-none">
      <div class="mb-4 flex flex-wrap items-start justify-between gap-2">
        <div class="min-w-0">
          <h3 class="text-base font-semibold text-[#12333B]">Tren Kualitas Air Limbah</h3>
          <p class="mt-1 text-sm text-slate-500">{{ subtitle }}</p>
        </div>
      </div>

      <div class="mb-4 grid gap-3 md:grid-cols-2">
        <ChartSummary field="ph" label="pH" :summary="summaries.ph" :decimals="2" />
        <ChartSummary field="tss" label="TSS" :unit="responseUnit('tss')" :summary="summaries.tss" :decimals="tssPrecision" />
      </div>

      <!-- Other water-quality readings (COD, NH3-N, ...) supplied by the page. -->
      <slot name="extra" />

      <p class="sr-only">{{ accessibilitySummary }}</p>
      <div class="min-w-0 max-w-full space-y-2" role="img" aria-label="Grafik tren pH dan TSS">
        <div v-for="field in FIELDS" :key="field" class="min-w-0 max-w-full">
          <ApexChart :key="FIELD_META[field].chartKey" type="line" height="210" :options="options[field]" :series="series[field]" />
        </div>
      </div>
      <div v-if="thresholdLegend.items.length" class="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-slate-600" aria-label="Keterangan garis batas">
        <span v-for="item in thresholdLegend.items" :key="`${item.color}|${item.name}`" class="inline-flex items-center gap-1.5">
          <span class="inline-block w-5 border-t-2 border-dashed" :style="{ borderColor: item.color }" aria-hidden="true"></span>{{ item.name }}
        </span>
        <span v-if="thresholdLegend.source" class="text-slate-500">· {{ thresholdLegend.source }}</span>
      </div>
      <div v-if="eventLegend.length" class="mt-1 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-slate-600" aria-label="Keterangan penanda peristiwa">
        <span v-for="item in eventLegend" :key="item.key" class="inline-flex items-center gap-1.5">
          <span v-if="item.key === 'line'" class="inline-block h-3 border-l-2 border-dashed" :style="{ borderColor: item.color }" aria-hidden="true"></span>
          <span v-else class="inline-block h-2.5 w-2.5 rounded-full" :style="{ background: item.color }" aria-hidden="true"></span>{{ item.label }}
        </span>
      </div>
    </section>
  </ChartState>
</template>
