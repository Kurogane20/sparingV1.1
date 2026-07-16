<template>
  <span
    :class="[
      'inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-xs font-semibold transition-all duration-300',
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
    online:  'bg-[#E6F2EC] text-[#1F7A4D]',
    active:  'bg-[#E6F2EC] text-[#1F7A4D]',
    warning: 'bg-[#F7EFD9] text-[#9A6B00]',
    offline: 'bg-[#EAEEEF] text-[#6E7E82]',
    inactive:'bg-[#EAEEEF] text-[#6E7E82]',
    error:   'bg-[#F7E4E4] text-[#B03030]',
  };
  return classes[props.status] || classes.inactive;
});

const showDot = computed(() => ['online', 'active'].includes(props.status));

const dotClass = computed(() => {
  if (['online', 'active'].includes(props.status)) {
    return 'bg-[#1F7A4D] animate-pulse';
  }
  return 'bg-[#6E7E82]';
});
</script>
