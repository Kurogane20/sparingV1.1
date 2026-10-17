const DEFAULT_TIMEZONE = 'Asia/Jakarta';
const DEFAULT_SERIES = {
  ph: { label: 'pH', unit: '' },
  tss: { label: 'TSS', unit: 'mg/L' },
  debit: { label: 'Debit', unit: 'L/min' },
};

const SERIES_NAMES = {
  ph: 'pH',
  tss: 'TSS',
  debit: 'Debit',
};

const STATUS_FALLBACKS = {
  sensor_error: { status_label: 'Kesalahan Sensor', status_reason: 'explicit_sensor_error', status_severity: 'critical' },
  no_data: { status_label: 'Tidak Ada Data', status_reason: 'no_finite_measurement', status_severity: 'warning' },
  stale: { status_label: 'Tidak Ada Data', status_reason: 'stale_measurement', status_severity: 'warning' },
  critical: { status_label: 'Kritis', status_reason: 'danger_threshold_violated', status_severity: 'critical' },
  no_flow: { status_label: 'Aliran Terhenti', status_reason: 'no_flow_threshold_violated', status_severity: 'warning' },
  warning: { status_label: 'Peringatan', status_reason: 'warning_threshold_violated', status_severity: 'warning' },
  warning_threshold: { status_label: 'Peringatan', status_reason: 'warning_threshold_violated', status_severity: 'warning' },
  quality_check: { status_label: 'Peringatan', status_reason: 'quality_check_required', status_severity: 'warning' },
  rapid_change: { status_label: 'Peringatan', status_reason: 'rapid_change_detected', status_severity: 'warning' },
  low_flow: { status_label: 'Peringatan', status_reason: 'low_flow_detected', status_severity: 'warning' },
  normal: { status_label: 'Normal', status_reason: 'within_configured_limits', status_severity: 'info' },
};

export const DASHBOARD_DISPLAY_CONFIG = Object.freeze({
  // Small: niceScale already rounds the ceiling up to the next round tick.
  scaleHeadroom: 1.05,
  debitQuantile: 0.95,
  minimumScaleMax: 1,
});

export function finiteOrNull(value) {
  return typeof value === 'number' && Number.isFinite(value) ? value : null;
}

function copyValue(value) {
  if (Array.isArray(value)) return value.map(copyValue);
  if (value && typeof value === 'object') {
    return Object.fromEntries(Object.entries(value).map(([key, item]) => [key, copyValue(item)]));
  }
  return value;
}

function normalizePoints(points) {
  const byTimestamp = new Map();
  if (!Array.isArray(points)) return [];

  points.forEach((point) => {
    if (!point || typeof point !== 'object') return;
    const timestamp = Date.parse(point.ts);
    if (!Number.isFinite(timestamp)) return;
    byTimestamp.set(timestamp, {
      ...copyValue(point),
      ts: point.ts,
      value: finiteOrNull(point.value),
    });
  });

  return [...byTimestamp.entries()]
    .sort(([left], [right]) => left - right)
    .map(([, point]) => point);
}

function normalizeSeries(series, key) {
  const raw = series && typeof series === 'object' ? series : {};
  return {
    ...copyValue(raw),
    label: typeof raw.label === 'string' ? raw.label : DEFAULT_SERIES[key].label,
    unit: typeof raw.unit === 'string' ? raw.unit : DEFAULT_SERIES[key].unit,
    points: normalizePoints(raw.points),
  };
}

export function normalizeTimeseriesPayload(payload) {
  const raw = payload && typeof payload === 'object' ? payload : {};
  const meta = raw.meta && typeof raw.meta === 'object' ? raw.meta : {};
  const rawSeries = raw.series && typeof raw.series === 'object' ? raw.series : {};

  return {
    ...copyValue(raw),
    meta: {
      ...copyValue(meta),
      timezone: typeof meta.timezone === 'string' && meta.timezone ? meta.timezone : DEFAULT_TIMEZONE,
      is_partial: meta.is_partial === true,
    },
    series: {
      ...copyValue(rawSeries),
      ph: normalizeSeries(rawSeries.ph, 'ph'),
      tss: normalizeSeries(rawSeries.tss, 'tss'),
      debit: normalizeSeries(rawSeries.debit, 'debit'),
    },
    statistics: raw.statistics && typeof raw.statistics === 'object' ? copyValue(raw.statistics) : {},
    thresholds: raw.thresholds && typeof raw.thresholds === 'object' ? copyValue(raw.thresholds) : {},
    events: Array.isArray(raw.events) ? raw.events.map(copyValue) : [],
    event_total: finiteOrNull(raw.event_total) ?? 0,
  };
}

export function formatDashboardTimestamp(timestamp, timezone = DEFAULT_TIMEZONE, timeOnly = false) {
  const date = new Date(timestamp);
  if (Number.isNaN(date.getTime())) return '—';

  try {
    const parts = new Intl.DateTimeFormat('id-ID', {
      timeZone: typeof timezone === 'string' && timezone ? timezone : DEFAULT_TIMEZONE,
      day: '2-digit',
      month: 'short',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      hourCycle: 'h23',
      numberingSystem: 'latn',
    }).formatToParts(date);
    const value = Object.fromEntries(parts.map(({ type, value: part }) => [type, part]));
    const clock = `${value.hour}:${value.minute}`;
    return timeOnly ? clock : `${value.day} ${value.month} ${value.year} • ${clock}`;
  } catch {
    return '—';
  }
}

function fieldPoints(snapshot, field) {
  return Array.isArray(snapshot?.series?.[field]?.points) ? snapshot.series[field].points : [];
}

function finiteValues(points) {
  return points.map((point) => finiteOrNull(point?.value)).filter((value) => value !== null);
}

function firstText(...values) {
  return values.find((value) => typeof value === 'string' && value.trim()) ?? null;
}

function sourceText(value) {
  if (typeof value === 'string' && value.trim()) return value;
  if (!value || typeof value !== 'object') return null;
  return firstText(value.label, value.name, value.title, value.source_label);
}

function thresholdEntry(container, names) {
  if (typeof container === 'number') return { value: finiteOrNull(container), source: null };
  if (!container || typeof container !== 'object') return null;
  const raw = names.map((name) => container[name]).find((value) => value !== undefined);
  if (raw === undefined) return null;
  if (typeof raw === 'number') {
    return {
      value: finiteOrNull(raw),
      source: sourceText(container.source ?? container.source_metadata ?? container.metadata),
    };
  }
  if (!raw || typeof raw !== 'object') return null;
  return {
    value: finiteOrNull(raw.value ?? raw.limit ?? raw.threshold),
    source: sourceText(raw.source ?? raw.source_metadata ?? raw.metadata),
  };
}

function annotationLabel(text, source) {
  return { text: source ? `${text} · ${source}` : text };
}

// The backend `source` is a provenance code (site_alert_rule / unconfigured),
// not text for operators; only human-written sources belong on the chart.
const PROVENANCE_CODE = /^[a-z0-9_]+$/;

function thresholdMetadata(container) {
  if (!container || typeof container !== 'object') return null;
  const source = sourceText(container.source);
  return [source && !PROVENANCE_CODE.test(source) ? source : null, sourceText(container.regulation)]
    .filter((value) => value !== null)
    .join(' · ') || null;
}

const FLAT_THRESHOLD_ANNOTATIONS = [
  { key: 'warning_min', text: 'Peringatan minimum', color: '#f59e0b' },
  { key: 'warning_max', text: 'Peringatan maksimum', color: '#f59e0b' },
  { key: 'danger_min', text: 'Bahaya minimum', color: '#dc2626' },
  { key: 'danger_max', text: 'Bahaya maksimum', color: '#dc2626' },
];

function flatThresholdValues(container) {
  if (!container || typeof container !== 'object') return [];
  return FLAT_THRESHOLD_ANNOTATIONS
    .map(({ key, text, color }) => ({
      value: finiteOrNull(container[key]),
      text,
      color,
    }))
    .filter(({ value }) => value !== null);
}

export function buildApexSeries(snapshot, fields = []) {
  if (!Array.isArray(fields)) return [];
  return fields
    .filter((field) => Object.hasOwn(SERIES_NAMES, field))
    .map((field) => ({
      name: SERIES_NAMES[field],
      data: fieldPoints(snapshot, field)
        .map((point) => ({ x: Date.parse(point?.ts), y: finiteOrNull(point?.value) }))
        .filter((point) => Number.isFinite(point.x)),
    }));
}

export function buildThresholdAnnotations(snapshot, field) {
  const thresholds = snapshot?.thresholds?.[field];
  const annotations = [];
  const add = (entry, text, color) => {
    if (entry?.value === null || entry?.value === undefined) return;
    annotations.push({
      y: entry.value,
      borderColor: color,
      strokeDashArray: 4,
      label: annotationLabel(text, entry.source),
    });
  };

  const flatValues = flatThresholdValues(thresholds);
  if (flatValues.length) {
    const metadata = thresholdMetadata(thresholds);
    flatValues.forEach(({ value, text, color }) => add({ value, source: metadata }, text, color));
    return annotations;
  }

  if (field === 'ph') {
    add(thresholdEntry(thresholds, ['lower', 'min', 'minimum']), 'Batas bawah', '#2563eb');
    add(thresholdEntry(thresholds, ['upper', 'max', 'maximum']), 'Batas atas', '#dc2626');
  }
  if (field === 'tss') {
    add(thresholdEntry(thresholds, ['reference', 'limit', 'value', 'maximum', 'max']), 'Nilai acuan', '#dc2626');
  }
  return annotations;
}

function eventCategory(event) {
  const value = event?.category ?? event?.type ?? event?.kind ?? event?.context?.category;
  if (typeof value !== 'string') return 'anomaly';
  const type = value.toLowerCase();
  if (['threshold_warning', 'threshold_danger', 'threshold'].includes(type)) return 'threshold';
  if (['rapid_change', 'rapid'].includes(type)) return 'rapid';
  if (['sensor_anomaly', 'sensor_error', 'op_status', 'sensor_fail', 'sensor_recover', 'anomaly'].includes(type)) return 'anomaly';
  if (['flow_drop', 'no_flow', 'flow_restored', 'low_flow_tss_check', 'flow'].includes(type)) return 'flow';
  if (['data_gap', 'gap', 'logger_offline', 'logger_online'].includes(type) || type.startsWith('logger_')) return 'gap';
  return 'anomaly';
}

const EVENT_SHAPES = {
  threshold: 'triangle',
  rapid: 'diamond',
  anomaly: 'circle',
  flow: 'square',
  gap: 'cross',
};

export function buildEventAnnotations(snapshot) {
  const events = Array.isArray(snapshot?.events) ? snapshot.events : [];
  return events.flatMap((event) => {
    const x = Date.parse(event?.ts);
    if (!Number.isFinite(x)) return [];
    const category = eventCategory(event);
    const genericValue = finiteOrNull(
      event?.context?.current
      ?? event?.value
      ?? event?.context?.value
      ?? event?.context?.debit?.value
      ?? event?.context?.tss?.current,
    );
    const debitValue = finiteOrNull(event?.context?.debit?.value);
    const y = event?.type === 'low_flow_tss_check' && debitValue !== null
      ? debitValue
      : genericValue;
    const annotation = {
      x,
      marker: { shape: EVENT_SHAPES[category] ?? EVENT_SHAPES.anomaly },
      label: { text: firstText(event?.label, event?.message, event?.title, category) ?? '' },
    };
    return y === null ? [annotation] : [{ ...annotation, y }];
  });
}

export function getFieldSummary(snapshot, field) {
  const summary = snapshot?.statistics?.[field];
  const series = snapshot?.series?.[field];
  const result = summary && typeof summary === 'object' ? copyValue(summary) : {};
  const fallback = STATUS_FALLBACKS[result.status ?? series?.status] ?? {};
  const statusLabel = firstText(result.status_label, series?.status_label, fallback.status_label);
  const statusReason = firstText(result.status_reason, series?.status_reason, fallback.status_reason);
  const statusSeverity = firstText(result.status_severity, series?.status_severity, fallback.status_severity);

  if (statusLabel) result.status_label = statusLabel;
  if (statusReason) result.status_reason = statusReason;
  if (statusSeverity) result.status_severity = statusSeverity;
  return result;
}

function scaleMax(value) {
  const finite = finiteOrNull(value);
  const base = finite !== null && finite > 0 ? finite : DASHBOARD_DISPLAY_CONFIG.minimumScaleMax;
  return base * DASHBOARD_DISPLAY_CONFIG.scaleHeadroom;
}

const NICE_STEPS = [1, 2, 2.5, 5, 10];

function stepDecimals(step) {
  let decimals = 0;
  while (decimals < 6 && Math.abs(Math.round(step * 10 ** decimals) - step * 10 ** decimals) > 1e-9) decimals += 1;
  return decimals;
}

// Axis bounds on a 1/2/2.5/5 × 10^n step, so every tick label is a round
// number at an even spacing (no 15.71/31.43…, no duplicated rounded labels).
export function niceScale(minimum, maximum, maxTicks = 6) {
  let lo = finiteOrNull(minimum) ?? 0;
  let hi = finiteOrNull(maximum) ?? lo;
  if (hi < lo) [lo, hi] = [hi, lo];
  if (hi === lo) hi = lo + (Math.abs(lo) || 1);
  const rough = (hi - lo) / maxTicks;
  const magnitude = 10 ** Math.floor(Math.log10(rough));
  const step = NICE_STEPS.find((candidate) => rough / magnitude <= candidate + 1e-9) * magnitude;
  const decimals = stepDecimals(step);
  const fixed = (value) => Number(value.toFixed(decimals));
  const niceMin = Math.floor(lo / step + 1e-9) * step;
  const niceMax = Math.ceil(hi / step - 1e-9) * step;
  return {
    min: fixed(niceMin),
    max: fixed(niceMax),
    tickAmount: Math.round((niceMax - niceMin) / step),
    decimals,
  };
}

function thresholdCandidates(snapshot, field, names) {
  const flat = flatThresholdValues(snapshot?.thresholds?.[field]).map(({ value }) => value);
  const named = names.map((name) => thresholdEntry(snapshot?.thresholds?.[field], [name])?.value);
  return [...flat, ...named].filter((value) => value !== null && value !== undefined);
}

export function getPhScale(snapshot) {
  const candidates = [
    ...finiteValues(fieldPoints(snapshot, 'ph')),
    finiteOrNull(getFieldSummary(snapshot, 'ph').current),
    ...thresholdCandidates(snapshot, 'ph', ['lower', 'min', 'minimum', 'upper', 'max', 'maximum']),
  ].filter((value) => value !== null);
  if (!candidates.length) return niceScale(0, 14, 7);
  const lo = Math.max(0, Math.min(...candidates) - 0.5);
  const hi = Math.min(14, Math.max(...candidates) + 0.5);
  return niceScale(lo, hi);
}

export function getTssScale(snapshot) {
  const values = finiteValues(fieldPoints(snapshot, 'tss'));
  const current = finiteOrNull(getFieldSummary(snapshot, 'tss').current);
  const candidates = [
    ...values,
    current,
    ...thresholdCandidates(snapshot, 'tss', ['reference', 'limit', 'value', 'maximum', 'max']),
  ].filter((value) => value !== null && value !== undefined);
  const maximum = candidates.length ? Math.max(...candidates) : 0;
  return niceScale(0, scaleMax(maximum));
}

function quantile(values, percentile) {
  if (!values.length) return 0;
  const sorted = [...values].sort((left, right) => left - right);
  const index = (sorted.length - 1) * percentile;
  const lower = Math.floor(index);
  const upper = Math.ceil(index);
  return sorted[lower] + (sorted[upper] - sorted[lower]) * (index - lower);
}

export function getDebitScale(snapshot, mode = 'normal') {
  const values = finiteValues(fieldPoints(snapshot, 'debit'));
  const current = finiteOrNull(getFieldSummary(snapshot, 'debit').current);
  const fullMaximum = Math.max(0, ...values, current ?? 0);

  if (mode === 'full') {
    return { ...niceScale(0, scaleMax(fullMaximum)), outlierCount: 0 };
  }

  const displayQuantile = quantile(values, DASHBOARD_DISPLAY_CONFIG.debitQuantile);
  const normalMaximum = Math.max(displayQuantile, current ?? 0);
  const scale = niceScale(0, scaleMax(normalMaximum));
  return {
    ...scale,
    // Values the chart clips at its visible ceiling.
    outlierCount: values.filter((value) => value > scale.max).length,
  };
}

const MINUTE_MS = 60 * 1000;
const TIME_STEPS_MS = [5, 10, 15, 30, 60, 120, 180, 360, 720, 1440].map((minutes) => minutes * MINUTE_MS);

function timezoneOffsetMs(timestamp, timeZone) {
  try {
    const parts = Object.fromEntries(new Intl.DateTimeFormat('en-US', {
      timeZone, hourCycle: 'h23', year: 'numeric', month: '2-digit', day: '2-digit',
      hour: '2-digit', minute: '2-digit', second: '2-digit',
    }).formatToParts(new Date(timestamp)).map(({ type, value }) => [type, Number(value)]));
    const wallClockAsUtc = Date.UTC(parts.year, parts.month - 1, parts.day, parts.hour, parts.minute, parts.second);
    return wallClockAsUtc - Math.floor(timestamp / 1000) * 1000;
  } catch {
    return 0;
  }
}

// x-axis bounds for ApexCharts: evenly spaced ticks only land on round local
// times (00:00, 02:00 …) when min/max are aligned to the step in the site's
// timezone; left to itself a formatted datetime axis printed 01:48, 03:37 …
export function timeAxisRange(dateFrom, dateTo, timeZone = DEFAULT_TIMEZONE, maxTicks = 10) {
  const from = Date.parse(dateFrom);
  const to = Date.parse(dateTo);
  if (!Number.isFinite(from) || !Number.isFinite(to) || to <= from) return null;
  const offset = timezoneOffsetMs(from, timeZone);
  const aligned = (step) => {
    const min = Math.floor((from + offset) / step) * step - offset;
    const max = Math.ceil((to + offset) / step) * step - offset;
    return { min, max, tickAmount: Math.round((max - min) / step) };
  };
  for (const step of TIME_STEPS_MS) {
    const axis = aligned(step);
    if (axis.tickAmount <= maxTicks) return axis;
  }
  const day = TIME_STEPS_MS.at(-1);
  return aligned(day * Math.ceil((to - from) / (day * maxTicks)));
}

export function formatDecimal(value, decimals = 2) {
  const number = finiteOrNull(value);
  if (number === null) return null;
  return number.toLocaleString('id-ID', { minimumFractionDigits: decimals, maximumFractionDigits: decimals });
}

// Event context values have no fixed precision: show what is significant.
export function formatMeasurement(value) {
  const number = finiteOrNull(value);
  if (number === null) return null;
  return number.toLocaleString('id-ID', { maximumFractionDigits: 3 });
}

const EVENT_LEGEND = [
  { key: 'critical', color: '#B03030', label: 'Peristiwa kritis' },
  { key: 'warning', color: '#9A6B00', label: 'Peristiwa peringatan' },
  { key: 'info', color: '#475569', label: 'Peristiwa informasi' },
];

// Legend for the event markers drawn on a chart: severity-coloured points on
// the line, and dashed vertical lines for logger/data events without a value.
export function eventLegendItems(pointEvents, hasLineEvents) {
  const severities = new Set((Array.isArray(pointEvents) ? pointEvents : [])
    .map((event) => (EVENT_LEGEND.some(({ key }) => key === event?.severity) ? event.severity : 'info')));
  const items = EVENT_LEGEND.filter(({ key }) => severities.has(key));
  if (hasLineEvents) items.push({ key: 'line', color: '#94a3b8', label: 'Peristiwa logger/data' });
  return items;
}
