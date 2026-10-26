<script setup>
import { computed } from 'vue';
import CompletenessBar from './CompletenessBar.vue';
import { FIELD_LABELS, joinLabels, localDateISO } from '@/Utils/dashboardStatus.js';
import { formatDashboardTimestamp } from '@/Utils/dashboardTimeseries.js';
import { getSensorUnit } from '@/Utils/helpers';

// Layer 1 of the dashboard sheet, shown to every role: is the site compliant
// today, how did the month go, how complete is today's data. Every sentence
// must be backed by the data: it never vouches for a value it could not judge.
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
  // "Now" (ms): decides whether a timestamp is from today (time only) or needs its date.
  now: { type: Number, default: () => Date.now() },
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
// Violation days also get a ring: the colours alone are too close for colour-blind readers.
const CELL_CLASS = {
  ok: 'bg-ok-bright',
  violation: 'bg-[#E58F65] ring-1 ring-inset ring-white/70',
  empty: 'bg-white/15',
  future: 'bg-white/5',
};
const CELL_TEXT = { ok: 'patuh', violation: 'melewati baku mutu', empty: 'tanpa data', future: 'belum terjadi' };

const decimalFormat = new Intl.NumberFormat('id-ID', { maximumFractionDigits: 2 });
const pctFormat = new Intl.NumberFormat('id-ID', { maximumFractionDigits: 1 });
const dayFormat = new Intl.DateTimeFormat('id-ID', { day: 'numeric', month: 'short', timeZone: 'UTC' });
const pct = (value) => (value == null ? '—' : `${pctFormat.format(value)}%`);

// A timestamp from today reads as a time; an older (or future) one keeps its date.
function when(iso) {
  const sameDay = localDateISO(props.timezone, new Date(iso)) === localDateISO(props.timezone, new Date(props.now));
  return formatDashboardTimestamp(iso, props.timezone, sameDay);
}

function limitText({ min, max }) {
  if (min !== null && max !== null) return `${decimalFormat.format(min)}–${decimalFormat.format(max)}`;
  if (max !== null) return decimalFormat.format(max);
  return `min. ${decimalFormat.format(min)}`;
}

// What the latest reading supports after an earlier breach today.
function latestVerdict(band) {
  if (!band.judged?.length) return 'Bacaan terakhir belum bisa dinilai.';
  if (!band.unjudged?.length) return 'Bacaan terakhir kembali dalam baku mutu.';
  return `Bacaan terakhir ${joinLabels(band.judged)} dalam baku mutu; ${joinLabels(band.unjudged)} belum bisa dinilai.`;
}

const tone = computed(() => {
  if (props.band.state === 'breach_now') return TONES.breach;
  if (['compliant', 'breached_today'].includes(props.band.state)) return TONES.deep;
  return TONES.idle;
});
const icon = computed(() => ICONS[props.band.state] ?? ICONS.no_rules);

const title = computed(() => {
  const { band } = props;
  if (band.state === 'compliant') return 'Patuh hari ini';
  if (band.state === 'breached_today') return 'Sempat melewati baku mutu hari ini';
  if (band.state === 'breach_now') return band.title;
  if (band.state === 'stale') {
    if (band.reason === 'future') return 'Jam logger tidak sesuai';
    return band.lastTs ? `Data terhenti sejak ${when(band.lastTs)}` : 'Belum ada data';
  }
  if (band.state === 'unverified') {
    if (!band.judged?.length) return 'Bacaan terakhir belum bisa dinilai';
    return band.unjudged?.length ? `Bacaan terakhir ${joinLabels(band.judged)} dalam baku mutu` : 'Bacaan terakhir dalam baku mutu';
  }
  if (band.state === 'no_rules') return 'Baku mutu belum diatur';
  return 'Status belum bisa ditentukan';
});

const detail = computed(() => {
  const { band } = props;
  if (band.state === 'compliant') {
    return band.nearLimit
      ? 'Tidak ada bacaan di luar baku mutu sejauh ini; ada yang mendekati batas.'
      : 'Tidak ada bacaan di luar baku mutu sejauh ini.';
  }
  if (band.state === 'breached_today') return `${latestVerdict(band)} Rinciannya ada di catatan kejadian.`;
  if (band.state === 'breach_now') {
    const readings = band.breaches.map((breach) => {
      const unit = breach.field === 'ph' ? '' : ` ${getSensorUnit(breach.field)}`;
      return `${FIELD_LABELS[breach.field] ?? breach.field} ${decimalFormat.format(breach.value)}${unit} (batas ${limitText(breach)})`;
    });
    return [...readings, band.since ? `sejak ${when(band.since)}` : null].filter(Boolean).join(' · ');
  }
  if (band.state === 'stale') {
    if (band.reason === 'future') {
      return `Bacaan terakhir tercatat ${when(band.lastTs)}, lebih maju dari waktu sekarang. Status kepatuhan belum bisa dinilai.${band.breachedToday ? ' Sempat melewati baku mutu hari ini.' : ''}`;
    }
    return band.breachedToday ? 'Sempat melewati baku mutu hari ini.' : 'Status kepatuhan diperbarui saat data masuk.';
  }
  if (band.state === 'unverified') {
    const partial = band.judged?.length && band.unjudged?.length ? `${joinLabels(band.unjudged)} belum bisa dinilai. ` : '';
    return `${partial}Status kepatuhan hari ini belum bisa dipastikan.`;
  }
  if (band.state === 'no_rules') return 'Status kepatuhan belum bisa dinilai untuk lokasi ini.';
  return '';
});

const showFollowup = computed(() => props.band.state === 'breach_now' && props.canFollowup && props.band.alertId != null);

const monthName = computed(() => {
  const first = props.month?.cells?.[0]?.date;
  return first
    ? new Intl.DateTimeFormat('id-ID', { month: 'long', timeZone: 'UTC' }).format(new Date(`${first}T00:00:00Z`))
    : 'bulan ini';
});
const monthCount = computed(() => (props.month?.judged
  ? `${props.month.compliant} dari ${props.month.judged} hari patuh`
  : 'Belum ada hari yang dinilai'));
// The calendar strip is visual only; the violation days are also said in words.
const violationDays = computed(() => (props.month?.cells ?? [])
  .filter((cell) => cell.status === 'violation')
  .map((cell) => Number(cell.date.slice(8))));
const violationText = computed(() => {
  const runs = [];
  for (const day of violationDays.value) {
    const last = runs[runs.length - 1];
    if (last && day === last[1] + 1) last[1] = day; else runs.push([day, day]);
  }
  return runs.map(([first, end]) => (first === end ? `${first}` : `${first}–${end}`)).join(', ');
});
const cellTitle =(cell) => `${dayFormat.format(new Date(`${cell.date}T00:00:00Z`))}: ${CELL_TEXT[cell.status]}`;
</script>

<template>
  <section class="grid grid-cols-2 gap-x-4 gap-y-5 px-5 py-5 md:px-6 lg:grid-cols-[minmax(0,1.25fr)_minmax(0,1fr)_minmax(0,1fr)] lg:items-end" :class="tone.band" aria-label="Status kepatuhan">
    <div class="col-span-2 min-w-0 lg:col-span-1">
      <p class="text-[12.5px]" :class="tone.muted">{{ siteLabel }}<span v-if="siteLabel && dateLabel"> · </span>{{ dateLabel }}</p>
      <div class="mt-2 flex items-center gap-3" role="status" aria-live="polite">
        <span class="grid h-8 w-8 shrink-0 place-items-center rounded-full text-sm" :class="icon.badge" aria-hidden="true"><i :class="icon.glyph"></i></span>
        <h2 class="min-w-0 text-[24px] font-extrabold leading-tight tracking-tight [overflow-wrap:anywhere] md:text-[28px] xl:text-[30px]">{{ title }}</h2>
      </div>
      <p v-if="detail" class="mt-2 text-[13px]">{{ detail }}</p>
      <button
        v-if="showFollowup"
        type="button"
        class="mt-3 rounded-md bg-[#FCEDE6] px-3 py-1.5 text-[13px] font-bold text-breach-band transition-colors hover:bg-white focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-white"
        @click="$emit('followup', band.alertId)"
      >Catat tindak lanjut</button>
    </div>

    <div class="min-w-0">
      <p class="text-[12.5px]" :class="tone.muted">Kepatuhan {{ monthName }}</p>
      <p class="text-[30px] font-bold leading-none tracking-tight tabular-nums md:text-[40px]">{{ pct(month?.pct) }}</p>
      <p class="mt-1 text-[12.5px]" :class="tone.muted">{{ monthCount }}</p>
      <p v-if="violationDays.length" class="mt-0.5 text-[12.5px]" :class="tone.muted">Melewati baku mutu: tgl {{ violationText }}</p>
      <ol v-if="month?.cells?.length" aria-hidden="true" class="mt-2 grid max-w-[220px] grid-cols-[repeat(16,minmax(0,1fr))] gap-0.5">
        <li v-for="cell in month.cells" :key="cell.date" class="h-[7px] rounded-[1.5px]" :class="CELL_CLASS[cell.status]" :title="cellTitle(cell)"></li>
      </ol>
    </div>

    <div class="min-w-0">
      <p class="text-[12.5px]" :class="tone.muted">Kelengkapan hari ini</p>
      <p class="text-[30px] font-bold leading-none tracking-tight tabular-nums md:text-[40px]">
        {{ pct(completenessPct) }} <span v-if="completenessAsOf" class="ml-1 whitespace-nowrap text-xs font-medium tracking-normal" :class="tone.muted">s.d. {{ completenessAsOf }}</span>
      </p>
      <CompletenessBar v-if="completenessSegments" class="mt-2 max-w-[260px]" :class="tone.muted" :segments="completenessSegments" dark />
    </div>
  </section>
</template>
