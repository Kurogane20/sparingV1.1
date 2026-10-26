<script setup>
import { computed } from 'vue';

// segments: output of completenessSegments() — received / missing / not yet due.
const props = defineProps({
  segments: { type: Object, default: null },
  compact: { type: Boolean, default: false },
  // On the dashboard's dark status band.
  dark: { type: Boolean, default: false },
});

const due = computed(() => (props.segments ? props.segments.received + props.segments.missing : 0));
const label = computed(() => (props.segments
  ? `${props.segments.received} dari ${due.value} data yang seharusnya sudah masuk; ${props.segments.notYet} data lagi sampai akhir hari`
  : ''));
</script>

<template>
  <div v-if="segments">
    <div class="flex w-full overflow-hidden rounded" :class="[compact ? 'h-1.5' : 'h-[6px]', dark ? 'bg-white/15' : 'bg-[#E5EDED]']" role="img" :aria-label="label">
      <div class="h-full" :class="dark ? 'bg-ok-bright' : 'bg-primary'" :style="{ width: `${segments.receivedPct}%` }"></div>
      <div class="h-full" :class="dark ? 'bg-[#E58F65]' : 'bg-[#C9732B]'" :style="{ width: `${segments.missingPct}%` }"></div>
    </div>
    <p class="mt-1" :class="[compact ? 'text-[10px]' : 'text-xs', dark ? '' : 'text-[#617377]']">
      <span :class="dark ? 'text-white' : 'text-ink'">{{ segments.received }} masuk</span>
      · <span :class="segments.missing ? (dark ? 'text-[#FFC4A6]' : 'text-[#9A4A12]') : ''">{{ segments.missing }} hilang</span>
      · {{ segments.notYet }} belum waktunya
    </p>
  </div>
</template>
