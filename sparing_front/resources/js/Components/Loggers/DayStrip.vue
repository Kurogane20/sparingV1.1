<script setup>
// The last 30 days of one logger, one cell per local day (oldest left).
defineProps({
  cells: { type: Array, default: () => [] }, // from dayStrip()
});
const LEVEL_CLASS = {
  none: 'bg-[#CFE3DF]',
  short: 'bg-breach-muted',
  long: 'bg-[#D9835F]',
  full: 'bg-breach',
};
</script>

<template>
  <ol class="flex h-3 w-full max-w-[22rem] gap-[2px]" aria-label="Gangguan 30 hari terakhir">
    <li
      v-for="cell in cells"
      :key="cell.date"
      class="h-full min-w-0 flex-1 rounded-[2px]"
      :class="LEVEL_CLASS[cell.level]"
      :title="cell.text"
    >
      <span class="sr-only">{{ cell.text }}</span>
    </li>
  </ol>
</template>
