// Presentation helpers for the Logger page (logger-diagnosis spec, Bagian 4).
// The server decides the diagnosis and cuts it per role; these only format it.
import { parseUTC } from './helpers.js';

const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'Mei', 'Jun', 'Jul', 'Agu', 'Sep', 'Okt', 'Nov', 'Des'];
const DAY_MS = 86400000;

export const STATE_META = {
  down: { label: 'Mati', dot: 'bg-breach', text: 'text-breach' },
  problem: { label: 'Bermasalah', dot: 'bg-breach', text: 'text-breach' },
  attention: { label: 'Perhatian', dot: 'bg-[#C98A1B]', text: 'text-[#8A5A00]' },
  unknown: { label: 'Tidak diketahui', dot: 'bg-idle', text: 'text-muted' },
  normal: { label: 'Normal', dot: 'bg-ok', text: 'text-ok' },
};

const SUMMARY_WORDS = [
  ['normal', 'normal'], ['attention', 'perhatian'], ['problem', 'bermasalah'],
  ['down', 'mati'], ['unknown', 'tidak diketahui'],
];

export function summaryText(rows) {
  const counts = {};
  for (const row of rows ?? []) counts[row.state] = (counts[row.state] ?? 0) + 1;
  const parts = SUMMARY_WORDS.filter(([key]) => counts[key]).map(([key, word]) => `${counts[key]} ${word}`);
  return parts.length ? parts.join(' · ') : 'Belum ada logger';
}

// Incident kinds as the history list names them.
export const KIND_LABELS = {
  down: 'Logger mati',
  rejected: 'Data ditolak server',
  rejected_partial: 'Sebagian kiriman ditolak',
  no_telemetry: 'Telemetri tidak aktif',
  send_fail_mm: 'Kirim ke MM gagal',
  send_fail_klhk: 'Kirim ke KLHK gagal',
  unstable_power: 'Sering mati mendadak',
  device_disk: 'Penyimpanan hampir penuh',
  device_temp: 'Logger terlalu panas',
};

// Alarm fields of category "logger", for the Alarm page and the bell.
export const LOGGER_FIELD_LABELS = {
  logger_down: 'Logger tidak terjangkau',
  rejected: 'Data ditolak server',
  rejected_partial: 'Sebagian kiriman ditolak server',
  no_telemetry: 'Telemetri logger tidak aktif',
  send_fail_mm: 'Kirim ke server MM gagal',
  send_fail_klhk: 'Kirim ke KLHK gagal',
  unstable_power: 'Logger sering mati mendadak',
  device_disk: 'Penyimpanan logger hampir penuh',
  device_temp: 'Logger terlalu panas',
};
const SENSOR_NAMES = { ph: 'pH', tss: 'TSS', debit: 'Debit', cod: 'COD', nh3n: 'NH3-N' };

export function loggerAlertTitle(alert) {
  const field = alert?.field || '';
  if (LOGGER_FIELD_LABELS[field]) return LOGGER_FIELD_LABELS[field];
  if (field.startsWith('sensor_')) {
    const key = field.slice(7);
    return `Sensor ${SENSOR_NAMES[key] || key.toUpperCase()} gagal dibaca`;
  }
  return 'Kejadian logger';
}

export function durationText(minutes) {
  const total = Math.max(0, Math.round(Number(minutes) || 0));
  if (total < 1) return 'kurang dari 1 menit';
  const days = Math.floor(total / 1440);
  const hours = Math.floor((total % 1440) / 60);
  const mins = total % 60;
  if (days) return hours ? `${days} hari ${hours} jam` : `${days} hari`;
  if (hours) return mins ? `${hours} jam ${mins} menit` : `${hours} jam`;
  return `${mins} menit`;
}

// Readings lost by an ended `down` incident ("2 bacaan hilang"); the share that
// caught up is already in the server's cause sentence.
export function recoveryText(incident) {
  if (incident?.kind !== 'down' || !incident.ended_at || !incident.data_expected) return '';
  const missing = incident.data_expected - Math.min(incident.data_recovered ?? 0, incident.data_expected);
  return missing > 0 ? `${missing} bacaan hilang` : '';
}

// The site's UTC offset in ms. Indonesian zones have no DST, so one offset
// holds for the whole 30 days.
function zoneOffsetMs(timeZone, at) {
  try {
    const parts = new Intl.DateTimeFormat('en-US', {
      timeZone, hourCycle: 'h23', year: 'numeric', month: '2-digit', day: '2-digit',
      hour: '2-digit', minute: '2-digit', second: '2-digit',
    }).formatToParts(at);
    const get = (type) => Number(parts.find((part) => part.type === type)?.value);
    const wall = Date.UTC(get('year'), get('month') - 1, get('day'), get('hour'), get('minute'), get('second'));
    return wall - Math.floor(at.getTime() / 1000) * 1000;
  } catch {
    return 7 * 3600 * 1000; // WIB, like the backend's fallback
  }
}

function dayLabel(date) {
  const [, month, day] = date.split('-').map(Number);
  return `${day} ${MONTHS[month - 1]}`;
}

// One cell per local day (oldest first): minutes of `down` incidents that day.
export function dayStrip(incidents, { days = 30, timeZone = 'Asia/Jakarta', now = Date.now() } = {}) {
  const offset = zoneOffsetMs(timeZone, new Date(now));
  const todayStart = Math.floor((now + offset) / DAY_MS) * DAY_MS - offset; // local midnight, in UTC ms
  const spans = (incidents ?? [])
    .filter((incident) => incident?.kind === 'down')
    .map((incident) => [
      parseUTC(incident.started_at).getTime(),
      incident.ended_at ? parseUTC(incident.ended_at).getTime() : now,
    ])
    .filter(([start, end]) => Number.isFinite(start) && Number.isFinite(end) && end > start)
    // Overlapping incidents (a down reopened after a telemetry-only spell) count once.
    .sort((a, b) => a[0] - b[0])
    .reduce((merged, span) => {
      const last = merged[merged.length - 1];
      if (last && span[0] <= last[1]) last[1] = Math.max(last[1], span[1]);
      else merged.push([...span]);
      return merged;
    }, []);

  const cells = [];
  for (let back = days - 1; back >= 0; back -= 1) {
    const dayStart = todayStart - back * DAY_MS;
    const dayEnd = Math.min(dayStart + DAY_MS, now); // today counts only up to now
    let ms = 0;
    for (const [start, end] of spans) ms += Math.max(0, Math.min(end, dayEnd) - Math.max(start, dayStart));
    const minutes = Math.min(1440, Math.round(ms / 60000));
    const date = new Date(dayStart + offset).toISOString().slice(0, 10);
    const label = dayLabel(date);
    const whole = minutes * 60000 >= dayEnd - dayStart - 10 * 60000;
    const level = minutes === 0 ? 'none' : minutes < 60 ? 'short' : whole ? 'full' : 'long';
    cells.push({
      date, label, minutes, level,
      text: minutes ? `${label}: gangguan ${durationText(minutes)}` : `${label}: tanpa gangguan`,
    });
  }
  return cells;
}
