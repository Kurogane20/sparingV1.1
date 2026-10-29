<script setup>
import { computed } from 'vue';
import { FIELD_LABELS, localDateISO } from '@/Utils/dashboardStatus.js';
import { formatDashboardTimestamp } from '@/Utils/dashboardTimeseries.js';
import { parseUTC } from '@/Utils/helpers';

// Layer 3 of the dashboard sheet, rendered only for operators and admins:
// alarms awaiting follow-up, the logger and its delivery, sensor health. The
// device table and electrical chart come in through the default slot.
const props = defineProps({
  logger: { type: Object, default: null }, // /logger/status row for this site
  activeAlerts: { type: Array, default: () => [] },
  // Total active alarms from /alerts/count; the list may be capped.
  activeCount: { type: Number, default: null },
  receivedToday: { type: Number, default: null },
  timezone: { type: String, default: 'Asia/Jakarta' },
  // "Now" (ms): a heartbeat from an earlier day keeps its date.
  now: { type: Number, default: () => Date.now() },
});

const SENSOR_FIELDS = ['ph', 'tss', 'cod', 'nh3n', 'debit'];
const sensors = computed(() => SENSOR_FIELDS
  .filter((field) => typeof props.logger?.[`${field}_ok`] === 'boolean')
  .map((field) => ({ field, label: FIELD_LABELS[field], ok: props.logger[`${field}_ok`] })));
// Only 'alive' is alive, as on the Loggers page; an unknown state is not healthy.
const LOGGER_STATE = {
  alive: { text: 'hidup', cls: 'text-ok' },
  down: { text: 'mati', cls: 'text-breach' },
};
const loggerState = computed(() => LOGGER_STATE[props.logger?.state] ?? { text: 'tidak diketahui', cls: 'text-muted' });
const alarmCount = computed(() => (typeof props.activeCount === 'number' ? props.activeCount : props.activeAlerts.length));
const heartbeat = computed(() => {
  // parseUTC: the API may send a naive UTC timestamp, which new Date() would read as local time.
  const at = parseUTC(props.logger?.last_heartbeat_at);
  if (Number.isNaN(at.getTime())) return '—';
  const sameDay = localDateISO(props.timezone, at) === localDateISO(props.timezone, new Date(props.now));
  return formatDashboardTimestamp(at, props.timezone, sameDay);
});
const klhk = computed(() => {
  const value = props.logger?.last_send_ok_klhk;
  if (value === true) return { text: 'berhasil', cls: 'text-ok' };
  if (value === false) return { text: 'gagal', cls: 'text-breach' };
  return { text: '—', cls: 'text-muted' };
});
const count = (value) => (typeof value === 'number' ? value : '—');
</script>

<template>
  <section class="border-t border-line bg-[#F3F7F7] px-4 py-4 md:px-6" aria-label="Perangkat dan data">
    <h3 class="text-[15px] font-bold text-ink">Perangkat &amp; data</h3>
    <div class="mt-3 grid gap-4 lg:grid-cols-3 lg:gap-0 lg:divide-x lg:divide-[#DCE6E6]">
      <div class="lg:pr-5">
        <h4 class="mb-1 text-xs font-normal text-muted">Alarm</h4>
        <!-- Recording a follow-up moves an alarm from "active" to "acknowledged",
             so every active alarm is one nobody has followed up yet. -->
        <dl class="text-[13px] text-ink">
          <div class="flex justify-between gap-3 py-1">
            <dt>Belum ditindaklanjuti</dt>
            <dd class="font-semibold tabular-nums" :class="alarmCount ? 'text-breach' : 'text-ok'">{{ alarmCount }}</dd>
          </div>
        </dl>
        <router-link to="/alarms" class="mt-1 inline-block text-[13px] font-semibold text-primary hover:underline">Buka halaman alarm →</router-link>
      </div>

      <div class="lg:px-5">
        <h4 class="mb-1 text-xs font-normal text-muted">Logger &amp; kiriman</h4>
        <dl class="text-[13px] text-ink">
          <template v-if="logger">
            <div class="flex justify-between gap-3 py-1">
              <dt>Logger</dt>
              <dd class="text-right font-semibold" :class="loggerState.cls">{{ loggerState.text }} · {{ heartbeat }}</dd>
            </div>
            <div class="flex justify-between gap-3 py-1">
              <dt>Antrean belum terkirim</dt>
              <dd class="font-semibold tabular-nums">{{ count(logger.buffer_depth) }}</dd>
            </div>
            <div class="flex justify-between gap-3 py-1">
              <dt>Kirim ke KLHK</dt>
              <dd class="font-semibold" :class="klhk.cls">{{ klhk.text }}</dd>
            </div>
          </template>
          <div class="flex justify-between gap-3 py-1">
            <dt>Bacaan masuk hari ini</dt>
            <dd class="font-semibold tabular-nums">{{ count(receivedToday) }}</dd>
          </div>
        </dl>
        <p v-if="!logger" class="mt-1 text-[13px] text-muted">Logger belum mengirim status.</p>
      </div>

      <div class="lg:pl-5">
        <h4 class="mb-1 text-xs font-normal text-muted">Sensor</h4>
        <dl v-if="sensors.length" class="text-[13px] text-ink">
          <div v-for="sensor in sensors" :key="sensor.field" class="flex justify-between gap-3 py-1">
            <dt>{{ sensor.label }}</dt>
            <dd class="font-semibold" :class="sensor.ok ? 'text-ok' : 'text-breach'">{{ sensor.ok ? 'normal' : 'bermasalah' }}</dd>
          </div>
        </dl>
        <p v-else class="text-[13px] text-muted">Logger belum mengirim status sensor.</p>
      </div>
    </div>
    <div v-if="$slots.default" class="mt-5 space-y-4"><slot /></div>
  </section>
</template>
