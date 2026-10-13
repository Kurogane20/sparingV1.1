<template>
  <div>
    <nav class="text-xs text-[#617377] mb-3">
      <template v-for="(c, i) in crumb" :key="i">
        <span v-if="i < crumb.length - 1">{{ c }} / </span>
        <b v-else class="text-ink font-semibold">{{ c }}</b>
      </template>
    </nav>
    <!-- The mobile menu button lives in UtilityStrip (always visible); don't add one here. -->
    <div class="flex items-end justify-between gap-4 flex-wrap mb-5">
      <div class="min-w-0">
        <h2 class="text-[19px] font-bold text-ink leading-tight">{{ title }}</h2>
        <p v-if="subtitle" class="text-[#617377] text-[12.5px] mt-0.5">{{ subtitle }}</p>
      </div>
      <div class="flex flex-wrap gap-2 items-center min-w-0 max-w-full">
        <slot name="actions" />
      </div>
    </div>
  </div>
</template>

<script setup>
defineProps({
  crumb: { type: Array, default: () => [] },
  title: { type: String, default: '' },
  subtitle: { type: String, default: '' },
});
</script>
