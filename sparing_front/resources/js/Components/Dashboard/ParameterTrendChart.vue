<script setup>
import WaterQualityTrendChart from './WaterQualityTrendChart.vue';
import DebitTrendChart from './DebitTrendChart.vue';

// One chart for the parameter picked in ParameterStrip. pH/TSS and Debit keep
// their own tested chart logic (axes, thresholds, events, tooltips); compact
// mode drops their card, heading and summaries, which the strip already shows.
defineProps({
  field: { type: String, default: 'tss' },
  snapshot: { type: Object, default: null },
  state: { type: String, default: 'idle' },
  stale: { type: Boolean, default: false },
  focusedEventId: { type: [String, Number], default: null },
  reducedMotion: { type: Boolean, default: false },
});
defineEmits(['retry']);
</script>

<template>
  <DebitTrendChart
    v-if="field === 'debit'"
    compact
    :snapshot="snapshot"
    :state="state"
    :stale="stale"
    :focused-event-id="focusedEventId"
    :reduced-motion="reducedMotion"
    @retry="$emit('retry')"
  />
  <WaterQualityTrendChart
    v-else
    compact
    :fields="[field]"
    :snapshot="snapshot"
    :state="state"
    :stale="stale"
    :focused-event-id="focusedEventId"
    :reduced-motion="reducedMotion"
    @retry="$emit('retry')"
  />
</template>
