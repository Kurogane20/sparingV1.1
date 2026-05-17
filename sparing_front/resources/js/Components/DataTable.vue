<template>
  <div class="card overflow-hidden">

    <!-- Header -->
    <div class="flex items-center justify-between px-5 py-4 border-b border-slate-100">
      <h3 class="card-title">{{ title }}</h3>
      <div class="flex items-center gap-3">
        <slot name="actions"></slot>
      </div>
    </div>

    <!-- Loading skeleton -->
    <div v-if="loading" class="p-5 space-y-3">
      <div v-for="i in 5" :key="i" class="flex items-center gap-4">
        <div class="skeleton h-3.5 w-12 rounded"></div>
        <div class="skeleton h-3.5 flex-1 rounded"></div>
        <div class="skeleton h-3.5 w-20 rounded"></div>
        <div class="skeleton h-5 w-14 rounded-full"></div>
      </div>
    </div>

    <!-- Empty state -->
    <div v-else-if="!data || data.length === 0" class="py-14 text-center">
      <div class="w-12 h-12 mx-auto mb-3 rounded-xl bg-slate-50 border border-slate-100 flex items-center justify-center">
        <i class="fas fa-inbox text-slate-300 text-lg"></i>
      </div>
      <p class="text-sm font-medium text-slate-400">{{ emptyMessage }}</p>
    </div>

    <!-- Table -->
    <div v-else class="overflow-x-auto">
      <table class="w-full">
        <thead>
          <tr class="bg-slate-50 border-b border-slate-100">
            <th
              v-for="col in columns"
              :key="col.key"
              :class="[
                'px-5 py-3 text-[10px] font-bold text-slate-400 uppercase tracking-wider whitespace-nowrap',
                col.align === 'right' ? 'text-right' : 'text-left',
                col.cellClass || '',
              ]"
            >
              {{ col.label }}
            </th>
          </tr>
        </thead>
        <tbody class="divide-y divide-slate-50">
          <tr
            v-for="(row, index) in data"
            :key="row.id || index"
            class="hover:bg-blue-50/30 transition-colors"
          >
            <td
              v-for="col in columns"
              :key="col.key"
              :class="[
                'px-5 py-3.5 text-sm text-slate-700',
                col.align === 'right' ? 'text-right' : 'text-left',
                col.cellClass || '',
              ]"
            >
              <slot :name="`cell-${col.key}`" :row="row" :value="row[col.key]">
                <span v-if="col.format">{{ col.format(row[col.key], row) }}</span>
                <span v-else>{{ row[col.key] ?? '—' }}</span>
              </slot>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Pagination -->
    <div
      v-if="pagination && totalItems > 0"
      class="px-5 py-3.5 border-t border-slate-100 flex items-center justify-between"
    >
      <span class="text-xs text-slate-400 font-mono">{{ paginationText }}</span>
      <div class="flex items-center gap-1">
        <button
          @click="$emit('page-change', currentPage - 1)"
          :disabled="currentPage <= 1"
          class="w-7 h-7 rounded-lg border border-slate-200 flex items-center justify-center text-slate-400 hover:bg-slate-50 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
        >
          <i class="fas fa-chevron-left text-[10px]"></i>
        </button>

        <button
          v-for="page in visiblePages"
          :key="page"
          @click="typeof page === 'number' && $emit('page-change', page)"
          :class="[
            'w-7 h-7 rounded-lg text-xs font-medium transition-colors',
            page === currentPage
              ? 'bg-primary text-white shadow-sm'
              : page === '...'
              ? 'text-slate-400 cursor-default'
              : 'border border-slate-200 text-slate-600 hover:bg-slate-50',
          ]"
        >{{ page }}</button>

        <button
          @click="$emit('page-change', currentPage + 1)"
          :disabled="currentPage >= totalPages"
          class="w-7 h-7 rounded-lg border border-slate-200 flex items-center justify-center text-slate-400 hover:bg-slate-50 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
        >
          <i class="fas fa-chevron-right text-[10px]"></i>
        </button>
      </div>
    </div>

    <!-- Simple footer (no pagination) -->
    <div v-else-if="data && data.length > 0" class="px-5 py-3 border-t border-slate-100">
      <span class="text-xs text-slate-400 font-mono">{{ data.length }} data</span>
    </div>

  </div>
</template>

<script setup>
import { computed } from 'vue';

const props = defineProps({
  title:       { type: String,  default: 'Data' },
  subtitle:    { type: String,  default: '' },
  data:        { type: Array,   default: () => [] },
  columns:     { type: Array,   required: true },
  loading:     { type: Boolean, default: false },
  emptyMessage:{ type: String,  default: 'Tidak ada data' },
  pagination:  { type: Boolean, default: false },
  currentPage: { type: Number,  default: 1 },
  totalItems:  { type: Number,  default: 0 },
  perPage:     { type: Number,  default: 50 },
});

defineEmits(['page-change']);

const totalPages = computed(() => Math.max(1, Math.ceil(props.totalItems / props.perPage)));

const visiblePages = computed(() => {
  const total = totalPages.value;
  const cur   = props.currentPage;
  if (total <= 7) return Array.from({ length: total }, (_, i) => i + 1);

  if (cur <= 4)          return [1, 2, 3, 4, 5, '...', total];
  if (cur >= total - 3)  return [1, '...', total - 4, total - 3, total - 2, total - 1, total];
  return [1, '...', cur - 1, cur, cur + 1, '...', total];
});

const paginationText = computed(() => {
  const start = (props.currentPage - 1) * props.perPage + 1;
  const end   = Math.min(start + props.perPage - 1, props.totalItems);
  return `${start}–${end} dari ${props.totalItems}`;
});
</script>
