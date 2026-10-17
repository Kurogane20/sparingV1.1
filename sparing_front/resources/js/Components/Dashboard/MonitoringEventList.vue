<script setup>
import { computed, ref } from 'vue';
import { formatDashboardTimestamp, formatMeasurement } from '@/Utils/dashboardTimeseries.js';

const props = defineProps({
  events: { type: Array, default: () => [] },
  eventTotal: { type: Number, default: 0 },
  timezone: { type: String, default: 'Asia/Jakarta' },
});
const emit = defineEmits(['focus-event']);

const EVENT_PREVIEW_LIMIT = 6;
const timeOf = (event) => {
  const value = Date.parse(event?.ts);
  return Number.isFinite(value) ? value : -Infinity;
};
// The API sends events oldest-first; operators want the newest on top.
const validEvents = computed(() => (Array.isArray(props.events) ? props.events : [])
  .filter((event) => event !== null && typeof event === 'object' && !Array.isArray(event))
  .map((event, index) => ({ event, index }))
  .sort((a, b) => (timeOf(b.event) - timeOf(a.event)) || (a.index - b.index))
  .map(({ event }) => event));
const expanded = ref(false);
const canToggle = computed(() => validEvents.value.length > EVENT_PREVIEW_LIMIT);
const visibleEvents = computed(() => (expanded.value ? validEvents.value : validEvents.value.slice(0, EVENT_PREVIEW_LIMIT)));
const total = computed(() => Number.isFinite(props.eventTotal) ? props.eventTotal : validEvents.value.length);
const hasUnrenderableDetails = computed(() => validEvents.value.length === 0 && total.value > 0);
const severityText = { critical: 'Kritis', warning: 'Peringatan', info: 'Informasi', normal: 'Normal' };
const severityShape = { critical: '▲', warning: '◆', info: '●', normal: '●' };

const FIELD_LABELS = { ph: 'pH', tss: 'TSS', debit: 'Debit', cod: 'COD', nh3n: 'NH3-N', temp: 'Temperatur' };
function fieldLabel(field) { return FIELD_LABELS[String(field).toLowerCase()] ?? field; }
function textValue(value) { return formatMeasurement(value); }
function contextItems(context) {
  if (!context || typeof context !== 'object') return [];
  const items = [];
  const add = (label, value) => { const text = textValue(value); if (text !== null) items.push(`${label}: ${text}`); };
  add('Nilai', context.current ?? context.value);
  // Below a minute it is delivery latency (older API versions), not an interval.
  if (Number.isFinite(context.interval_seconds) && context.interval_seconds >= 60) {
    const minutes = context.interval_seconds / 60;
    items.push(`Interval: ${formatMeasurement(Math.round(minutes * 10) / 10)} menit`);
  }
  if (context.debit && typeof context.debit === 'object') add('Debit', context.debit.value);
  if (context.tss && typeof context.tss === 'object') {
    add('TSS', context.tss.current);
    add('Perubahan TSS', context.tss.delta);
  }
  return [...new Set(items)];
}
function focusEvent(event) { emit('focus-event', event); }
</script>

<template>
  <section class="sensor-card min-w-0 max-w-full p-0 motion-reduce:hover:transform-none motion-reduce:transition-none" aria-label="Event pemantauan">
    <div class="flex flex-wrap items-center justify-between gap-2 border-b border-slate-200 px-4 py-3">
      <h3 class="card-title">Event pemantauan</h3>
      <p v-if="total > visibleEvents.length" class="text-xs text-slate-600">Menampilkan {{ visibleEvents.length }} dari {{ total }} event</p>
    </div>
    <p v-if="!visibleEvents.length" class="px-4 py-6 text-center text-sm text-slate-600">{{ hasUnrenderableDetails ? 'Event terdeteksi, tetapi detailnya tidak dapat ditampilkan.' : 'Belum ada event pemantauan pada periode ini.' }}</p>
    <ul v-else class="divide-y divide-slate-100">
      <li v-for="event in visibleEvents" :key="event.id ?? `${event.ts}-${event.type}`">
        <button type="button" class="w-full px-4 py-3 text-left transition-colors hover:bg-teal-50 focus-visible:bg-teal-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-[-2px] focus-visible:outline-teal-700 motion-reduce:transition-none" @click="focusEvent(event)">
          <div class="flex items-start justify-between gap-3">
            <div class="min-w-0">
              <p class="font-semibold text-slate-800">{{ event.label || event.type || 'Event pemantauan' }}</p>
              <p class="mt-0.5 text-xs text-slate-500">{{ formatDashboardTimestamp(event.ts, timezone) }}<span v-if="event.end_ts"> – {{ formatDashboardTimestamp(event.end_ts, timezone, true) }}</span></p>
            </div>
            <span class="inline-flex shrink-0 items-center gap-1 rounded border border-slate-200 bg-slate-50 px-2 py-1 text-xs font-semibold text-slate-700" :aria-label="`Keparahan: ${severityText[event.severity] ?? 'Informasi'}`"><span aria-hidden="true">{{ severityShape[event.severity] ?? '●' }}</span>{{ severityText[event.severity] ?? 'Informasi' }}</span>
          </div>
          <p v-if="event.field || event.direction" class="mt-1 text-xs text-slate-600"><span v-if="event.field">Parameter: {{ fieldLabel(event.field) }}</span><span v-if="event.field && event.direction"> · </span><span v-if="event.direction">Arah: {{ event.direction }}</span></p>
          <p v-if="contextItems(event.context).length" class="mt-1 text-xs text-slate-600">{{ contextItems(event.context).join(' · ') }}</p>
        </button>
      </li>
    </ul>
    <div v-if="canToggle" class="border-t border-slate-100 px-4 py-2">
      <button type="button" class="text-xs font-semibold text-teal-700 hover:underline focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-teal-700" :aria-expanded="expanded ? 'true' : 'false'" @click="expanded = !expanded">
        {{ expanded ? 'Tampilkan lebih sedikit' : `Tampilkan semua (${validEvents.length})` }}
      </button>
    </div>
  </section>
</template>
