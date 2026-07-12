/**
 * Parse a datetime value as UTC. Naive strings (no TZ suffix) from the API
 * are stored in UTC but lack a 'Z', so we append it before parsing.
 * @param {string|Date} date
 * @returns {Date}
 */
export function parseUTC(date) {
  if (!date) return new Date(NaN);
  if (date instanceof Date) return date;
  const s = String(date);
  if (!s.endsWith('Z') && !/[+-]\d{2}:\d{2}$/.test(s)) {
    return new Date(s + 'Z');
  }
  return new Date(s);
}

/**
 * Format date to Indonesian locale in the given IANA timezone.
 * @param {string|Date} date
 * @param {boolean} includeTime
 * @param {string} tz  IANA timezone string, e.g. 'Asia/Jakarta'
 * @returns {string}
 */
export function formatDate(date, includeTime = false, tz = 'Asia/Jakarta') {
  if (!date) return '-';
  const d = parseUTC(date);
  if (isNaN(d)) return '-';
  try {
    const options = {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      timeZone: tz,
    };
    if (includeTime) {
      options.hour = '2-digit';
      options.minute = '2-digit';
    }
    return d.toLocaleDateString('id-ID', options);
  } catch {
    return d.toLocaleDateString('id-ID', { year: 'numeric', month: 'short', day: 'numeric', timeZone: 'Asia/Jakarta' });
  }
}

/**
 * Format time only (HH:mm:ss) in the given IANA timezone.
 * @param {string|Date} date
 * @param {string} tz  IANA timezone string
 * @returns {string}
 */
export function formatTime(date, tz = 'Asia/Jakarta') {
  if (!date) return '-';
  const d = parseUTC(date);
  if (isNaN(d)) return '-';
  try {
    return d.toLocaleTimeString('id-ID', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      timeZone: tz,
    });
  } catch {
    return d.toLocaleTimeString('id-ID', { hour: '2-digit', minute: '2-digit', second: '2-digit', timeZone: 'Asia/Jakarta' });
  }
}

/**
 * Get relative time (e.g., "5 minutes ago")
 * @param {string|Date} date - Date to compare
 * @returns {string} Relative time string
 */
export function getRelativeTime(date) {
  if (!date) return '-';

  const d = parseUTC(date);
  if (isNaN(d)) return '-';
  const now = new Date();
  const diffMs = now - d;
  const diffMinutes = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);
  const diffDays = Math.floor(diffMs / 86400000);

  if (diffMinutes < 1) return 'Baru saja';
  if (diffMinutes < 60) return `${diffMinutes} menit lalu`;
  if (diffHours < 24) return `${diffHours} jam lalu`;
  return `${diffDays} hari lalu`;
}

/**
 * Get status badge class based on status
 * @param {string} status - Status value
 * @returns {string} CSS class name
 */
export function getStatusClass(status) {
  const statusMap = {
    active: 'bg-green-100 text-green-800',
    online: 'bg-green-100 text-green-800',
    offline: 'bg-red-100 text-red-800',
    inactive: 'bg-gray-100 text-gray-800',
    sleep: 'bg-yellow-100 text-yellow-800',
    warning: 'bg-yellow-100 text-yellow-800',
    error: 'bg-red-100 text-red-800',
  };

  return statusMap[status?.toLowerCase()] || 'bg-gray-100 text-gray-800';
}

/**
 * Get sensor status based on last seen time
 * @param {string|Date} lastSeen - Last seen timestamp
 * @param {number} thresholdMinutes - Minutes threshold for offline status
 * @returns {string} Status string
 */
export function getSensorStatus(lastSeen, onlineMin = 90, warningMin = 150) {
  if (!lastSeen) return 'unknown';
  // parseUTC: API timestamps are naive UTC; new Date() alone would misread them
  // as local (WIB), skewing the age by 7 hours. Thresholds match the backend
  // (hourly-burst ingest: online < 90 min, warning < 150 min).
  const d = parseUTC(lastSeen);
  if (isNaN(d)) return 'unknown';
  const diffMinutes = Math.floor((new Date() - d) / 60000);
  if (diffMinutes < onlineMin) return 'online';
  if (diffMinutes < warningMin) return 'warning';
  return 'offline';
}

/**
 * Format number with thousand separators
 * @param {number} value - Number to format
 * @param {number} decimals - Number of decimal places
 * @returns {string} Formatted number
 */
export function formatNumber(value, decimals = 2) {
  if (value == null || isNaN(value)) return '-';
  return Number(value).toLocaleString('id-ID', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
}

/**
 * Validate sensor value against expected range
 * @param {string} field - Sensor field name
 * @param {number} value - Value to validate
 * @returns {boolean} True if valid
 */
export function validateSensorValue(field, value) {
  const validations = {
    ph: { min: 0, max: 14 },
    tss: { min: 0, max: Infinity },
    debit: { min: 0, max: Infinity },
    temp: { min: -40, max: 80 },
    rh: { min: 0, max: 100 },
    wind_speed_kmh: { min: 0, max: Infinity },
    noise: { min: 0, max: Infinity },
    voltage: { min: 0, max: 1000 },
    current: { min: 0, max: 1000 },
  };

  const validation = validations[field];
  if (!validation) return true; // No validation rules

  return value >= validation.min && value <= validation.max;
}

/**
 * Get threshold status for sensor value
 * @param {string} field - Sensor field name
 * @param {number} value - Current value
 * @returns {string} Status: 'normal', 'warning', 'danger'
 */
export function getThresholdStatus(field, value) {
  // Baku mutu: Permen LH No. 5/2014 & ISPU
  // Array = [min, max] range; number = upper limit only
  const thresholds = {
    ph:    { warning: [6.5, 8.5], danger: [6.0, 9.0] },
    tss:   { warning: 150,        danger: 200 },
    nh3n:  { warning: 7,          danger: 10 },
    cod:   { warning: 200,        danger: 300 },
    noise: { warning: 60,         danger: 70 },
    temp:  { warning: 30,         danger: 35 },
    pm25:  { warning: 35,         danger: 65 },
    pm10:  { warning: 100,        danger: 150 },
    so2:   { warning: 600,        danger: 900 },
    no2:   { warning: 150,        danger: 200 },
    co:    { warning: 5000,       danger: 10000 },
  };

  const threshold = thresholds[field];
  if (!threshold) return 'normal';

  if (Array.isArray(threshold.danger)) {
    if (value < threshold.danger[0] || value > threshold.danger[1]) return 'danger';
  } else if (value > threshold.danger) {
    return 'danger';
  }

  if (Array.isArray(threshold.warning)) {
    if (value < threshold.warning[0] || value > threshold.warning[1]) return 'warning';
  } else if (value > threshold.warning) {
    return 'warning';
  }

  return 'normal';
}

/**
 * Get unit for sensor field
 * @param {string} field - Sensor field name
 * @returns {string} Unit string
 */
export function getSensorUnit(field) {
  const units = {
    ph: 'pH',
    tss: 'mg/L',
    debit: 'L/min',
    nh3n: 'mg/L',
    cod: 'mg/L',
    temp: '°C',
    rh: '%',
    wind_speed_kmh: 'km/h',
    wind_deg: '°',
    noise: 'dB',
    co: 'ppm',
    so2: 'ppm',
    no2: 'ppm',
    o3: 'ppm',
    pm25: 'µg/m³',
    pm10: 'µg/m³',
    tvoc: 'ppb',
    voltage: 'V',
    current: 'A',
  };

  return units[field] || '';
}

/**
 * Get human-readable sensor name
 * @param {string} field - Sensor field name
 * @returns {string} Human-readable name
 */
export function getSensorName(field) {
  const names = {
    ph: 'pH',
    tss: 'TSS',
    debit: 'Debit',
    nh3n: 'NH3-N',
    cod: 'COD',
    temp: 'Temperatur',
    rh: 'Kelembapan',
    wind_speed_kmh: 'Kecepatan Angin',
    wind_deg: 'Arah Angin',
    noise: 'Kebisingan',
    co: 'Karbon Monoksida',
    so2: 'Sulfur Dioksida',
    no2: 'Nitrogen Dioksida',
    o3: 'Ozon',
    pm25: 'PM2.5',
    pm10: 'PM10',
    tvoc: 'TVOC',
    voltage: 'Tegangan',
    current: 'Arus',
  };

  return names[field] || field.toUpperCase();
}

/**
 * Debounce function for search inputs
 * @param {Function} fn - Function to debounce
 * @param {number} delay - Delay in milliseconds
 * @returns {Function} Debounced function
 */
export function debounce(fn, delay = 300) {
  let timeoutId;
  return function (...args) {
    clearTimeout(timeoutId);
    timeoutId = setTimeout(() => fn.apply(this, args), delay);
  };
}

/**
 * Download data as CSV file
 * @param {Array} data - Array of objects to export
 * @param {string} filename - Output filename
 */
export function downloadCSV(data, filename = 'export.csv') {
  if (!data || data.length === 0) return;

  const headers = Object.keys(data[0]);
  const csvContent = [
    headers.join(','),
    ...data.map(row => headers.map(header => {
      const value = row[header];
      return typeof value === 'string' && value.includes(',')
        ? `"${value}"`
        : value;
    }).join(',')),
  ].join('\n');

  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
  const link = document.createElement('a');
  link.href = URL.createObjectURL(blob);
  link.download = filename;
  link.click();
}
