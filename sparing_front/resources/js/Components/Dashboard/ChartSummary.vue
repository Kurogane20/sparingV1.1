<script setup>
import { computed } from 'vue';

const props = defineProps({
  field: { type: String, default: '' },
  summary: { type: Object, default: () => ({}) },
  label: { type: String, default: '' },
  unit: { type: String, default: '' },
  decimals: { type: Number, default: 2 },
});

const safeDecimals = computed(() => Number.isInteger(props.decimals) && props.decimals >= 0 && props.decimals <= 6 ? props.decimals : 2);
const valueUnit = computed(() => props.unit ? ` ${props.unit}` : '');
const formatValue = (value) => typeof value === 'number' && Number.isFinite(value)
  ? `${value.toFixed(safeDecimals.value)}${valueUnit.value}`
  : '—';

const fallbackStatus = {
  no_flow: { label: 'Aliran Terhenti', reason: 'Debit berada pada kondisi tanpa aliran.', severity: 'warning', icon: '■' },
  no_data: { label: 'Tidak Ada Data', reason: 'Belum ada pembacaan yang dapat digunakan.', severity: 'warning', icon: '○' },
  sensor_error: { label: 'Kesalahan Sensor', reason: 'Sensor membutuhkan pemeriksaan.', severity: 'critical', icon: '▲' },
  critical: { label: 'Kritis', reason: 'Nilai melewati batas bahaya.', severity: 'critical', icon: '▲' },
  warning: { label: 'Peringatan', reason: 'Nilai memerlukan perhatian.', severity: 'warning', icon: '◆' },
  normal: { label: 'Normal', reason: 'Nilai berada dalam rentang yang diharapkan.', severity: 'normal', icon: '●' },
};

// The API often sends a machine code as status_reason (e.g. explicit_sensor_error);
// operators should read a sentence, never the raw identifier.
const REASON_TEXT = {
  explicit_sensor_error: 'Logger melaporkan sensor error.',
  stale_measurement: 'Pembacaan terakhir sudah lama.',
  no_finite_measurement: 'Belum ada pembacaan yang valid.',
  quality_check_required: 'Perlu pemeriksaan kualitas data.',
  no_flow_active: 'Debit berada pada kondisi tanpa aliran.',
  low_flow_detected: 'Debit rendah terdeteksi.',
  danger_threshold_violated: 'Nilai melewati batas bahaya.',
  warning_threshold_violated: 'Nilai mendekati batas.',
  within_configured_limits: 'Nilai dalam batas yang diatur.',
};
const REASON_CODE = /^[a-z0-9_]+$/;

function reasonText(raw, fallback) {
  if (typeof raw !== 'string' || !raw.trim()) return fallback;
  const reason = raw.trim();
  if (REASON_TEXT[reason]) return REASON_TEXT[reason];
  return REASON_CODE.test(reason) ? fallback : reason;
}

// "no_data" because the newest reading is too old, while a value is still shown.
const isStaleReading = computed(() => props.summary?.status === 'no_data'
  && props.summary?.status_reason === 'stale_measurement'
  && typeof props.summary?.current === 'number' && Number.isFinite(props.summary.current));

const status = computed(() => {
  const fallback = fallbackStatus[props.summary?.status] ?? fallbackStatus.no_data;
  const label = typeof props.summary?.status_label === 'string' && props.summary.status_label.trim() ? props.summary.status_label : fallback.label;
  return {
    label: isStaleReading.value ? 'Data Tidak Terbaru' : label,
    reason: reasonText(props.summary?.status_reason, fallback.reason),
    severity: typeof props.summary?.status_severity === 'string' && props.summary.status_severity.trim() ? props.summary.status_severity : fallback.severity,
    icon: fallback.icon,
  };
});

const availability = computed(() => typeof props.summary?.availability_pct === 'number' && Number.isFinite(props.summary.availability_pct)
  ? `${props.summary.availability_pct}%` : null);
const flowState = computed(() => ({
  flowing: 'Aliran normal', low_flow: 'Aliran rendah', no_flow: 'Aliran terhenti',
  no_data: 'Data aliran tidak tersedia', sensor_error: 'Sensor aliran bermasalah',
})[props.summary?.flow_state] ?? null);
const severityClass = computed(() => ({ critical: 'text-red-800 bg-red-50 border-red-200', warning: 'text-amber-900 bg-amber-50 border-amber-200', normal: 'text-emerald-800 bg-emerald-50 border-emerald-200' })[status.value.severity] ?? 'text-slate-700 bg-slate-50 border-slate-200');
</script>

<template>
  <section class="rounded-md border border-slate-200 bg-white p-3" :aria-label="`Ringkasan ${label || field}`">
    <div class="flex items-start justify-between gap-3">
      <div>
        <p class="text-xs font-semibold uppercase tracking-wide text-slate-500">{{ label || field }}</p>
        <p class="mt-1 font-mono text-2xl font-bold text-[#12333B]">{{ formatValue(summary?.current) }}</p>
        <p class="text-xs text-slate-500">Saat ini</p>
      </div>
      <div class="max-w-[60%] text-right">
        <span class="inline-flex items-center gap-1 rounded border px-2 py-1 text-xs font-semibold" :class="severityClass" :aria-label="`Status: ${status.label}`">
          <span aria-hidden="true">{{ status.icon }}</span>{{ status.label }}
        </span>
        <p class="mt-1 text-xs text-slate-600">{{ status.reason }}</p>
        <p v-if="flowState" class="mt-1 text-xs font-semibold text-slate-700"><span aria-hidden="true">■</span> {{ flowState }}</p>
      </div>
    </div>
    <dl class="mt-3 grid grid-cols-3 gap-2 border-t border-slate-100 pt-3 text-xs">
      <div><dt class="text-slate-500">Rata-rata</dt><dd class="mt-0.5 font-mono font-semibold text-slate-700">{{ formatValue(summary?.avg) }}</dd></div>
      <div><dt class="text-slate-500">Minimum</dt><dd class="mt-0.5 font-mono font-semibold text-slate-700">{{ formatValue(summary?.min) }}</dd></div>
      <div><dt class="text-slate-500">Maksimum</dt><dd class="mt-0.5 font-mono font-semibold text-slate-700">{{ formatValue(summary?.max) }}</dd></div>
    </dl>
    <p v-if="availability !== null" class="mt-3 border-t border-slate-100 pt-2 text-xs text-slate-600">Ketersediaan {{ availability }}</p>
  </section>
</template>
