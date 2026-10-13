import { getThresholdStatus, parseUTC } from './helpers.js';

// Loggers send an hourly burst, so a healthy site's newest reading is at most
// ~1h old. Anything older than this is shown as "no current data".
export const SITE_STALE_MS = 3 * 60 * 60 * 1000;

const STATUS_ORDER = ['danger', 'warning', 'offline', 'nodata', 'normal'];

export function rowStatusFromLatest(latest) {
  if (!latest) return 'nodata';
  const statuses = ['ph', 'tss', 'cod', 'nh3n']
    .filter((field) => latest[field] != null)
    .map((field) => getThresholdStatus(field, latest[field]));
  if (!statuses.length) return 'nodata';
  if (statuses.includes('danger')) return 'danger';
  if (statuses.includes('warning')) return 'warning';
  return 'normal';
}

export function siteChipStatus({ latest = null, loggerState = null, now = Date.now() } = {}) {
  if (loggerState === 'down') return 'offline';
  const ts = latest?.ts ? parseUTC(latest.ts).getTime() : NaN;
  if (!Number.isFinite(ts) || now - ts > SITE_STALE_MS) return 'nodata';
  return rowStatusFromLatest(latest);
}

export function buildSiteChips(rows, loggerStates = {}, now = Date.now()) {
  return rows
    .map(({ site, latest }) => ({
      uid: site.uid,
      name: site.name ?? site.uid,
      status: siteChipStatus({ latest, loggerState: loggerStates[site.uid] ?? null, now }),
    }))
    .sort((a, b) => STATUS_ORDER.indexOf(a.status) - STATUS_ORDER.indexOf(b.status)
      || a.name.localeCompare(b.name, 'id'));
}
