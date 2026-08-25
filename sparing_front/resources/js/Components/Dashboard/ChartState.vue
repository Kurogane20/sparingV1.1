<script setup>
import { computed } from 'vue';

const props = defineProps({
  state: { type: String, default: 'idle' },
  message: { type: String, default: '' },
  partialReasons: { type: Array, default: () => [] },
  availability: { type: Number, default: undefined },
});

const emit = defineEmits(['retry']);

const reasonCopy = {
  missing_intervals: 'Ada interval data yang hilang',
  stale_tail: 'Data terbaru belum diterima',
  field_missing: 'Salah satu parameter tidak tersedia',
  event_limit_reached: 'Jumlah event dibatasi',
  events_limited: 'Jumlah event dibatasi',
  point_limit_reached: 'Jumlah titik data dibatasi',
  points_limited: 'Jumlah titik data dibatasi',
  event_fetch_failed: 'Event pemantauan tidak dapat dimuat',
  events_failed: 'Event pemantauan tidak dapat dimuat',
};

const partialReasonText = computed(() => props.partialReasons
  .map((reason) => {
    const code = typeof reason === 'string' ? reason : reason?.code;
    if (typeof reason?.message === 'string' && reason.message.trim()) return reason.message;
    if (typeof code !== 'string' || !code.trim()) return null;
    return reasonCopy[code] ?? code
      .replaceAll(/[_-]+/g, ' ')
      .replace(/\b\w/g, (letter) => letter.toUpperCase());
  })
  .filter(Boolean));

const hasAvailability = computed(() => Number.isFinite(props.availability));
const isContentState = computed(() => ['ready', 'partial', 'stale'].includes(props.state));
const retryMessage = computed(() => props.message || 'Silakan coba memuat data kembali.');
function retry() { emit('retry'); }
</script>

<template>
  <section class="chart-container min-h-[200px]" :aria-busy="state === 'loading' ? 'true' : undefined">
    <div v-if="state === 'loading'" class="flex min-h-[200px] flex-col justify-center gap-3 p-5" aria-live="polite">
      <div class="skeleton h-4 w-2/5"></div>
      <div class="skeleton h-28 w-full"></div>
      <p class="text-sm text-slate-500">Memuat data pemantauan…</p>
    </div>

    <div v-else-if="state === 'empty'" class="flex min-h-[200px] flex-col items-center justify-center p-5 text-center">
      <span aria-hidden="true" class="text-lg text-teal-700">○</span>
      <p class="mt-2 text-sm font-semibold text-slate-700">Tidak ada data pada periode ini</p>
      <p class="mt-1 text-sm text-slate-500">Pilih periode lain atau periksa koneksi perangkat.</p>
    </div>

    <div v-else-if="state === 'error'" class="flex min-h-[200px] flex-col items-center justify-center p-5 text-center" role="alert">
      <span aria-hidden="true" class="text-lg text-red-700">▲</span>
      <p class="mt-2 text-sm font-semibold text-slate-800">Data gagal dimuat</p>
      <p class="mt-1 max-w-md text-sm text-slate-600">{{ retryMessage }}</p>
      <button type="button" class="btn-secondary mt-4 px-4 py-2" @click="retry">Coba Lagi</button>
    </div>

    <template v-else>
      <div v-if="state === 'partial'" class="mb-3 rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-900" aria-live="polite">
        <p class="font-semibold"><span aria-hidden="true">◆</span> Data tidak lengkap</p>
        <ul v-if="partialReasonText.length" class="mt-1 list-disc pl-5 text-amber-800">
          <li v-for="reason in partialReasonText" :key="reason">{{ reason }}</li>
        </ul>
        <p v-if="hasAvailability" class="mt-1">Ketersediaan data: {{ availability }}%</p>
      </div>

      <div v-if="state === 'stale'" class="mb-3 flex flex-wrap items-center gap-2 rounded-md border border-slate-300 bg-slate-50 px-3 py-2 text-sm text-slate-700" aria-live="polite">
        <span aria-hidden="true">◇</span>
        <span class="font-semibold">Pembaruan gagal — menampilkan data terakhir</span>
        <span v-if="message" class="text-slate-600">{{ message }}</span>
        <button type="button" class="btn-secondary ml-auto px-3 py-1.5" @click="retry">Coba Lagi</button>
      </div>

      <slot v-if="isContentState || state === 'idle'"></slot>
    </template>
  </section>
</template>
