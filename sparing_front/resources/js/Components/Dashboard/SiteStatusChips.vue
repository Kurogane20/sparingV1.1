<script setup>
import { nextTick, ref, watch } from 'vue';

const props = defineProps({
  chips: { type: Array, default: () => [] },
  modelValue: { type: String, default: '' },
});
const emit = defineEmits(['update:modelValue']);

const STATUS = {
  danger: { dot: '#B03030', text: 'bahaya' },
  warning: { dot: '#9A6B00', text: 'waspada' },
  offline: { dot: '#8FA0A3', text: 'mati' },
  nodata: { dot: '#C4D1D3', text: 'tanpa data terbaru' },
  normal: { dot: '#1F7A4D', text: 'normal' },
};
const presentation = (status) => STATUS[status] ?? STATUS.nodata;

function select(uid) {
  if (uid !== props.modelValue) emit('update:modelValue', uid);
}

// Chips re-sort when site statuses arrive (problem sites first); keep the
// active chip inside the row horizontally without scrolling the page itself.
const scroller = ref(null);
watch(() => [props.modelValue, props.chips.map((chip) => chip.uid).join('|')], async () => {
  await nextTick();
  const row = scroller.value;
  const active = row?.querySelector?.('[aria-pressed="true"]');
  if (!row || !active) return;
  const left = active.offsetLeft;
  const right = left + active.offsetWidth;
  if (left < row.scrollLeft) row.scrollLeft = left;
  else if (right > row.scrollLeft + row.clientWidth) row.scrollLeft = right - row.clientWidth;
}, { flush: 'post' });
</script>

<template>
  <div v-if="chips.length > 1" class="mb-4 min-w-0 max-w-full md:mb-5">
    <!-- relative: keeps the absolutely positioned sr-only text inside the overflow clip -->
    <div role="group" aria-label="Pilih lokasi pemantauan" ref="scroller" class="chip-scroller relative flex min-w-0 gap-2 overflow-x-auto pb-1">
      <button
        v-for="chip in chips"
        :key="chip.uid"
        type="button"
        :aria-pressed="chip.uid === modelValue ? 'true' : 'false'"
        :title="`${chip.name} — ${presentation(chip.status).text}`"
        class="inline-flex shrink-0 items-center gap-2 rounded-full border px-3 py-1.5 text-xs font-semibold transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary"
        :class="chip.uid === modelValue ? 'border-primary bg-[#E4F1F2] text-ink' : 'border-[#D7E0E1] bg-white text-[#617377] hover:bg-[#EEF2F3]'"
        @click="select(chip.uid)"
      >
        <span class="h-2 w-2 shrink-0 rounded-full" :style="{ background: presentation(chip.status).dot }" aria-hidden="true"></span>
        <span class="whitespace-nowrap">{{ chip.name }}</span>
        <span v-if="chip.status === 'offline'" class="font-normal text-[#8FA0A3]">mati</span>
        <span v-else class="sr-only">— {{ presentation(chip.status).text }}</span>
      </button>
    </div>
  </div>
</template>

<style scoped>
/* Phones swipe the chip row: hide the native scrollbar (it rendered as a grey
   bar with arrows under the chips) and fade the edge so more sites read as
   "scroll for more" instead of a clipped name. */
.chip-scroller {
  scrollbar-width: none;
  -webkit-mask-image: linear-gradient(to right, #000 calc(100% - 2rem), transparent);
  mask-image: linear-gradient(to right, #000 calc(100% - 2rem), transparent);
  scroll-padding-inline: 0.25rem;
}
.chip-scroller::-webkit-scrollbar {
  display: none;
}
@media (min-width: 768px) {
  .chip-scroller {
    -webkit-mask-image: none;
    mask-image: none;
  }
}
</style>
