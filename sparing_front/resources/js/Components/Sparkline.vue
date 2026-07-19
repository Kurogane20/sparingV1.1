<template>
  <svg viewBox="0 0 120 34" preserveAspectRatio="none" class="w-full h-[34px] mt-1.5">
    <line v-if="threshLine !== null" :x1="0" :y1="threshLine" :x2="120" :y2="threshLine"
          stroke="#B03030" stroke-width="1" stroke-dasharray="3 3" opacity="0.6" />
    <path v-if="d" :d="d" fill="none" :stroke="color" stroke-width="1.8" />
  </svg>
</template>
<script setup>
import { computed } from 'vue';
const props = defineProps({ points: { type: Array, default: () => [] }, threshold: { type: Number, default: null }, color: { type: String, default: '#0E7C86' } });
const bounds = computed(() => {
  const vals = props.points.filter((v) => v != null);
  const extra = props.threshold != null ? [props.threshold] : [];
  const all = [...vals, ...extra];
  if (!all.length) return null;
  const min = Math.min(...all), max = Math.max(...all);
  return { min, max, span: (max - min) || 1 };
});
const y = (v, b) => 30 - ((v - b.min) / b.span) * 26 + 2;
const d = computed(() => {
  const b = bounds.value; if (!b || props.points.length < 2) return '';
  const n = props.points.length;
  return props.points.map((v, i) => `${i === 0 ? 'M' : 'L'}${(i / (n - 1)) * 120},${y(v ?? b.min, b)}`).join(' ');
});
const threshLine = computed(() => (props.threshold != null && bounds.value ? y(props.threshold, bounds.value) : null));
</script>
