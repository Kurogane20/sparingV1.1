<template>
  <div
    class="sensor-card group"
    :class="statusRingClass"
    :style="{ borderLeftColor: accentColor, borderLeftWidth: '4px' }"
  >
    <!-- Subtle accent tint -->
    <div
      class="absolute inset-0 rounded-xl pointer-events-none"
      :style="{ background: accentColor, opacity: 0.025 }"
    ></div>

    <!-- Watermark icon -->
    <div
      class="absolute bottom-2 right-3 pointer-events-none select-none"
      :style="{ color: accentColor, opacity: 0.07 }"
    >
      <i :class="[icon, 'text-5xl']"></i>
    </div>

    <!-- Content -->
    <div class="relative z-10">

      <!-- Label + unified status badge -->
      <div class="flex items-center justify-between gap-2 mb-2.5">
        <p class="text-[10px] font-bold text-slate-400 uppercase tracking-[0.12em] leading-none">{{ label }}</p>
        <span
          v-if="cardStatus"
          :class="['text-[10px] font-semibold px-1.5 py-0.5 rounded leading-none whitespace-nowrap', cardStatus.badge]"
          :title="cardStatus.tip"
        >{{ cardStatus.label }}</span>
      </div>

      <!-- Value -->
      <div class="flex items-baseline gap-1.5 mb-3">
        <span
          class="text-[2rem] font-bold leading-none tracking-tight font-mono"
          :class="valueColorClass"
        >{{ displayValue }}</span>
        <span v-if="unit && value !== null" class="text-xs font-medium text-slate-400">{{ unit }}</span>
      </div>

      <!-- Trend / no-data -->
      <div v-if="trend !== null" :class="['flex items-center gap-1.5 text-xs font-medium', trendClass]">
        <i :class="[trendIcon, 'text-xs']"></i>
        <span>{{ trendText }}</span>
      </div>
      <div v-else-if="value === null || value === undefined" class="flex items-center gap-1.5 text-xs text-slate-300">
        <i class="fas fa-minus text-[10px]"></i>
        <span>Menunggu data</span>
      </div>

    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue';
import { formatNumber, getThresholdStatus } from '@/Utils/helpers';

const props = defineProps({
  label:     { type: String,           required: true },
  value:     { type: [Number, String], default: null },
  unit:      { type: String,           default: '' },
  icon:      { type: String,           required: true },
  iconClass: { type: String,           default: '' },
  trend:     { type: Number,           default: null },
  field:     { type: String,           default: null },
  decimals:  { type: Number,           default: 1 },
  health:    { type: Object,            default: null },
});

const fieldAccentMap = {
  ph:      '#3b82f6',
  tss:     '#0ea5e9',
  cod:     '#6366f1',
  nh3n:    '#10b981',
  debit:   '#14b8a6',
  temp:    '#f97316',
  voltage: '#f59e0b',
  current: '#eab308',
  noise:   '#8b5cf6',
  pm25:    '#ec4899',
  pm10:    '#f43f5e',
};

const accentColor = computed(() => fieldAccentMap[props.field] || '#64748b');

const displayValue = computed(() => {
  if (props.value === null || props.value === undefined) return '—';
  return formatNumber(props.value, props.decimals);
});

const thresholdStatus = computed(() => {
  if (!props.field || props.value === null) return null;
  return getThresholdStatus(props.field, props.value);
});

// One unified status. A faulty sensor outranks the compliance verdict, because
// a "Baik" reading you can't trust is worse than an honest "Cek Sensor".
// Priority: sensor bad > over-limit > near-limit > sensor warning > normal.
const cardStatus = computed(() => {
  const h = props.health?.status;
  const c = thresholdStatus.value;
  const rose  = 'bg-rose-50 text-rose-700';
  const amber = 'bg-amber-50 text-amber-700';
  if (h === 'bad')      return { key: 'sensor_bad', label: 'Cek Sensor', badge: rose,  tip: props.health?.reason || 'Sensor bermasalah' };
  if (c === 'danger')   return { key: 'danger',     label: 'Bahaya',     badge: rose,  tip: 'Melebihi baku mutu' };
  if (c === 'warning')  return { key: 'warning',    label: 'Waspada',    badge: amber, tip: 'Mendekati baku mutu' };
  if (h === 'warning')  return { key: 'sensor_warn',label: 'Cek Sensor', badge: amber, tip: props.health?.reason || 'Perlu perhatian' };
  if (c === 'normal')   return { key: 'ok',         label: 'Baik',       badge: 'bg-emerald-50 text-emerald-700', tip: 'Dalam batas baku mutu' };
  return null;
});

const statusRingClass = computed(() => {
  const k = cardStatus.value?.key;
  if (k === 'sensor_bad' || k === 'danger') return 'ring-1 ring-rose-200';
  if (k === 'warning' || k === 'sensor_warn') return 'ring-1 ring-amber-100';
  return '';
});

const valueColorClass = computed(() => {
  const k = cardStatus.value?.key;
  // A stuck/faulty sensor: dim the number to signal it can't be trusted.
  if (k === 'sensor_bad')  return 'text-slate-400';
  if (k === 'danger')      return 'text-rose-600';
  if (k === 'warning')     return 'text-amber-600';
  return 'text-slate-800';
});

const trendClass = computed(() => {
  if (props.trend === null || props.trend === 0) return 'text-slate-400';
  return props.trend > 0 ? 'text-rose-500' : 'text-emerald-500';
});

const trendIcon = computed(() => {
  if (props.trend === null || props.trend === 0) return 'fas fa-minus';
  return props.trend > 0 ? 'fas fa-arrow-up' : 'fas fa-arrow-down';
});

const trendText = computed(() => {
  if (props.trend === null) return 'Tidak ada data tren';
  if (props.trend === 0)    return 'Stabil';
  const pct = Math.abs(props.trend).toFixed(1);
  return `${pct}% dari 1 jam lalu`;
});
</script>
