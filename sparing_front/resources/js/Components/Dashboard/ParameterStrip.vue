<script setup>
import Sparkline from '@/Components/Sparkline.vue';
import { limitPosition } from '@/Utils/dashboardStatus.js';

// Layer 2 of the dashboard sheet: one column per parameter with its latest
// value and where it sits against the limit. pH, TSS and Debit pick the chart
// below; other readings (COD, NH₃-N, …) have no trend API yet and show a
// sparkline instead.
const props = defineProps({
  items: { type: Array, default: () => [] }, // { field, label, value, unit, rule, spark }
  modelValue: { type: String, default: 'tss' },
  selectable: { type: Array, default: () => ['ph', 'tss', 'debit'] },
});
const emit = defineEmits(['update:modelValue']);

const DECIMALS = { ph: 2, nh3n: 2 };
const limitFormat = new Intl.NumberFormat('id-ID', { maximumFractionDigits: 2 });
const numberText = (value, field) => (typeof value === 'number' && Number.isFinite(value)
  ? new Intl.NumberFormat('id-ID', { maximumFractionDigits: DECIMALS[field] ?? 1 }).format(value)
  : '—');

function limitText(rule) {
  const min = typeof rule?.danger_min === 'number' ? rule.danger_min : null;
  const max = typeof rule?.danger_max === 'number' ? rule.danger_max : null;
  if (min !== null && max !== null) return `batas ${limitFormat.format(min)}–${limitFormat.format(max)}`;
  if (max !== null) return `batas ${limitFormat.format(max)}`;
  if (min !== null) return `min. ${limitFormat.format(min)}`;
  return 'tanpa baku mutu';
}

const isSelectable = (field) => props.selectable.includes(field);
const position = (item) => limitPosition(item.value, item.rule?.is_active === false ? null : item.rule);
const isSelected = (item) => isSelectable(item.field) && item.field === props.modelValue;

function select(field) {
  if (field !== props.modelValue) emit('update:modelValue', field);
}

function cellAttrs(item) {
  if (!isSelectable(item.field)) return {};
  return { type: 'button', 'aria-pressed': isSelected(item) ? 'true' : 'false', onClick: () => select(item.field) };
}
</script>

<template>
  <div class="grid grid-cols-2 border-b border-line md:flex md:divide-x md:divide-line" role="group" aria-label="Parameter saat ini">
    <component
      :is="isSelectable(item.field) ? 'button' : 'div'"
      v-for="item in items"
      :key="item.field"
      v-bind="cellAttrs(item)"
      class="relative min-w-0 border-b border-line px-4 py-3.5 text-left odd:border-r md:flex-1 md:border-b-0 md:px-5 md:odd:border-r-0"
      :class="[
        isSelectable(item.field) ? 'cursor-pointer transition-colors hover:bg-[#F7FAFA] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-[-2px] focus-visible:outline-primary' : '',
        isSelected(item) ? 'bg-[#F2F8F8]' : '',
      ]"
    >
      <span class="block text-[12.5px] font-semibold text-muted">{{ item.label }}</span>
      <span class="mt-0.5 block text-[24px] font-bold leading-tight tracking-tight tabular-nums" :class="position(item).breach ? 'text-breach' : 'text-ink'">
        {{ numberText(item.value, item.field) }}<small v-if="item.unit" class="ml-1 text-[12.5px] font-medium tracking-normal text-muted">{{ item.unit }}</small>
      </span>
      <span class="block text-xs text-muted">{{ limitText(item.rule) }}</span>
      <span v-if="position(item).kind !== 'none'" class="relative mt-2 block h-1 rounded bg-line" aria-hidden="true">
        <span
          class="absolute inset-y-0 rounded"
          :class="position(item).breach ? 'bg-breach' : 'bg-primary'"
          :style="{ left: `${position(item).start}%`, width: `${Math.max(position(item).end - position(item).start, 2)}%` }"
        ></span>
      </span>
      <span v-if="item.spark && !isSelectable(item.field)" class="mt-2 block w-full max-w-[8rem]">
        <Sparkline :points="item.spark" :threshold="item.rule?.danger_max ?? null" />
      </span>
      <span v-if="isSelected(item)" class="absolute inset-x-0 bottom-0 h-[3px] bg-primary" aria-hidden="true"></span>
    </component>
  </div>
</template>
