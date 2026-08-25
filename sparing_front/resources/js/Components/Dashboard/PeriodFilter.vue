<script setup>
import { computed } from 'vue';

const props = defineProps({
  modelValue: { type: String, default: '24h' },
  customRange: { type: Object, default: () => ({ dateFrom: '', dateTo: '' }) },
  timezone: { type: String, default: 'Asia/Jakarta' },
});

const emit = defineEmits(['update:modelValue', 'update:customRange', 'apply-custom']);
const periods = [
  { value: '1h', label: '1h' }, { value: '6h', label: '6h' }, { value: '12h', label: '12h' },
  { value: 'today', label: 'Hari ini' }, { value: '24h', label: '24h' }, { value: '7d', label: '7d' }, { value: 'custom', label: 'Kustom' },
];
const dateFrom = computed(() => typeof props.customRange?.dateFrom === 'string' ? props.customRange.dateFrom : '');
const dateTo = computed(() => typeof props.customRange?.dateTo === 'string' ? props.customRange.dateTo : '');
const completeRange = computed(() => Boolean(dateFrom.value && dateTo.value));

function selectPeriod(value) { emit('update:modelValue', value); }
function updateRange(key, value) { emit('update:customRange', { dateFrom: dateFrom.value, dateTo: dateTo.value, [key]: value }); }
function applyCustom() { if (completeRange.value) emit('apply-custom'); }
</script>

<template>
  <section class="w-full" aria-label="Filter periode pemantauan">
    <div class="hidden w-full flex-wrap gap-1 sm:flex" role="group" aria-label="Pilih periode pemantauan">
      <button v-for="period in periods" :key="period.value" type="button" class="rounded-md border px-3 py-1.5 text-sm font-semibold transition-colors" :class="modelValue === period.value ? 'border-teal-700 bg-teal-700 text-white' : 'border-slate-300 bg-white text-slate-700 hover:border-teal-600 hover:bg-teal-50'" :aria-pressed="modelValue === period.value" @click="selectPeriod(period.value)">{{ period.label }}</button>
    </div>
    <label class="block sm:hidden">
      <span class="mb-1 block text-xs font-semibold text-slate-600">Pilih periode pemantauan</span>
      <select class="form-input py-2" :value="modelValue" aria-label="Pilih periode pemantauan" @change="selectPeriod($event.target.value)">
        <option v-for="period in periods" :key="period.value" :value="period.value">{{ period.label }}</option>
      </select>
    </label>
    <div v-if="modelValue === 'custom'" class="mt-3 grid w-full grid-cols-1 gap-3 rounded-md border border-slate-200 bg-slate-50 p-3 sm:grid-cols-[minmax(0,1fr)_minmax(0,1fr)_auto] sm:items-end">
      <label class="block text-sm font-semibold text-slate-700">Mulai
        <input class="form-input mt-1 py-2" type="datetime-local" :value="dateFrom" @input="updateRange('dateFrom', $event.target.value)">
      </label>
      <label class="block text-sm font-semibold text-slate-700">Selesai
        <input class="form-input mt-1 py-2" type="datetime-local" :value="dateTo" @input="updateRange('dateTo', $event.target.value)">
      </label>
      <button type="button" class="btn-primary px-4 py-2" :disabled="!completeRange" @click="applyCustom">Terapkan rentang</button>
      <p class="text-xs text-slate-500 sm:col-span-3">Zona waktu: {{ timezone }}</p>
    </div>
  </section>
</template>
