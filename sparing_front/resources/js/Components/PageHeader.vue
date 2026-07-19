<template>
  <div>
    <nav class="text-xs text-[#617377] mb-3">
      <template v-for="(c, i) in crumb" :key="i">
        <span v-if="i < crumb.length - 1">{{ c }} / </span>
        <b v-else class="text-ink font-semibold">{{ c }}</b>
      </template>
    </nav>
    <div class="flex items-end justify-between gap-4 flex-wrap mb-5">
      <div class="flex items-center gap-3">
        <button
          type="button"
          class="md:hidden w-9 h-9 rounded-md border border-[#D7E0E1] flex items-center justify-center text-ink hover:bg-[#EEF2F3] transition-colors shrink-0"
          @click="toggleSidebar"
          aria-label="Buka menu"
        >
          <i class="fas fa-bars text-sm"></i>
        </button>
        <div>
          <h2 class="text-[19px] font-bold text-ink leading-tight">{{ title }}</h2>
          <p v-if="subtitle" class="text-[#617377] text-[12.5px] mt-0.5">{{ subtitle }}</p>
        </div>
      </div>
      <div class="flex gap-2 items-center">
        <slot name="actions" />
      </div>
    </div>
  </div>
</template>

<script setup>
import { inject } from 'vue';

defineProps({
  crumb: { type: Array, default: () => [] },
  title: { type: String, default: '' },
  subtitle: { type: String, default: '' },
});

// AppLayout owns sidebarOpen and provides the toggle function; fall back to a
// no-op so this component still works if mounted outside AppLayout.
const toggleSidebar = inject('toggleSidebar', () => {});
</script>
