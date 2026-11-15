<script setup>
import { computed } from 'vue';
import DayStrip from '@/Components/Loggers/DayStrip.vue';
import LoggerEventTimeline from '@/Components/LoggerEventTimeline.vue';
import { KIND_LABELS, STATE_META, dayStrip, durationText, recoveryText } from '@/Utils/loggerDiagnosis.js';
import { formatDashboardTimestamp } from '@/Utils/dashboardTimeseries.js';
import { getRelativeTime, parseUTC } from '@/Utils/helpers';

// One logger on the Logger page. The server already cut the row per role:
// `action`, `device` and `tech` are simply absent for those who may not see them.
const props = defineProps({
  row: { type: Object, required: true },        // /logger/diagnosis row
  incidents: { type: Array, default: () => [] }, // /logger/incidents of this site
  expanded: { type: Boolean, default: false },
  events: { type: Array, default: () => [] },    // raw events, admins only
  eventsLoading: { type: Boolean, default: false },
  now: { type: Number, default: () => Date.now() },
});
defineEmits(['toggle']);

const tz = computed(() => props.row.timezone || 'Asia/Jakarta');
const meta = computed(() => STATE_META[props.row.state] ?? STATE_META.unknown);
const primary = computed(() => props.row.findings?.[0] ?? null);
const others = computed(() => (props.row.findings ?? []).slice(1));
const strip = computed(() => dayStrip(props.incidents, { timeZone: tz.value, now: props.now }));
const panelId = computed(() => `logger-detail-${String(props.row.site_uid).replace(/[^A-Za-z0-9_-]/g, '_')}`);

const when = (ts) => formatDashboardTimestamp(parseUTC(ts), tz.value);
const sinceText = computed(() => {
  if (props.row.state === 'normal') {
    return props.row.last_heartbeat_at ? `melapor ${getRelativeTime(props.row.last_heartbeat_at)}` : '';
  }
  return props.row.since ? `sejak ${when(props.row.since)}` : '';
});

const history = computed(() => props.incidents.map((incident) => ({
  id: incident.id,
  label: KIND_LABELS[incident.kind] ?? incident.kind,
  range: `${when(incident.started_at)} – ${incident.ended_at ? when(incident.ended_at) : 'sekarang'}`,
  duration: incident.duration_min == null ? '—' : durationText(incident.duration_min),
  text: incident.cause_detail || (incident.ended_at ? 'Penyebab sedang disimpulkan.' : 'Masih berlangsung.'),
  lost: recoveryText(incident),
})));

const SENSOR_LABELS = { ph: 'pH', tss: 'TSS', debit: 'Debit', cod: 'COD', nh3n: 'NH₃-N' };
const word = (value, yes, no) => (value === true ? yes : value === false ? no : '—');
const device = computed(() => {
  const d = props.row.device;
  if (!d) return null;
  const sensors = Object.entries(d.sensors ?? {})
    .filter(([, ok]) => ok !== null && ok !== undefined)
    .map(([key, ok]) => `${SENSOR_LABELS[key] ?? key} ${ok ? 'OK' : 'gagal'}`)
    .join(' · ');
  return [
    ['Heartbeat terakhir', d.last_heartbeat_at ? when(d.last_heartbeat_at) : '—'],
    ['Internet', word(d.internet_ok, 'tersambung', 'putus')],
    ['Antrean belum terkirim', d.buffer_depth ?? '—'],
    ['Kirim ke MM', word(d.last_send_ok_mm, 'berhasil', 'gagal')],
    ['Kirim ke KLHK', word(d.last_send_ok_klhk, 'berhasil', 'gagal')],
    ['Sensor', sensors || '—'],
  ];
});

const pct = (value) => (typeof value === 'number' ? `${Math.round(value)}%` : '—');
const tech = computed(() => {
  const t = props.row.tech;
  if (!t) return null;
  return {
    rows: [
      ['uid', t.uid || '—'],
      ['Versi', t.logger_version || '—'],
      ['Aplikasi berjalan', typeof t.uptime_s === 'number' ? durationText(t.uptime_s / 60) : '—'],
      ['CPU · RAM · Disk', `${pct(t.cpu_pct)} · ${pct(t.mem_pct)} · ${pct(t.disk_pct)}`],
      ['Suhu', typeof t.cpu_temp === 'number' ? `${Math.round(t.cpu_temp)} °C` : '—'],
    ],
    rejections: (t.rejections ?? []).map((r) => `${r.source} · ${r.reason} · ${r.count}× · terakhir ${when(r.last_at)}${r.last_detail ? ` · ${r.last_detail}` : ''}`),
    notes: (props.row.findings ?? []).filter((f) => f.tech).map((f) => f.tech),
  };
});
</script>

<template>
  <li class="border-b border-line last:border-b-0">
    <div class="flex flex-col gap-3 px-4 py-4 md:flex-row md:items-start md:gap-6 md:px-6">
      <div class="min-w-0 flex-1">
        <div class="flex flex-wrap items-center gap-x-2 gap-y-1">
          <span class="h-2.5 w-2.5 shrink-0 rounded-full" :class="meta.dot" aria-hidden="true"></span>
          <h3 class="text-[15px] font-bold text-ink">{{ row.site_name }}</h3>
          <span class="text-xs font-semibold uppercase tracking-wide" :class="meta.text">{{ meta.label }}</span>
          <span v-if="sinceText" class="text-xs text-muted">· {{ sinceText }}</span>
        </div>
        <p class="mt-1 text-[13.5px] text-ink">{{ row.headline }}</p>
        <p v-if="primary?.action" class="mt-1 text-[13px] text-muted">
          <span class="font-semibold text-ink">Langkah:</span> {{ primary.action }}
        </p>
      </div>
      <div class="flex shrink-0 items-center gap-3 md:w-[24rem]">
        <DayStrip class="flex-1" :cells="strip" :label="`Gangguan 30 hari terakhir — ${row.site_name}`" />
        <button
          type="button"
          class="min-h-[44px] shrink-0 rounded-md px-3 py-1 text-xs md:min-h-0 md:px-2 font-semibold text-primary hover:bg-[#EEF4F4] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary"
          :aria-expanded="expanded ? 'true' : 'false'"
          :aria-controls="panelId"
          @click="$emit('toggle')"
        >
          {{ expanded ? 'Tutup' : 'Rincian' }}<span class="sr-only"> {{ row.site_name }}</span>
        </button>
      </div>
    </div>

    <div v-if="expanded" :id="panelId" class="space-y-5 border-t border-line bg-[#F3F7F7] px-4 py-4 text-[13px] md:px-6">
      <section v-if="others.length">
        <h4 class="mb-1 text-xs font-semibold uppercase tracking-wide text-muted">Temuan lain</h4>
        <ul class="space-y-1.5">
          <li v-for="finding in others" :key="finding.code + finding.title" class="text-ink">
            {{ finding.title }}
            <span v-if="finding.action" class="block text-muted">Langkah: {{ finding.action }}</span>
          </li>
        </ul>
      </section>

      <section>
        <h4 class="mb-1 text-xs font-semibold uppercase tracking-wide text-muted">Riwayat gangguan (30 hari)</h4>
        <p v-if="!history.length" class="text-muted">Tidak ada gangguan tercatat.</p>
        <ul v-else class="divide-y divide-line">
          <li v-for="item in history" :key="item.id" class="py-2 first:pt-0">
            <div class="flex flex-wrap items-baseline justify-between gap-x-3">
              <span class="font-semibold text-ink">{{ item.label }}</span>
              <span class="text-xs tabular-nums text-muted">{{ item.range }} · {{ item.duration }}</span>
            </div>
            <p class="text-ink">{{ item.text }}<template v-if="item.lost"> {{ item.lost }}</template></p>
          </li>
        </ul>
      </section>

      <section v-if="device">
        <h4 class="mb-1 text-xs font-semibold uppercase tracking-wide text-muted">Kondisi perangkat</h4>
        <dl class="grid grid-cols-1 gap-x-8 sm:grid-cols-2">
          <div v-for="[label, value] in device" :key="label" class="flex justify-between gap-3 py-1">
            <dt class="text-muted">{{ label }}</dt>
            <dd class="text-right font-semibold text-ink">{{ value }}</dd>
          </div>
        </dl>
      </section>

      <section v-if="tech">
        <h4 class="mb-1 text-xs font-semibold uppercase tracking-wide text-muted">Teknis</h4>
        <dl class="grid grid-cols-1 gap-x-8 sm:grid-cols-2">
          <div v-for="[label, value] in tech.rows" :key="label" class="flex justify-between gap-3 py-1">
            <dt class="text-muted">{{ label }}</dt>
            <dd class="min-w-0 break-all text-right font-mono text-xs text-ink">{{ value }}</dd>
          </div>
        </dl>
        <ul v-if="tech.notes.length || tech.rejections.length" class="mt-2 space-y-1 break-all font-mono text-xs text-muted">
          <li v-for="note in tech.notes" :key="note">{{ note }}</li>
          <li v-for="line in tech.rejections" :key="line">{{ line }}</li>
        </ul>
        <div class="mt-3">
          <LoggerEventTimeline :events="events" :loading="eventsLoading" />
        </div>
      </section>
    </div>
  </li>
</template>
