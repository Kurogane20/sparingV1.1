<script setup>
import { computed } from 'vue';
import Sparkline from '@/Components/Sparkline.vue';
import { limitPosition } from '@/Utils/dashboardStatus.js';

// Layer 2 of the dashboard sheet: one cell per parameter with its latest
// value and where it sits against the limit. pH, TSS and Debit pick the chart
// below; other readings (COD, NH₃-N, …) have no trend API yet and show a
// sparkline instead. Like the status band, it never judges a quality-flagged
// value or an inactive limit.
const props = defineProps({
  items: { type: Array, default: () => [] }, // { field, label, value, unit, rule, spark, flagged }
  modelValue: { type: String, default: 'tss' },
  selectable: { type: Array, default: () => ['ph', 'tss', 'debit'] },
  // id of the chart the selectable cells switch (aria-controls).
  chartId: { type: String, default: null },
});
const emit = defineEmits(['update:modelValue']);

// [min, max] fraction digits. pH keeps two so its digits don't jump between readings.
const DIGITS = { ph: [2, 2], nh3n: [0, 2] };
const formatters = new Map();
function numberText(value, field) {
  if (typeof value !== 'number' || !Number.isFinite(value)) return '—';
  const [min, max] = DIGITS[field] ?? [0, 1];
  const key = `${min}:${max}`;
  if (!formatters.has(key)) {
    formatters.set(key, new Intl.NumberFormat('id-ID', { minimumFractionDigits: min, maximumFractionDigits: max }));
  }
  // Tiny negative noise (debit -0.04) would print as "-0".
  return formatters.get(key).format(Number(value.toFixed(max)) === 0 ? 0 : value);
}

const limitFormat = new Intl.NumberFormat('id-ID', { maximumFractionDigits: 2 });
function limitText(rule) {
  const min = typeof rule?.danger_min === 'number' ? rule.danger_min : null;
  const max = typeof rule?.danger_max === 'number' ? rule.danger_max : null;
  if (min !== null && max !== null) return `batas ${limitFormat.format(min)}–${limitFormat.format(max)}`;
  if (max !== null) return `batas ${limitFormat.format(max)}`;
  if (min !== null) return `min. ${limitFormat.format(min)}`;
  return 'tanpa baku mutu';
}

// An inactive rule is no limit at all: not shown, not judged.
const activeRule = (item) => (item.rule && item.rule.is_active !== false ? item.rule : null);

const cells = computed(() => props.items.map((item) => {
  const rule = activeRule(item);
  const pos = item.flagged ? { kind: 'none' } : limitPosition(item.value, rule);
  const selectable = props.selectable.includes(item.field);
  const hasValue = typeof item.value === 'number' && Number.isFinite(item.value);
  const below = pos.breach && typeof rule?.danger_min === 'number' && item.value < rule.danger_min;
  const sparkPoints = Array.isArray(item.spark) ? item.spark.filter((point) => point != null) : [];
  return {
    ...item,
    rule,
    pos,
    selectable,
    selected: selectable && item.field === props.modelValue,
    number: numberText(item.value, item.field),
    showUnit: Boolean(item.unit) && hasValue,
    limit: limitText(rule),
    // Said in words too, so the breach does not depend on colour.
    breachText: pos.breach ? (below ? 'di bawah baku mutu' : 'melewati baku mutu') : '',
    showSpark: !selectable && sparkPoints.length > 1,
  };
}));

function select(field) {
  if (field !== props.modelValue) emit('update:modelValue', field);
}

function cellAttrs(cell) {
  if (!cell.selectable) return {};
  return {
    type: 'button',
    'aria-pressed': cell.selected ? 'true' : 'false',
    ...(props.chartId ? { 'aria-controls': props.chartId } : {}),
    onClick: () => select(cell.field),
  };
}
</script>

<template>
  <!-- -mb-px/-mr-px inside overflow-hidden: the last row's and column's own
       borders fall outside, so every cell can draw border-b/border-r whatever
       the cell count. One row only from xl: with the sidebar open, md–lg
       leaves 464–720 px, too narrow for up to six values. -->
  <div class="overflow-hidden border-b border-line">
    <div class="-mb-px -mr-px grid grid-cols-2 md:grid-cols-3 xl:flex" role="group" aria-label="Parameter saat ini">
      <component
        :is="cell.selectable ? 'button' : 'div'"
        v-for="cell in cells"
        :key="cell.field"
        v-bind="cellAttrs(cell)"
        class="relative flex min-w-0 flex-col border-b border-r border-line px-4 py-3.5 text-left md:px-5 xl:flex-1"
        :class="cell.selectable
          ? ['cursor-pointer transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-[-2px] focus-visible:outline-primary', cell.selected ? 'bg-[#F2F8F8]' : 'hover:bg-[#F7FAFA]']
          : ''"
      >
        <span class="block text-[12.5px] font-semibold text-muted">{{ cell.label }}</span>
        <span class="mt-0.5 flex flex-wrap items-baseline gap-x-1 text-[24px] font-bold leading-tight tracking-tight tabular-nums" :class="cell.pos.breach ? 'text-breach' : 'text-ink'">
          <span>{{ cell.number }}</span>
          <small v-if="cell.showUnit" class="text-[12.5px] font-medium tracking-normal text-muted">{{ cell.unit }}</small>
          <span v-if="cell.breachText" class="sr-only">, {{ cell.breachText }}</span>
        </span>
        <span class="block text-xs" :class="cell.pos.breach ? 'font-semibold text-breach' : 'text-muted'">{{ cell.limit }}</span>
        <span v-if="cell.flagged" class="block text-xs text-muted">data diragukan</span>
        <span v-if="cell.pos.kind !== 'none'" class="relative mt-2 block h-1 rounded bg-line" aria-hidden="true">
          <span
            class="absolute inset-y-0 rounded"
            :class="cell.pos.breach ? 'bg-breach' : 'bg-primary'"
            :style="{ left: `${cell.pos.start}%`, width: `${Math.max(cell.pos.end - cell.pos.start, 2)}%` }"
          ></span>
          <template v-if="cell.pos.kind === 'range'">
            <span v-for="at in [cell.pos.minAt, cell.pos.maxAt]" :key="at" class="absolute -inset-y-0.5 w-px bg-muted" :style="{ left: `${at}%` }"></span>
          </template>
        </span>
        <span v-if="cell.showSpark" class="mt-2 block w-full max-w-[8rem]" aria-hidden="true">
          <Sparkline :points="cell.spark" :threshold="cell.rule?.danger_max ?? null" />
        </span>
        <span v-if="cell.selected" class="absolute inset-x-0 bottom-0 h-[3px] bg-primary" aria-hidden="true"></span>
      </component>
    </div>
  </div>
</template>
