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
  normal: { status_label: 'Normal', status_reason: 'Dalam kondisi normal', status_severity: 'success' },
  warning: { status_label: 'Peringatan', status_reason: 'Memerlukan perhatian', status_severity: 'warning' },
  danger: { status_label: 'Melebihi batas', status_reason: 'Memerlukan tindak lanjut', status_severity: 'danger' },
  critical: { status_label: 'Kritis', status_reason: 'Memerlukan tindak lanjut segera', status_severity: 'danger' },
  no_data: { status_label: 'Data tidak tersedia', status_reason: 'Belum ada data pengukuran', status_severity: 'muted' },
};

export const DASHBOARD_DISPLAY_CONFIG = Object.freeze({
  scaleHeadroom: 1.1,
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
  return typeof value === 'string' ? value.toLowerCase() : 'anomaly';
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
    const y = finiteOrNull(event?.value ?? event?.context?.value);
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

export function getTssScale(snapshot, mode = 'normal') {
  const values = finiteValues(fieldPoints(snapshot, 'tss'));
  const current = finiteOrNull(getFieldSummary(snapshot, 'tss').current);
  const reference = thresholdEntry(snapshot?.thresholds?.tss, ['reference', 'limit', 'value', 'maximum', 'max'])?.value;
  const candidates = [...values, current, reference].filter((value) => value !== null && value !== undefined);
  const maximum = candidates.length ? Math.max(...candidates) : 0;
  return { min: 0, max: scaleMax(maximum) };
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
    return { min: 0, max: scaleMax(fullMaximum), outlierCount: 0 };
  }

  const displayQuantile = quantile(values, DASHBOARD_DISPLAY_CONFIG.debitQuantile);
  const normalMaximum = Math.max(displayQuantile, current ?? 0);
  return {
    min: 0,
    max: scaleMax(normalMaximum),
    outlierCount: values.filter((value) => value > normalMaximum).length,
  };
}
