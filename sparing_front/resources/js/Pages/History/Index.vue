<template>
  <AppLayout>
    <div class="space-y-6">
      <!-- Page Header -->
      <PageHeader
        :crumb="['Beranda', 'Data', 'Riwayat Data']"
        title="Riwayat Data Pemantauan"
        subtitle="Filter dan ekspor data historis dari semua sensor"
      >
        <template #actions>
          <button
            @click="exportToExcel"
            :disabled="!historyData.length"
            class="btn-primary flex items-center gap-2 text-sm disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <i class="fas fa-file-excel"></i>Ekspor Excel
          </button>
        </template>
      </PageHeader>

      <!-- Statistics Summary -->
      <div v-if="historyData.length > 0" class="grid grid-cols-2 md:grid-cols-4 gap-3 md:gap-4">
        <div class="card p-4 flex items-center gap-4">
          <div class="w-10 h-10 rounded-xl bg-[#E4F1F2] flex items-center justify-center shrink-0">
            <i class="fas fa-database text-[#0E7C86] text-sm"></i>
          </div>
          <div>
            <div class="text-2xl font-bold text-slate-800">{{ pagination.totalItems }}</div>
            <div class="text-xs text-slate-400 mt-0.5">Total Data</div>
          </div>
        </div>

        <div class="card p-4 flex items-center gap-4">
          <div class="w-10 h-10 rounded-xl bg-emerald-50 flex items-center justify-center shrink-0">
            <i class="fas fa-calendar-alt text-emerald-600 text-sm"></i>
          </div>
          <div>
            <div class="text-2xl font-bold text-slate-800">{{ dateDifferenceInDays }}</div>
            <div class="text-xs text-slate-400 mt-0.5">Hari Periode</div>
          </div>
        </div>

        <div class="card p-4 flex items-center gap-4">
          <div class="w-10 h-10 rounded-xl bg-[#E4F1F2] flex items-center justify-center shrink-0">
            <i class="fas fa-chart-line text-[#0E7C86] text-sm"></i>
          </div>
          <div>
            <div class="text-2xl font-bold text-slate-800">{{ filters.fields.length }}</div>
            <div class="text-xs text-slate-400 mt-0.5">Parameter</div>
          </div>
        </div>

        <div class="card p-4 flex items-center gap-4">
          <div class="w-10 h-10 rounded-xl bg-amber-50 flex items-center justify-center shrink-0">
            <i class="fas fa-map-marker-alt text-amber-600 text-sm"></i>
          </div>
          <div class="min-w-0">
            <div class="text-sm font-bold text-slate-800 truncate">{{ selectedSiteName }}</div>
            <div class="text-xs text-slate-400 mt-0.5">Lokasi Terpilih</div>
          </div>
        </div>
      </div>

      <!-- Filters Card -->
      <div class="card p-5 md:p-6">
        <h3 class="card-title mb-4">Filter Data</h3>

        <div class="grid grid-cols-1 md:grid-cols-4 gap-4 mb-4">
          <div>
            <label class="block text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1.5">Lokasi</label>
            <select v-model="filters.siteUid" class="form-input text-sm">
              <option value="">Pilih Lokasi</option>
              <option v-for="site in sites" :key="site.uid" :value="site.uid">
                {{ site.name }} — {{ site.company_name }}
              </option>
            </select>
          </div>
          <div>
            <label class="block text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1.5">Dari Tanggal</label>
            <input v-model="filters.dateFrom" type="date" class="form-input text-sm" />
          </div>
          <div>
            <label class="block text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1.5">Sampai Tanggal</label>
            <input v-model="filters.dateTo" type="date" class="form-input text-sm" />
          </div>
          <div>
            <label class="block text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1.5">Interval</label>
            <select v-model="filters.interval" class="form-input text-sm">
              <option value="raw">Data mentah (2 menit)</option>
              <option value="hourly">Rerata per jam</option>
              <option value="daily">Rerata harian</option>
            </select>
          </div>
        </div>

        <!-- Fields Selection with Checkboxes -->
        <div class="mb-4">
          <label class="block text-xs font-semibold text-slate-500 uppercase tracking-wide mb-3">Parameter Sensor</label>
          <div class="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3">
            <label
              v-for="field in availableFields"
              :key="field.key"
              class="flex items-center gap-2 p-3 border border-slate-200 rounded-lg hover:bg-slate-50 cursor-pointer transition-colors"
              :class="filters.fields.includes(field.key) ? 'bg-primary bg-opacity-5 border-primary' : ''"
            >
              <input
                type="checkbox"
                :value="field.key"
                v-model="filters.fields"
                class="w-4 h-4 text-primary border-slate-300 rounded focus:ring-primary"
              />
              <span class="text-sm font-medium text-slate-700">{{ field.label }}</span>
            </label>
          </div>
        </div>

        <!-- Action Buttons -->
        <div class="flex gap-3 pt-4 border-t border-slate-100">
          <button @click="applyFilters" class="btn-primary flex items-center gap-2 text-sm">
            <i class="fas fa-search text-xs"></i>Terapkan Filter
          </button>
          <button @click="resetFilters" class="btn-secondary flex items-center gap-2 text-sm">
            <i class="fas fa-redo text-xs"></i>Reset
          </button>
        </div>
      </div>

      <!-- Data Table -->
      <DataTable
        title="Data Historis"
        :data="historyData"
        :columns="tableColumns"
        :loading="loading"
        :pagination="true"
        :current-page="pagination.currentPage"
        :total-items="pagination.totalItems"
        :per-page="pagination.perPage"
        empty-message="Tidak ada data. Silakan pilih lokasi dan terapkan filter."
        @page-change="handlePageChange"
      >
        <template #actions>
          <div class="text-xs font-mono text-slate-400">
            {{ pagination.totalItems }} data
          </div>
        </template>

        <!-- Custom cell for timestamp -->
        <template #cell-ts="{ value }">
          <div class="text-sm">
            <div>{{ formatDate(value, false, siteTz) }}</div>
            <div v-if="filters.interval !== 'daily'" class="text-xs text-slate-400 font-mono">{{ formatTime(value, siteTz) }}</div>
          </div>
        </template>

        <!-- Custom cells for sensor values with color coding.
             Operational-status rows (op_status set) carry no readings — show a
             single "Kalibrasi/Berhenti/Rusak" badge on the first value column
             instead of a row of dashes. -->
        <template v-for="(field, fi) in selectedFields" :key="`cell-${field.key}`" #[`cell-${field.key}`]="{ value, row }">
          <span
            v-if="row.op_status != null && fi === 0"
            class="px-2 py-1 rounded-full text-[11.5px] font-semibold"
            :style="{ background: '#EAEEEF', color: '#6E7E82' }"
            :title="'Kode kondisi KLHK: ' + row.op_status"
          >
            {{ opStatusLabel(row.op_status) }}
          </span>
          <span v-else-if="row.op_status != null" class="text-slate-300">—</span>
          <span
            v-else
            :class="['font-medium', getValueColorClass(field.key, value)]"
          >
            {{ value != null ? formatNumber(value, 2) : '-' }}
          </span>
        </template>

        <!-- Validasi column (raw mode only) -->
        <template #cell-quality_flag="{ value }">
          <span
            class="px-2 py-1 rounded-full text-[11.5px] font-semibold"
            :style="value == null
              ? { background: '#E6F2EC', color: '#1F7A4D' }
              : { background: '#F7EFD9', color: '#9A6B00' }"
          >
            {{ value == null ? 'Valid' : 'Anomali' }}
          </span>
        </template>

        <!-- Jumlah data column (aggregated mode only) -->
        <template #cell-count="{ value }">
          <span class="text-sm font-medium text-slate-700">{{ value ?? '-' }}</span>
        </template>
      </DataTable>

      <p v-if="filters.interval === 'raw'" class="text-xs text-[#617377] px-1">
        Nilai anomali dikecualikan dari perhitungan rerata namun tetap tersimpan untuk audit.
      </p>
    </div>
  </AppLayout>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import AppLayout from '@/Layouts/AppLayout.vue';
import PageHeader from '@/Components/PageHeader.vue';
import DataTable from '@/Components/DataTable.vue';
import { useApi } from '@/Composables/useApi';
import { useAuth } from '@/Composables/useAuth';
import { useToast } from '@/Composables/useToast';
import {
  formatDate,
  formatTime,
  formatNumber,
  getSensorName,
  getSensorUnit,
  getThresholdStatus,
  parseUTC,
} from '@/Utils/helpers';
import logger from '@/Utils/logger';
import * as XLSX from 'xlsx';

// Composables
const { getData, getSites } = useApi();
const { filterSitesByUser } = useAuth();
const toast = useToast();

// State
const sites = ref([]);
const historyData = ref([]);
const loading = ref(false);

// Filters
const filters = ref({
  siteUid: '',
  dateFrom: getDefaultDateFrom(),
  dateTo: getDefaultDateTo(),
  fields: ['ph', 'tss', 'cod', 'nh3n', 'debit', 'temp', 'voltage', 'current'],
  interval: 'raw',
});

// Pagination
const pagination = ref({
  currentPage: 1,
  totalItems: 0,
  perPage: 50,
});

// Available sensor fields - Water quality parameters only
const availableFields = [
  { key: 'ph', label: 'pH' },
  { key: 'tss', label: 'TSS' },
  { key: 'cod', label: 'COD' },
  { key: 'nh3n', label: 'NH3-N' },
  { key: 'debit', label: 'Debit' },
  { key: 'temp', label: 'Temperatur' },
  { key: 'voltage', label: 'Tegangan' },
  { key: 'current', label: 'Arus' },
];

// Computed: Selected site name
const selectedSiteName = computed(() => {
  const site = sites.value.find(s => s.uid === filters.value.siteUid);
  return site ? site.name : '-';
});

const siteTz = computed(() => {
  const site = sites.value.find(s => s.uid === filters.value.siteUid);
  return site?.timezone || 'Asia/Jakarta';
});

// Computed: Date difference in days
const dateDifferenceInDays = computed(() => {
  if (!filters.value.dateFrom || !filters.value.dateTo) return 0;
  const from = new Date(filters.value.dateFrom);
  const to = new Date(filters.value.dateTo);
  const diffTime = Math.abs(to - from);
  const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
  return diffDays;
});

// Computed table columns based on selected fields
const selectedFields = computed(() => {
  return availableFields.filter((f) => filters.value.fields.includes(f.key));
});

const isAggregated = computed(() => filters.value.interval !== 'raw');

// KLHK operational-status codes carried on op_status rows (intentional states,
// not sensor failures — rendered with the neutral offline palette).
const OP_STATUS_LABELS = { '-1': 'Berhenti', '-2': 'Kalibrasi', '-3': 'Rusak' };
const opStatusLabel = (code) => OP_STATUS_LABELS[String(code)] || `Kode ${code}`;

const tableColumns = computed(() => {
  const cols = [
    {
      key: 'ts',
      label: filters.value.interval === 'daily' ? 'Tanggal' : 'Waktu',
      cellClass: 'whitespace-nowrap',
    },
    ...selectedFields.value.map((field) => ({
      key: field.key,
      label: `${field.label} (${getSensorUnit(field.key)})`,
      format: 'number',
      decimals: 2,
    })),
  ];

  if (isAggregated.value) {
    cols.push({ key: 'count', label: 'Jumlah Data', cellClass: 'whitespace-nowrap' });
  } else {
    cols.push({ key: 'quality_flag', label: 'Validasi', cellClass: 'whitespace-nowrap' });
  }

  return cols;
});

// Get default date range (last 7 days)
function getDefaultDateFrom() {
  const date = new Date();
  date.setDate(date.getDate() - 7);
  return date.toISOString().split('T')[0];
}

function getDefaultDateTo() {
  return new Date().toISOString().split('T')[0];
}

// Get color class for sensor value based on threshold
const getValueColorClass = (field, value) => {
  if (value == null) return 'text-slate-400';

  const status = getThresholdStatus(field, value);
  if (status === 'danger') return 'text-red-600';
  if (status === 'warning') return 'text-yellow-600';
  return 'text-slate-800';
};

// Load sites list
const loadSites = async () => {
  try {
    const response = await getSites({ per_page: 100 });
    // Handle different possible response structures
    let sitesList = [];
    if (response && response.items) {
      sitesList = response.items;
    } else if (Array.isArray(response)) {
      sitesList = response;
    } else if (response && response.data) {
      sitesList = Array.isArray(response.data) ? response.data : [];
    } else {
      logger.warn('Unexpected sites API response format:', response);
    }

    // Filter sites based on user permissions
    sites.value = filterSitesByUser(sitesList);

    // Auto-select first site if none selected
    if (sites.value.length > 0 && !filters.value.siteUid) {
      filters.value.siteUid = sites.value[0].uid;
    }
  } catch (error) {
    logger.error('Failed to load sites:', error);
    sites.value = [];
  }
};

// Load history data from API
const loadHistoryData = async () => {
  if (!filters.value.siteUid) {
    historyData.value = [];
    return;
  }

  // Aggregated mode requires date_from — the backend 400s without it.
  // The page already defaults dateFrom on init/reset, but guard here too
  // in case it was ever cleared out from under an aggregated interval.
  if (filters.value.interval !== 'raw' && !filters.value.dateFrom) {
    toast.warn('Pilih rentang tanggal untuk agregasi');
    return;
  }

  loading.value = true;

  try {
    const params = {
      site_uid: filters.value.siteUid,
      date_from: filters.value.dateFrom,
      // Add 1 day to date_to to include all data from the end date
      date_to: (() => {
        const endDate = new Date(filters.value.dateTo);
        endDate.setDate(endDate.getDate() + 1);
        return endDate.toISOString().split('T')[0];
      })(),
      fields: filters.value.fields.join(','),
      page: pagination.value.currentPage,
      per_page: pagination.value.perPage,
      order: 'desc',
      interval: filters.value.interval,
    };

    const response = await getData(params);

    // Handle different possible response structures
    let dataList = [];
    let total = 0;

    if (response && response.items) {
      dataList = response.items;
      total = response.total || response.items.length;
    } else if (Array.isArray(response)) {
      dataList = response;
      total = response.length;
    } else if (response && response.data) {
      dataList = Array.isArray(response.data) ? response.data : [];
      total = response.total || dataList.length;
    } else {
      logger.warn('Unexpected history data API response format:', response);
    }

    historyData.value = dataList;
    pagination.value.totalItems = total;
  } catch (error) {
    logger.error('Failed to load history data:', error);
    historyData.value = [];
    pagination.value.totalItems = 0;
  } finally {
    loading.value = false;
  }
};

// Apply filters
const applyFilters = () => {
  pagination.value.currentPage = 1; // Reset to first page
  loadHistoryData();
};

// Reset filters to default
const resetFilters = () => {
  filters.value = {
    siteUid: sites.value[0]?.uid || '',
    dateFrom: getDefaultDateFrom(),
    dateTo: getDefaultDateTo(),
    fields: ['ph', 'tss', 'cod', 'nh3n', 'debit', 'temp', 'voltage', 'current'],
    interval: 'raw',
  };
  applyFilters();
};

// Handle page change
const handlePageChange = (page) => {
  pagination.value.currentPage = page;
  loadHistoryData();
};

// Export data to CSV
const exportToExcel = () => {
  if (!historyData.value.length) return;

  // Build labeled rows. Numeric parameters stay real numbers so Excel can sum/
  // chart them; empty values become blank cells (not "-").
  const rows = historyData.value.map((row) => {
    const out = {
      'Waktu (WIB)': formatDate(row.ts, true, siteTz.value),
    };
    selectedFields.value.forEach((field) => {
      const label = `${field.label} (${getSensorUnit(field.key)})`;
      const v = row[field.key];
      out[label] = v == null ? '' : v;
    });
    if (isAggregated.value) {
      out['Jumlah Data'] = row.count ?? '';
    } else {
      out['Validasi'] = row.quality_flag == null ? 'Valid' : 'Anomali';
    }
    return out;
  });

  const ws = XLSX.utils.json_to_sheet(rows);
  const wb = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(wb, ws, 'Riwayat Data');
  const site = filters.value.siteUid || 'data';
  const filename = `sparing-${site}-${new Date().toISOString().split('T')[0]}.xlsx`;
  XLSX.writeFile(wb, filename);
};

// Initialize
onMounted(async () => {
  await loadSites();
  await loadHistoryData();
});
</script>
