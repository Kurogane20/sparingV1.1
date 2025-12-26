<template>
  <span
    :class="[
      'inline-flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-semibold transition-all duration-300',
      statusClasses
    ]"
  >
    <!-- Animated dot for online status -->
    <span
      v-if="showDot"
      :class="['w-2 h-2 rounded-full', dotClass]"
    ></span>
    
    <!-- Icon -->
    <i v-if="icon" :class="[icon, 'text-xs']"></i>
    
    <!-- Label -->
    <span>{{ label }}</span>
  </span>
</template>

<script setup>
import { computed } from 'vue';

const props = defineProps({
  status: {
    type: String,
    required: true,
    validator: (value) => ['online', 'active', 'warning', 'offline', 'inactive', 'error'].includes(value),
  },
  label: {
    type: String,
    default: '',
  },
  icon: {
    type: String,
    default: '',
  },
});

const statusClasses = computed(() => {
  const classes = {
    online: 'bg-emerald-100 text-emerald-700 shadow-sm shadow-emerald-200/50',
    active: 'bg-emerald-100 text-emerald-700 shadow-sm shadow-emerald-200/50',
    warning: 'bg-amber-100 text-amber-700 shadow-sm shadow-amber-200/50',
    offline: 'bg-rose-100 text-rose-700 shadow-sm shadow-rose-200/50',
    inactive: 'bg-gray-100 text-gray-600',
    error: 'bg-rose-100 text-rose-700 shadow-sm shadow-rose-200/50',
  };
  return classes[props.status] || classes.inactive;
});

const showDot = computed(() => ['online', 'active'].includes(props.status));

const dotClass = computed(() => {
  if (['online', 'active'].includes(props.status)) {
    return 'bg-emerald-500 animate-pulse';
  }
  return 'bg-gray-400';
});
</script>
