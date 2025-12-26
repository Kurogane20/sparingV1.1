<template>
  <div class="card-gradient rounded-2xl overflow-hidden">
    <!-- Header -->
    <div class="px-6 py-4 border-b border-gray-100">
      <div class="flex justify-between items-center">
        <div>
          <h3 class="text-lg font-semibold text-gray-900">{{ title }}</h3>
          <p v-if="subtitle" class="text-sm text-gray-500 mt-0.5">{{ subtitle }}</p>
        </div>
        <slot name="header-actions"></slot>
      </div>
    </div>

    <!-- Loading State -->
    <div v-if="loading" class="p-6">
      <div class="space-y-4">
        <div v-for="i in 5" :key="i" class="flex items-center gap-4">
          <div class="skeleton h-4 w-16 rounded"></div>
          <div class="skeleton h-4 flex-1 rounded"></div>
          <div class="skeleton h-4 w-24 rounded"></div>
          <div class="skeleton h-6 w-16 rounded-full"></div>
        </div>
      </div>
    </div>

    <!-- Empty State -->
    <div v-else-if="!data || data.length === 0" class="p-12 text-center">
      <div class="w-16 h-16 mx-auto mb-4 rounded-2xl bg-gray-100 flex items-center justify-center">
        <i class="fas fa-inbox text-2xl text-gray-400"></i>
      </div>
      <p class="text-gray-500 font-medium">{{ emptyMessage }}</p>
    </div>

    <!-- Data Table -->
    <div v-else class="overflow-x-auto">
      <table class="data-table">
        <thead>
          <tr>
            <th
              v-for="col in columns"
              :key="col.key"
              :class="['px-6 py-4', col.align === 'right' ? 'text-right' : 'text-left']"
            >
              {{ col.label }}
            </th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="(row, index) in data"
            :key="row.id || index"
            class="group hover:bg-gradient-to-r hover:from-primary/5 hover:to-transparent"
          >
            <td
              v-for="col in columns"
              :key="col.key"
              :class="['px-6 py-4 text-sm', col.align === 'right' ? 'text-right' : 'text-left']"
            >
              <!-- Custom slot for cell content -->
              <slot :name="`cell-${col.key}`" :row="row" :value="row[col.key]">
                <span v-if="col.format" class="text-gray-700">
                  {{ col.format(row[col.key], row) }}
                </span>
                <span v-else class="text-gray-700">
                  {{ row[col.key] ?? '-' }}
                </span>
              </slot>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Footer -->
    <div v-if="showPagination && data && data.length > 0" class="px-6 py-4 border-t border-gray-100">
      <div class="flex justify-between items-center text-sm text-gray-500">
        <span>Menampilkan {{ data.length }} data</span>
        <slot name="pagination"></slot>
      </div>
    </div>
  </div>
</template>

<script setup>
defineProps({
  title: {
    type: String,
    default: 'Data Table',
  },
  subtitle: {
    type: String,
    default: '',
  },
  data: {
    type: Array,
    default: () => [],
  },
  columns: {
    type: Array,
    required: true,
  },
  loading: {
    type: Boolean,
    default: false,
  },
  emptyMessage: {
    type: String,
    default: 'Tidak ada data',
  },
  showPagination: {
    type: Boolean,
    default: true,
  },
});
</script>

<style scoped>
.data-table {
  @apply w-full;
}

.data-table thead {
  @apply bg-gradient-to-r from-gray-50 to-gray-100/50;
}

.data-table th {
  @apply text-xs font-semibold text-gray-500 uppercase tracking-wider;
}

.data-table tbody tr {
  @apply border-b border-gray-50 transition-all duration-200;
}

.data-table tbody tr:last-child {
  @apply border-b-0;
}
</style>
