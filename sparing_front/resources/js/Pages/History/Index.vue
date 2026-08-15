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
            :disabled="!historyData.length || exporting"
            class="px-3 py-2 rounded-md text-sm text-white bg-primary hover:bg-primary-dark transition-colors flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <i class="fas" :class="exporting ? 'fa-spinner fa-spin' : 'fa-file-excel'"></i>
            {{ exporting ? 'Mengekspor…' : 'Ekspor Excel' }}
          </button>
        </template>
      </PageHeader>

      <!-- Statistics Summary -->
      <div v-if="historyData.length > 0" class="grid grid-cols-2 md:grid-cols-4 gap-3 md:gap-4">
        <div class="bg-white border border-[#D7E0E1] rounded-lg p-4 flex items-center gap-4">
          <div class="w-10 h-10 rounded-xl bg-[#E4F1F2] flex items-center justify-center shrink-0">
            <i class="fas fa-database text-primary text-sm"></i>
          </div>
          <div>
            <div class="text-2xl font-bold text-ink">{{ pagination.totalItems }}</div>
            <div class="text-xs text-[#617377] mt-0.5">Total Data</div>
          </div>
        </div>

        <div class="bg-white border border-[#D7E0E1] rounded-lg p-4 flex items-center gap-4">
          <div class="w-10 h-10 rounded-xl bg-[#E6F2EC] flex items-center justify-center shrink-0">
            <i class="fas fa-calendar-alt text-success text-sm"></i>
          </div>
          <div>
            <div class="text-2xl font-bold text-ink">{{ dateDifferenceInDays }}</div>
            <div class="text-xs text-[#617377] mt-0.5">Hari Periode</div>
          </div>
        </div>

        <div class="bg-white border border-[#D7E0E1] rounded-lg p-4 flex items-center gap-4">
          <div class="w-10 h-10 rounded-xl bg-[#E4F1F2] flex items-center justify-center shrink-0">
            <i class="fas fa-chart-line text-primary text-sm"></i>
          </div>
          <div>
            <div class="text-2xl font-bold text-ink">{{ filters.fields.length }}</div>
            <div class="text-xs text-[#617377] mt-0.5">Parameter</div>
          </div>
        </div>

        <div class="bg-white border border-[#D7E0E1] rounded-lg p-4 flex items-center gap-4">
          <div class="w-10 h-10 rounded-xl bg-[#F7EFD9] flex items-center justify-center shrink-0">
            <i class="fas fa-map-marker-alt text-warning text-sm"></i>
          </div>
          <div class="min-w-0">
            <div class="text-sm font-bold text-ink truncate">{{ selectedSiteName }}</div>
            <div class="text-xs text-[#617377] mt-0.5">Lokasi Terpilih</div>
          </div>
        </div>
      </div>

      <!-- Filters Card -->
      <div class="bg-white border border-[#D7E0E1] rounded-lg p-4 md:p-5">
        <h3 class="text-[15px] font-bold text-ink mb-4">Filter Data</h3>

        <div class="grid grid-cols-1 md:grid-cols-4 gap-4 mb-4">
          <div>
            <label class="block text-[11.5px] font-semibold text-ink mb-1">Lokasi</label>
            <select v-model="filters.siteUid" class="w-full border border-[#C4D1D3] rounded-md p-2 text-sm">
              <option value="">Pilih Lokasi</option>
              <option v-for="site in sites" :key="site.uid" :value="site.uid">
                {{ site.name }} — {{ site.company_name }}
              </option>
            </select>
          </div>
          <div>
            <label class="block text-[11.5px] font-semibold text-ink mb-1">Dari Tanggal</label>
            <input v-model="filters.dateFrom" type="date" class="w-full border border-[#C4D1D3] rounded-md p-2 text-sm" />
          </div>
          <div>
            <label class="block text-[11.5px] font-semibold text-ink mb-1">Sampai Tanggal</label>
            <input v-model="filters.dateTo" type="date" class="w-full border border-[#C4D1D3] rounded-md p-2 text-sm" />
          </div>
          <div>
            <label class="block text-[11.5px] font-semibold text-ink mb-1">Interval</label>
            <select v-model="filters.interval" class="w-full border border-[#C4D1D3] rounded-md p-2 text-sm">
              <option value="raw">Data mentah (2 menit)</option>
              <option value="hourly">Rerata per jam</option>
              <option value="daily">Rerata harian</option>
            </select>
          </div>
        </div>

        <!-- Fields Selection with Checkboxes -->
        <div class="mb-4">
          <label class="block text-[11.5px] font-semibold text-ink mb-3">Parameter Sensor</label>
          <div class="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3">
            <label
              v-for="field in availableFields"
              :key="field.key"
              class="flex items-center gap-2 p-3 border border-[#D7E0E1] rounded-lg hover:bg-[#EEF2F3] cursor-pointer transition-colors"
              :class="filters.fields.includes(field.key) ? 'bg-[#E4F1F2] border-primary' : ''"
            >
              <input
                type="checkbox"
                :value="field.key"
                v-model="filters.fields"
                class="w-4 h-4 text-primary border-[#C4D1D3] rounded focus:ring-primary"
              />
              <span class="text-sm font-medium text-ink">{{ field.label }}</span>
            </label>
          </div>
        </div>

        <!-- Action Buttons -->
        <div class="flex gap-3 pt-4 border-t border-[#D7E0E1]">
          <button @click="applyFilters" class="px-3 py-2 rounded-md text-sm text-white bg-primary hover:bg-primary-dark transition-colors flex items-center gap-2">
            <i class="fas fa-search text-xs"></i>Terapkan Filter
          </button>
          <button @click="resetFilters" class="px-3 py-2 rounded-md border border-[#C4D1D3] text-sm text-ink hover:bg-[#EEF2F3] transition-colors flex items-center gap-2">
            <i class="fas fa-redo text-xs"></i>Reset
          </button>
        </div>
      </div>

      <!-- Data Table -->
      <div class="bg-white border border-[#D7E0E1] rounded-lg overflow-hidden">
        <div class="flex items-center justify-between px-4 py-3 border-b border-[#D7E0E1]">
          <h3 class="text-[15px] font-bold text-ink">Data Historis</h3>
          <div class="text-xs font-mono text-[#617377]">{{ pagination.totalItems }} data</div>
        </div>

        <div class="overflow-x-auto">
          <table class="w-full text-sm">
            <thead>
              <tr class="bg-[#EEF2F3] text-left text-[11.5px] text-[#617377] uppercase tracking-wide">
                <th class="px-4 py-2.5 font-semibold whitespace-nowrap">{{ filters.interval === 'daily' ? 'Tanggal' : 'Waktu' }}</th>
                <th v-for="field in selectedFields" :key="field.key" class="px-4 py-2.5 font-semibold whitespace-nowrap">
                  {{ field.label }} ({{ getSensorUnit(field.key) }})
                </th>
                <th v-if="isAggregated" class="px-4 py-2.5 font-semibold whitespace-nowrap">Jumlah Data</th>
                <th v-else class="px-4 py-2.5 font-semibold whitespace-nowrap">Validasi</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-[#EEF2F3]">
              <tr v-if="loading">
                <td :colspan="selectedFields.length + 2" class="px-4 py-8 text-center text-[#617377] text-sm">
                  <i class="fas fa-spinner fa-spin mr-2"></i>Memuat data…
                </td>
              </tr>
              <tr v-else-if="!historyData.length">
                <td :colspan="selectedFields.length + 2" class="px-4 py-8 text-center text-[#617377] text-sm">
                  Tidak ada data. Silakan pilih lokasi dan terapkan filter.
                </td>
              </tr>
              <tr v-else v-for="(row, ri) in historyData" :key="ri" class="hover:bg-[#F7FAFA] transition-colors">
                <td class="px-4 py-2.5 whitespace-nowrap">
                  <div class="text-ink">{{ formatDate(row.ts, false, siteTz) }}</div>
                  <div v-if="filters.interval !== 'daily'" class="text-[11.5px] text-[#617377] font-mono">{{ formatTime(row.ts, siteTz) }}</div>
                </td>

                <!-- Custom cells for sensor values with color coding.
                     Operational-status rows (op_status set) carry no readings — show a
                     single "Kalibrasi/Berhenti/Rusak" badge on the first value column
                     instead of a row of dashes. -->
                <td v-for="(field, fi) in selectedFields" :key="field.key" class="px-4 py-2.5">
                  <span
                    v-if="row.op_status != null && fi === 0"
                    class="px-2 py-1 rounded-full text-[11.5px] font-semibold"
                    :style="{ background: '#EAEEEF', color: '#6E7E82' }"
                    :title="'Kode kondisi KLHK: ' + row.op_status"
                  >
                    {{ opStatusLabel(row.op_status) }}
                  </span>
                  <span v-else-if="row.op_status != null" class="text-[#C4D1D3]">—</span>
                  <span
                    v-else
                    :class="['font-mono font-medium', getValueColorClass(field.key, row[field.key])]"
                  >
                    {{ row[field.key] != null ? formatNumber(row[field.key], 2) : '-' }}
                  </span>
                </td>

                <!-- Validasi column (raw mode only) -->
                <td v-if="isAggregated" class="px-4 py-2.5">
                  <span class="text-sm font-medium text-ink">{{ row.count ?? '-' }}</span>
                </td>
                <td v-else class="px-4 py-2.5">
                  <span
                    class="px-2 py-1 rounded-full text-[11.5px] font-semibold"
                    :style="row.quality_flag == null
                      ? { background: '#E6F2EC', color: '#1F7A4D' }
                      : { background: '#F7EFD9', color: '#9A6B00' }"
                  >
                    {{ row.quality_flag == null ? 'Valid' : 'Anomali' }}
                  </span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- Pagination -->
        <div class="flex items-center justify-between px-4 py-3 border-t border-[#D7E0E1] text-[12.5px] text-[#617377] flex-wrap gap-2">
          <span>{{ paginationLabel }}</span>
          <div class="flex items-center gap-2">
            <button
              type="button"
              class="px-2.5 py-1.5 rounded-md border border-[#C4D1D3] disabled:opacity-40"
              :disabled="pagination.currentPage <= 1 || loading"
              @click="handlePageChange(pagination.currentPage - 1)"
            >
              <i class="fas fa-chevron-left text-xs"></i>
            </button>
            <span class="text-ink font-semibold">{{ pagination.currentPage }} / {{ totalPages }}</span>
            <button
              type="button"
              class="px-2.5 py-1.5 rounded-md border border-[#C4D1D3] disabled:opacity-40"
              :disabled="pagination.currentPage >= totalPages || loading"
              @click="handlePageChange(pagination.currentPage + 1)"
            >
              <i class="fas fa-chevron-right text-xs"></i>
            </button>
          </div>
        </div>
      </div>

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
const exporting = ref(false);

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

// Pagination display helpers
const totalPages = computed(() => Math.max(1, Math.ceil(pagination.value.totalItems / pagination.value.perPage)));
const paginationLabel = computed(() => {
  if (!pagination.value.totalItems) return '0 dari 0 data';
  const start = (pagination.value.currentPage - 1) * pagination.value.perPage + 1;
  const end = Math.min(pagination.value.totalItems, pagination.value.currentPage * pagination.value.perPage);
  return `${start}–${end} dari ${pagination.value.totalItems} data`;
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
  if (value == null) return 'text-[#617377]';

  const status = getThresholdStatus(field, value);
  if (status === 'danger') return 'text-danger';
  if (status === 'warning') return 'text-warning';
  return 'text-ink';
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
// Export the FULL filtered range, not just the current page. The table is
// paginated (per_page rows loaded at a time), so historyData holds only one
// page — exporting that alone was the bug. Here we page through the whole range
// (backend caps per_page at 500) and build the workbook from every row.
const exportToExcel = async () => {
  if (!filters.value.siteUid) return;
  if (filters.value.interval !== 'raw' && !filters.value.dateFrom) {
    toast.warn('Pilih rentang tanggal untuk agregasi');
    return;
  }
  exporting.value = true;
  try {
    const dateToPlus = (() => {
      const d = new Date(filters.value.dateTo);
      d.setDate(d.getDate() + 1);        // include the whole end date
      return d.toISOString().split('T')[0];
    })();
    const base = {
      site_uid: filters.value.siteUid,
      date_from: filters.value.dateFrom,
      date_to: dateToPlus,
      fields: filters.value.fields.join(','),
      order: 'asc',                       // chronological for the export
      interval: filters.value.interval,
    };

    const PER_PAGE = 500;                 // backend maximum
    const all = [];
    let page = 1;
    let total = Infinity;
    while (all.length < total) {
      const res = await getData({ ...base, page, per_page: PER_PAGE });
      const items = res?.items || (Array.isArray(res) ? res : []);
      total = res?.total ?? items.length;
      all.push(...items);
      if (items.length < PER_PAGE) break; // last page reached
      page += 1;
      if (page > 200) break;              // hard safety cap (~100k rows)
    }

    if (!all.length) {
      toast.warn('Tidak ada data pada rentang yang dipilih');
      return;
    }

    const rows = all.map((row) => {
      const out = { 'Waktu (WIB)': formatDate(row.ts, true, siteTz.value) };
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
    const range = `${filters.value.dateFrom}_${filters.value.dateTo}`;
    XLSX.writeFile(wb, `sparing-${site}-${range}.xlsx`);
    toast.success(`${rows.length} baris diekspor`);
  } catch (e) {
    logger.error('Excel export failed:', e);
    toast.error('Gagal mengekspor data');
  } finally {
    exporting.value = false;
  }
};

// Initialize
onMounted(async () => {
  await loadSites();
  await loadHistoryData();
});
</script>
