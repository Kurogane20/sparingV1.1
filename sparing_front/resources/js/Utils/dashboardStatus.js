// Status logic for the "Bentang air" dashboard: what the status band says,
// how the month went, and where a reading sits against its limit. Pure
// functions, so every state is testable without a browser.

export const STALE_AFTER_MS = 2 * 60 * 60 * 1000;

export const FIELD_LABELS = Object.freeze({
  ph: 'pH',
  tss: 'TSS',
  cod: 'COD',
  nh3n: 'NH₃-N',
  debit: 'Debit',
  temp: 'Suhu',
});

const finite = (value) => (typeof value === 'number' && Number.isFinite(value) ? value : null);

function activeRules(rules) {
  const list = Array.isArray(rules) ? rules : Object.values(rules ?? {});
  return list.filter((rule) => rule && rule.is_active !== false
    && (finite(rule.danger_min) !== null || finite(rule.danger_max) !== null));
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
  return new Intl.DateTimeFormat('en-CA', {
    timeZone, year: 'numeric', month: '2-digit', day: '2-digit',
  }).format(at);
}

/**
 * The status band's state; the first match wins:
 *   no_rules → stale → breach_now → breached_today → compliant
 * rules: alert rules (array or field → rule map); latest: the /data/last row;
 * todayStatus: today's status from /stats/compliance-daily;
 * activeAlerts: /alerts?status=active for the site.
 */
export function bandState({
  rules, latest, todayStatus = null, activeAlerts = [], now = Date.now(), staleAfterMs = STALE_AFTER_MS,
} = {}) {
  const active = activeRules(rules);
  if (!active.length) return { state: 'no_rules' };

  const breachedToday = todayStatus === 'violation';
  const lastTs = latest?.ts ? Date.parse(latest.ts) : NaN;
  if (!Number.isFinite(lastTs)) return { state: 'stale', lastTs: null, breachedToday };
  if (now - lastTs > staleAfterMs) {
    return { state: 'stale', lastTs: new Date(lastTs).toISOString(), breachedToday };
  }

  // A quality-flagged or operational-status row (calibration, stopped) is not
  // a measurement to judge against the limit.
  const measurable = !latest.quality_flag && (latest.op_status === null || latest.op_status === undefined);
  const breaches = measurable
    ? active.filter((rule) => isOutsideLimit(latest[rule.field], rule)).map((rule) => ({
      field: rule.field,
      value: latest[rule.field],
      min: finite(rule.danger_min),
      max: finite(rule.danger_max),
    }))
    : [];
  if (breaches.length) {
    const fields = breaches.map((breach) => breach.field);
    const alert = (Array.isArray(activeAlerts) ? activeAlerts : [])
      .filter((item) => fields.includes(item?.field) && (item.category ?? 'compliance') === 'compliance')
      .sort((left, right) => Date.parse(left.triggered_at) - Date.parse(right.triggered_at))[0] ?? null;
    return {
      state: 'breach_now',
      fields,
      breaches,
      title: `${joinLabels(fields)} melewati baku mutu`,
      since: alert?.triggered_at ?? null,
      alertId: alert?.id ?? null,
    };
  }
  if (breachedToday) return { state: 'breached_today' };
  return { state: 'compliant', nearLimit: todayStatus === 'warning' };
}

/**
 * The month's compliance from /stats/compliance-daily days. A day counts as
 * compliant when it is `ok` or `warning` (a warning is not a violation); days
 * without measurements and days after `today` are left out.
 */
export function monthCompliance(days, today) {
  const cells = (Array.isArray(days) ? days : []).map(({ date, status }) => {
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
      kind: 'range',
      start: Math.min(minAt, valueAt),
      end: Math.max(minAt, valueAt),
      minAt,
      maxAt: at(max),
      breach: reading < min || reading > max,
    };
  }
  if (max !== null) {
    return { kind: 'max', start: 0, end: max > 0 ? clamp((reading * 100) / max) : 100, breach: reading > max };
  }
  return { kind: 'min', start: 0, end: min > 0 ? clamp((reading * 100) / min) : 100, breach: reading < min };
}
