<script setup>
import { computed } from 'vue';
import { formatDashboardTimestamp } from '@/Utils/dashboardTimeseries.js';

const props = defineProps({
  events: { type: Array, default: () => [] },
  eventTotal: { type: Number, default: 0 },
  timezone: { type: String, default: 'Asia/Jakarta' },
});
const emit = defineEmits(['focus-event']);

const visibleEvents = computed(() => Array.isArray(props.events) ? props.events : []);
const total = computed(() => Number.isFinite(props.eventTotal) ? props.eventTotal : visibleEvents.value.length);
const severityText = { critical: 'Kritis', warning: 'Peringatan', info: 'Informasi', normal: 'Normal' };
const severityShape = { critical: '▲', warning: '◆', info: '●', normal: '●' };

function textValue(value) { return typeof value === 'number' && Number.isFinite(value) ? String(value) : null; }
function contextItems(context) {
  if (!context || typeof context !== 'object') return [];
  const items = [];
  const add = (label, value) => { const text = textValue(value); if (text !== null) items.push(`${label}: ${text}`); };
  add('Nilai', context.current ?? context.value);
  if (Number.isFinite(context.interval_seconds)) {
    const minutes = context.interval_seconds / 60;
    items.push(`Interval: ${Number.isInteger(minutes) ? minutes : minutes.toFixed(1)} menit`);
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
  <section class="sensor-card p-0" aria-labelledby="monitoring-events-title">
    <div class="flex flex-wrap items-center justify-between gap-2 border-b border-slate-200 px-4 py-3">
      <h3 id="monitoring-events-title" class="card-title">Event pemantauan</h3>
      <p v-if="total > visibleEvents.length" class="text-xs text-slate-600">Menampilkan {{ visibleEvents.length }} dari {{ total }} event</p>
    </div>
    <p v-if="!visibleEvents.length" class="px-4 py-6 text-center text-sm text-slate-600">Belum ada event pemantauan pada periode ini.</p>
    <ul v-else class="divide-y divide-slate-100">
      <li v-for="event in visibleEvents" :key="event.id ?? `${event.ts}-${event.type}`">
        <button type="button" class="w-full px-4 py-3 text-left transition-colors hover:bg-teal-50 focus-visible:bg-teal-50" @click="focusEvent(event)">
          <div class="flex items-start justify-between gap-3">
            <div class="min-w-0">
              <p class="font-semibold text-slate-800">{{ event.label || event.type || 'Event pemantauan' }}</p>
              <p class="mt-0.5 text-xs text-slate-500">{{ formatDashboardTimestamp(event.ts, timezone) }}<span v-if="event.end_ts"> – {{ formatDashboardTimestamp(event.end_ts, timezone, true) }}</span></p>
            </div>
            <span class="inline-flex shrink-0 items-center gap-1 rounded border border-slate-200 bg-slate-50 px-2 py-1 text-xs font-semibold text-slate-700" :aria-label="`Keparahan: ${severityText[event.severity] ?? 'Informasi'}`"><span aria-hidden="true">{{ severityShape[event.severity] ?? '●' }}</span>{{ severityText[event.severity] ?? 'Informasi' }}</span>
          </div>
          <p v-if="event.field || event.direction" class="mt-1 text-xs text-slate-600"><span v-if="event.field">Parameter: {{ event.field }}</span><span v-if="event.field && event.direction"> · </span><span v-if="event.direction">Arah: {{ event.direction }}</span></p>
          <p v-if="contextItems(event.context).length" class="mt-1 text-xs text-slate-600">{{ contextItems(event.context).join(' · ') }}</p>
        </button>
      </li>
    </ul>
  </section>
</template>
