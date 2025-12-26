<template>
  <div :class="['sensor-card group', statusBorderClass]">
    <!-- Gradient Top Border (visible on hover) -->
    <div class="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-primary via-emerald-400 to-cyan-400 opacity-0 group-hover:opacity-100 transition-opacity duration-300 rounded-t-2xl"></div>
    
    <!-- Header with label and icon -->
    <div class="flex justify-between items-start mb-4">
      <div>
        <span class="text-sm font-medium text-gray-500">{{ label }}</span>
        <span v-if="statusLabel" :class="['ml-2 text-xs font-medium px-2 py-0.5 rounded-full', statusBadgeClass]">
          {{ statusLabel }}
        </span>
      </div>
      <div
        :class="[
          'w-12 h-12 rounded-xl flex items-center justify-center text-lg transition-all duration-300 group-hover:scale-110 group-hover:shadow-lg',
          iconClass,
        ]"
      >
        <i :class="icon"></i>
      </div>
    </div>

    <!-- Value Display -->
    <div class="mb-2">
      <div class="flex items-baseline gap-2">
        <span class="text-4xl font-bold bg-gradient-to-r from-gray-900 via-gray-700 to-gray-600 bg-clip-text text-transparent">
          {{ displayValue }}
        </span>
        <span v-if="unit" class="text-base font-medium text-gray-400">
          {{ unit }}
        </span>
      </div>
    </div>

    <!-- Trend Indicator -->
    <div
      v-if="trend !== null"
      :class="['flex items-center gap-2 text-sm font-medium', trendClass]"
    >
      <div :class="['w-6 h-6 rounded-full flex items-center justify-center', trendBgClass]">
        <i :class="[trendIcon, 'text-xs']"></i>
      </div>
      <span>{{ trendText }}</span>
    </div>

    <!-- No Data State -->
    <div v-else-if="value === null || value === undefined" class="flex items-center gap-2 text-sm text-gray-400">
      <i class="fas fa-info-circle"></i>
      <span>Data tidak tersedia</span>
    </div>

    <!-- Decorative Element -->
    <div class="absolute bottom-0 right-0 w-24 h-24 bg-gradient-to-tl from-primary/5 to-transparent rounded-tl-full pointer-events-none"></div>
  </div>
</template>

<script setup>
import { computed } from 'vue';
import { formatNumber, getThresholdStatus } from '@/Utils/helpers';

// Props
const props = defineProps({
  label: {
    type: String,
    required: true,
  },
  value: {
    type: [Number, String],
    default: null,
  },
  unit: {
    type: String,
    default: '',
  },
  icon: {
    type: String,
    required: true,
  },
  iconClass: {
    type: String,
    default: 'bg-gray-100 text-gray-600',
  },
  trend: {
    type: Number,
    default: null,
  },
  field: {
    type: String,
    default: null,
  },
  decimals: {
    type: Number,
    default: 1,
  },
});

// Display formatted value
const displayValue = computed(() => {
  if (props.value === null || props.value === undefined) return '-';
  return formatNumber(props.value, props.decimals);
});

// Trend styling
const trendClass = computed(() => {
  if (props.trend === null || props.trend === 0) return 'text-gray-500';
  return props.trend > 0 ? 'text-rose-600' : 'text-emerald-600';
});

const trendBgClass = computed(() => {
  if (props.trend === null || props.trend === 0) return 'bg-gray-100';
  return props.trend > 0 ? 'bg-rose-100' : 'bg-emerald-100';
});

const trendIcon = computed(() => {
  if (props.trend === null || props.trend === 0) return 'fas fa-minus';
  return props.trend > 0 ? 'fas fa-arrow-up' : 'fas fa-arrow-down';
});

const trendText = computed(() => {
  if (props.trend === null) return 'Tidak ada data tren';
  if (props.trend === 0) return 'Stabil';
  const percentage = Math.abs(props.trend).toFixed(1);
  return `${percentage}% dari 1 jam lalu`;
});

// Status based on threshold
const thresholdStatus = computed(() => {
  if (!props.field || props.value === null) return null;
  return getThresholdStatus(props.field, props.value);
});

const statusLabel = computed(() => {
  if (!thresholdStatus.value) return null;
  if (thresholdStatus.value === 'normal') return 'Baik';
  if (thresholdStatus.value === 'warning') return 'Peringatan';
  if (thresholdStatus.value === 'danger') return 'Bahaya';
  return null;
});

const statusBadgeClass = computed(() => {
  if (!thresholdStatus.value) return '';
  if (thresholdStatus.value === 'normal') return 'bg-emerald-100 text-emerald-700';
  if (thresholdStatus.value === 'warning') return 'bg-amber-100 text-amber-700';
  if (thresholdStatus.value === 'danger') return 'bg-rose-100 text-rose-700';
  return '';
});

const statusBorderClass = computed(() => {
  if (!thresholdStatus.value) return '';
  if (thresholdStatus.value === 'danger') return 'ring-2 ring-rose-200';
  if (thresholdStatus.value === 'warning') return 'ring-2 ring-amber-200';
  return '';
});
</script>

<style scoped>
.sensor-card {
  min-height: 160px;
  position: relative;
  background: linear-gradient(135deg, #ffffff 0%, #fafafa 100%);
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.05);
}
</style>
