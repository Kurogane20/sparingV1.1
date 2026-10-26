<script setup>
import { computed } from 'vue';
import CompletenessBar from './CompletenessBar.vue';
import { FIELD_LABELS } from '@/Utils/dashboardStatus.js';
import { formatDashboardTimestamp } from '@/Utils/dashboardTimeseries.js';
import { formatNumber, getSensorUnit } from '@/Utils/helpers';

// Layer 1 of the dashboard sheet, shown to every role: is the site compliant
// today, how did the month go, how complete is today's data.
const props = defineProps({
  band: { type: Object, required: true },       // bandState()
  month: { type: Object, default: null },        // monthCompliance()
  completenessPct: { type: Number, default: null },
  completenessAsOf: { type: String, default: '' },
  completenessSegments: { type: Object, default: null },
  siteLabel: { type: String, default: '' },
  dateLabel: { type: String, default: '' },
  timezone: { type: String, default: 'Asia/Jakarta' },
  canFollowup: { type: Boolean, default: false },
});
defineEmits(['followup']);

const TONES = {
  deep: { band: 'bg-deep text-[#EAF4F3]', muted: 'text-deep-muted' },
  breach: { band: 'bg-breach-band text-[#FCEDE6]', muted: 'text-breach-muted' },
  idle: { band: 'bg-idle text-white', muted: 'text-[#C9D6D9]' },
};
const ICONS = {
  compliant: { glyph: 'fas fa-check', badge: 'bg-ok-bright text-deep' },
  breached_today: { glyph: 'fas fa-exclamation', badge: 'bg-[#E0A45A] text-deep' },
  breach_now: { glyph: 'fas fa-exclamation', badge: 'bg-[#F4A582] text-breach-band' },
  stale: { glyph: 'fas fa-clock', badge: 'bg-white/20 text-white' },
  unverified: { glyph: 'fas fa-circle-question', badge: 'bg-white/20 text-white' },
  no_rules: { glyph: 'fas fa-sliders', badge: 'bg-white/20 text-white' },
};
const CELL_CLASS = { ok: 'bg-ok-bright', violation: 'bg-[#E58F65]', empty: 'bg-white/15', future: 'bg-white/5' };
const CELL_TEXT = { ok: 'patuh', violation: 'melewati baku mutu', empty: 'tanpa data', future: 'belum terjadi' };

const decimalFormat = new Intl.NumberFormat('id-ID', { maximumFractionDigits: 2 });
const pctFormat = new Intl.NumberFormat('id-ID', { maximumFractionDigits: 1 });

function limitText({ min, max }) {
  if (min !== null && max !== null) return `${decimalFormat.format(min)}–${decimalFormat.format(max)}`;
  if (max !== null) return decimalFormat.format(max);
  return `min. ${decimalFormat.format(min)}`;
}

const tone = computed(() => {
  if (props.band.state === 'breach_now') return TONES.breach;
  if (['stale', 'no_rules', 'unverified'].includes(props.band.state)) return TONES.idle;
  return TONES.deep;
});
const icon = computed(() => ICONS[props.band.state] ?? ICONS.no_rules);

const title = computed(() => {
  const { band } = props;
  if (band.state === 'compliant') return 'Patuh hari ini';
  if (band.state === 'breached_today') return 'Sempat melewati baku mutu hari ini';
  if (band.state === 'breach_now') return band.title;
  if (band.state === 'stale') {
    return band.lastTs ? `Data terhenti sejak ${formatDashboardTimestamp(band.lastTs, props.timezone)}` : 'Belum ada data';
  }
  // Today not judged yet (compliance-daily unknown, or nothing measured today).
  if (band.state === 'unverified') return band.measurement ? 'Bacaan terakhir dalam baku mutu' : 'Bacaan terakhir belum bisa dinilai';
  return 'Baku mutu belum diatur';
});

const detail = computed(() => {
  const { band } = props;
  if (band.state === 'compliant') {
    return band.nearLimit ? 'Semua parameter di bawah baku mutu, ada yang mendekati batas.' : 'Semua parameter di bawah baku mutu.';
  }
  if (band.state === 'breached_today') return 'Sekarang kembali normal. Rinciannya ada di catatan kejadian.';
  if (band.state === 'breach_now') {
    const readings = band.breaches.map((breach) => {
      const unit = breach.field === 'ph' ? '' : ` ${getSensorUnit(breach.field)}`;
      return `${FIELD_LABELS[breach.field] ?? breach.field} ${decimalFormat.format(breach.value)}${unit} (batas ${limitText(breach)})`;
    });
    const since = band.since ? `sejak ${formatDashboardTimestamp(band.since, props.timezone, true)}` : null;
    return [...readings, since].filter(Boolean).join(' · ');
  }
  if (band.state === 'stale') {
    return band.breachedToday ? 'Sempat melewati baku mutu hari ini.' : 'Status kepatuhan diperbarui saat data masuk.';
  }
  if (band.state === 'unverified') return 'Status kepatuhan hari ini belum bisa dipastikan.';
  return 'Status kepatuhan belum bisa dinilai untuk lokasi ini.';
});

const showFollowup = computed(() => props.band.state === 'breach_now' && props.canFollowup && props.band.alertId != null);

const monthName = computed(() => {
  const first = props.month?.cells?.[0]?.date;
  return first
    ? new Intl.DateTimeFormat('id-ID', { month: 'long', timeZone: 'UTC' }).format(new Date(`${first}T00:00:00Z`))
    : 'bulan ini';
});
const monthPct = computed(() => (props.month?.pct == null ? '—' : `${pctFormat.format(props.month.pct)}%`));
const monthCount = computed(() => (props.month?.judged
  ? `${props.month.compliant} dari ${props.month.judged} hari patuh`
  : 'Belum ada hari yang dinilai'));
const completenessText = computed(() => (props.completenessPct == null ? '—' : `${formatNumber(props.completenessPct, 1)}%`));
const cellTitle = (cell) => `${cell.date}: ${CELL_TEXT[cell.status]}`;
</script>

<template>
  <section class="grid gap-5 px-5 py-5 md:grid-cols-[minmax(0,1.25fr)_minmax(0,1fr)_minmax(0,1fr)] md:items-end md:px-6" :class="tone.band" aria-label="Status kepatuhan">
    <div class="min-w-0">
      <p class="text-[12.5px]" :class="tone.muted">{{ siteLabel }}<span v-if="siteLabel && dateLabel"> · </span>{{ dateLabel }}</p>
      <div class="mt-2 flex items-center gap-3">
        <span class="grid h-8 w-8 shrink-0 place-items-center rounded-full text-sm" :class="icon.badge" aria-hidden="true"><i :class="icon.glyph"></i></span>
        <h2 class="text-[24px] font-extrabold leading-tight tracking-tight md:text-[30px]">{{ title }}</h2>
      </div>
      <p class="mt-2 text-[13px]">{{ detail }}</p>
      <button
        v-if="showFollowup"
        type="button"
        class="mt-3 rounded-md bg-[#FCEDE6] px-3 py-1.5 text-[13px] font-bold text-breach-band focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-white"
        @click="$emit('followup', band.alertId)"
      >Catat tindak lanjut</button>
    </div>

    <div class="min-w-0">
      <p class="text-[12.5px]" :class="tone.muted">Kepatuhan {{ monthName }}</p>
      <p class="text-[36px] font-bold leading-none tracking-tight tabular-nums md:text-[40px]">{{ monthPct }}</p>
      <p class="mt-1 text-[12.5px]" :class="tone.muted">{{ monthCount }}</p>
      <ol v-if="month?.cells?.length" class="relative mt-2 grid max-w-[220px] grid-cols-[repeat(16,minmax(0,1fr))] gap-0.5" aria-label="Kalender kepatuhan bulan ini">
        <li v-for="cell in month.cells" :key="cell.date" class="h-[7px] rounded-[1.5px]" :class="CELL_CLASS[cell.status]" :title="cellTitle(cell)">
          <span class="sr-only">{{ cellTitle(cell) }}</span>
        </li>
      </ol>
    </div>

    <div class="min-w-0">
      <p class="text-[12.5px]" :class="tone.muted">Kelengkapan data hari ini</p>
      <p class="text-[36px] font-bold leading-none tracking-tight tabular-nums md:text-[40px]">
        {{ completenessText }}<span v-if="completenessAsOf" class="ml-1.5 text-xs font-medium tracking-normal" :class="tone.muted">s.d. {{ completenessAsOf }}</span>
      </p>
      <CompletenessBar v-if="completenessSegments" class="mt-2 max-w-[260px]" :segments="completenessSegments" dark />
    </div>
  </section>
</template>
