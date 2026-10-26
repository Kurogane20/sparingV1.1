// Status logic for the "Bentang air" dashboard: what the status band says,
// how the month went, and where a reading sits against its limit. Pure
// functions, so every state is testable without a browser.
import { parseUTC } from './helpers.js';
import { SITE_STALE_MS } from './siteStatus.js';

// Readings arrive in hourly bursts, so an hour-old reading is normal. Same
// threshold as the site chips, so a chip and the band never disagree.
export const STALE_AFTER_MS = SITE_STALE_MS;
// A reading dated ahead of the clock (a logger stamping local time as UTC)
// would otherwise look fresh for hours after the logger stops.
const FUTURE_SKEW_MS = 10 * 60 * 1000;

export const FIELD_LABELS = Object.freeze({
  ph: 'pH',
  tss: 'TSS',
  cod: 'COD',
  nh3n: 'NH₃-N',
  debit: 'Debit',
  temp: 'Suhu',
});

const finite = (value) => (typeof value === 'number' && Number.isFinite(value) ? value : null);
// /data/last and /alerts return naive UTC timestamps (MySQL); parseUTC reads
// them as UTC rather than the browser's local time.
const epoch = (value) => (value ? parseUTC(value).getTime() : NaN);
const isoUTC = (ms) => new Date(ms).toISOString();

function activeRules(rules) {
  const list = Array.isArray(rules) ? rules : Object.values(rules ?? {});
  return list.filter((rule) => rule && rule.is_active !== false
    && (finite(rule.danger_min) !== null || finite(rule.danger_max) !== null));
}

// Mirrors app/utils/quality.py field_is_flagged: quality_fields ",tss,cod,"
// names the flagged parameters; a flag without it (older rows) covers the row.
function fieldFlagged(row, field) {
  if (!row.quality_flag) return false;
  if (typeof row.quality_fields !== 'string') return true;
  return row.quality_fields.split(',').includes(field);
}

export function isOutsideLimit(value, rule) {
  const reading = finite(value);
  if (reading === null || !rule) return false;
  const min = finite(rule.danger_min);
  const max = finite(rule.danger_max);
  return (min !== null && reading < min) || (max !== null && reading > max);
}

export function joinLabels(fields) {
  const labels = fields.map((field) => FIELD_LABELS[field] ?? field);
  if (labels.length <= 1) return labels[0] ?? '';
  return `${labels.slice(0, -1).join(', ')} dan ${labels[labels.length - 1]}`;
}

/** 'YYYY-MM-DD' of `at` in the site's timezone — the day compliance-daily counts. */
export function localDateISO(timeZone = 'Asia/Jakarta', at = new Date()) {
  const options = { year: 'numeric', month: '2-digit', day: '2-digit' };
  let parts;
  try {
    parts = new Intl.DateTimeFormat('en-US', { ...options, timeZone }).formatToParts(at);
  } catch {
    // Unknown zone name: fall back to WIB, like the backend's site_utc_offset.
    parts = new Intl.DateTimeFormat('en-US', { ...options, timeZone: 'Asia/Jakarta' }).formatToParts(at);
  }
  const part = (type) => parts.find((entry) => entry.type === type)?.value;
  return `${part('year')}-${part('month')}-${part('day')}`;
}

/**
 * The status band's state; the first match wins:
 *   no_rules → stale → breach_now → breached_today → compliant → unverified
 * rules: alert rules (array or field → rule map); latest: the /data/last row;
 * todayStatus: today's status from /stats/compliance-daily (null when unknown);
 * activeAlerts: /alerts?status=active for the site.
 */
export function bandState({
  rules, latest, todayStatus = null, activeAlerts = [], now = Date.now(), staleAfterMs = STALE_AFTER_MS,
} = {}) {
  const active = activeRules(rules);
  if (!active.length) return { state: 'no_rules' };

  const breachedToday = todayStatus === 'violation';
  const lastTs = epoch(latest?.ts);
  if (!Number.isFinite(lastTs)) return { state: 'stale', reason: 'none', lastTs: null, breachedToday };
  // A logger clock running ahead is not "data stopped"; the band says so.
  if (lastTs - now > FUTURE_SKEW_MS) return { state: 'stale', reason: 'future', lastTs: isoUTC(lastTs), breachedToday };
  if (now - lastTs > staleAfterMs) return { state: 'stale', reason: 'old', lastTs: isoUTC(lastTs), breachedToday };

  // An operational-status row (calibration, stopped, malfunction) is not a measurement.
  const measurement = latest.op_status === null || latest.op_status === undefined;
  const breaches = measurement
    ? active
      .filter((rule) => !fieldFlagged(latest, rule.field) && isOutsideLimit(latest[rule.field], rule))
      .map((rule) => ({
        field: rule.field,
        value: latest[rule.field],
        min: finite(rule.danger_min),
        max: finite(rule.danger_max),
      }))
    : [];
  if (breaches.length) {
    const fields = breaches.map((breach) => breach.field);
    const oldest = (Array.isArray(activeAlerts) ? activeAlerts : [])
      .filter((item) => fields.includes(item?.field) && (item.category ?? 'compliance') === 'compliance')
      .map((item) => ({ item, at: epoch(item.triggered_at) }))
      .filter(({ at }) => Number.isFinite(at))
      .reduce((first, entry) => (!first || entry.at < first.at ? entry : first), null);
    const below = breaches.some((breach) => breach.min !== null && breach.value < breach.min);
    return {
      state: 'breach_now',
      fields,
      breaches,
      title: `${joinLabels(fields)} ${below ? 'di luar' : 'melewati'} baku mutu`,
      since: oldest ? isoUTC(oldest.at) : null,
      alertId: oldest?.item.id ?? null,
    };
  }
  // Which ruled values of the latest row could be judged at all (not null, not
  // flagged, not an operational-status row). The band only vouches for these.
  const judged = measurement
    ? active.filter((rule) => finite(latest[rule.field]) !== null && !fieldFlagged(latest, rule.field)).map((rule) => rule.field)
    : [];
  const unjudged = active.map((rule) => rule.field).filter((field) => !judged.includes(field));
  if (breachedToday) return { state: 'breached_today', judged, unjudged };
  // "Patuh hari ini" only once today's measurements were judged compliant.
  if (todayStatus === 'ok' || todayStatus === 'warning') {
    return { state: 'compliant', nearLimit: todayStatus === 'warning' };
  }
  return { state: 'unverified', judged, unjudged };
}

/**
 * The month's compliance from /stats/compliance-daily days. A day counts as
 * compliant when it is `ok` or `warning` (a warning is not a violation); days
 * without measurements and days after `today` are left out.
 */
export function monthCompliance(days, today) {
  const cells = (Array.isArray(days) ? days : [])
    .filter((day) => typeof day?.date === 'string')
    .map(({ date, status }) => {
      if (date > today) return { date, status: 'future' };
      if (status === 'ok' || status === 'warning') return { date, status: 'ok' };
      if (status === 'violation') return { date, status: 'violation' };
      return { date, status: 'empty' };
    });
  const compliant = cells.filter((cell) => cell.status === 'ok').length;
  const judged = compliant + cells.filter((cell) => cell.status === 'violation').length;
  return {
    cells, compliant, judged, pct: judged ? Math.round((compliant / judged) * 1000) / 10 : null,
  };
}

/** Where a reading sits against its limit, as percentages of a bar track. */
export function limitPosition(value, rule) {
  const reading = finite(value);
  const min = finite(rule?.danger_min);
  const max = finite(rule?.danger_max);
  if (reading === null || (min === null && max === null)) return { kind: 'none' };
  const breach = isOutsideLimit(reading, rule);
  const clamp = (n) => Math.min(100, Math.max(0, n));
  if (min !== null && max !== null && max > min) {
    // The track runs half a range beyond each limit, so a value outside still shows.
    const pad = (max - min) / 2;
    const lo = min - pad;
    const hi = max + pad;
    const at = (n) => clamp(((n - lo) * 100) / (hi - lo));
    const valueAt = at(reading);
    const minAt = at(min);
    return {
      kind: 'range', start: Math.min(minAt, valueAt), end: Math.max(minAt, valueAt), minAt, maxAt: at(max), breach,
    };
  }
  if (max !== null) {
    return { kind: 'max', start: 0, end: max > 0 ? clamp((reading * 100) / max) : (breach ? 100 : 0), breach };
  }
  return { kind: 'min', start: 0, end: min > 0 ? clamp((reading * 100) / min) : (breach ? 0 : 100), breach };
}
