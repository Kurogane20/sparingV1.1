<template>
  <AppLayout>
    <PageHeader
      :crumb="['Beranda', 'Alarm']"
      title="Alarm & Riwayat Kejadian"
      subtitle="Seluruh alarm tercatat; penutupan wajib disertai catatan tindak lanjut."
    >
      <template #actions>
        <button
          type="button"
          class="px-3 py-2 rounded-md border border-[#D7E0E1] text-sm text-ink hover:bg-[#EEF2F3] transition-colors flex items-center gap-2"
          @click="load"
          :disabled="loading"
        >
          <i class="fas fa-rotate text-xs" :class="{ 'fa-spin': loading }"></i>
          Muat ulang
        </button>
      </template>
    </PageHeader>

    <!-- Filter bar -->
    <div class="bg-white border border-[#D7E0E1] rounded-lg p-4 mb-4">
      <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3 items-end">
        <div>
          <label class="block text-[11.5px] font-semibold text-ink mb-1">Tingkat</label>
          <select v-model="filters.threshold_type" class="w-full border border-[#C4D1D3] rounded-md p-2 text-sm">
            <option value="">Semua</option>
            <option value="danger">Bahaya</option>
            <option value="warning">Waspada</option>
          </select>
        </div>
        <div>
          <label class="block text-[11.5px] font-semibold text-ink mb-1">Kategori</label>
          <select v-model="filters.category" class="w-full border border-[#C4D1D3] rounded-md p-2 text-sm">
            <option value="">Semua</option>
            <option value="compliance">Baku mutu</option>
            <option value="data_quality">Kualitas data</option>
            <option value="logger">Logger</option>
          </select>
        </div>
        <div>
          <label class="block text-[11.5px] font-semibold text-ink mb-1">Lokasi</label>
          <select v-model="filters.site_uid" class="w-full border border-[#C4D1D3] rounded-md p-2 text-sm">
            <option value="">Semua</option>
            <option v-for="s in sites" :key="s.uid" :value="s.uid">{{ s.name }}</option>
          </select>
        </div>
        <div>
          <label class="block text-[11.5px] font-semibold text-ink mb-1">Status</label>
          <select v-model="filters.status" class="w-full border border-[#C4D1D3] rounded-md p-2 text-sm">
            <option value="active">Aktif</option>
            <option value="acknowledged">Dalam tindak lanjut</option>
            <option value="resolved">Selesai</option>
            <option value="all">Semua</option>
          </select>
        </div>
        <div>
          <button
            type="button"
            class="w-full px-3 py-2 rounded-md text-sm text-white bg-primary hover:bg-primary-dark transition-colors"
            @click="applyFilters"
          >
            Terapkan
          </button>
        </div>
      </div>
    </div>

    <!-- Table -->
    <div class="bg-white border border-[#D7E0E1] rounded-lg overflow-hidden">
      <div class="overflow-x-auto">
        <table class="w-full text-sm">
          <thead>
            <tr class="bg-[#EEF2F3] text-left text-[11.5px] text-[#617377] uppercase tracking-wide">
              <th class="px-4 py-2.5 font-semibold">No</th>
              <th class="px-4 py-2.5 font-semibold">Waktu</th>
              <th class="px-4 py-2.5 font-semibold">Lokasi</th>
              <th class="px-4 py-2.5 font-semibold">Kejadian</th>
              <th class="px-4 py-2.5 font-semibold">Nilai</th>
              <th class="px-4 py-2.5 font-semibold">Durasi</th>
              <th class="px-4 py-2.5 font-semibold">PIC</th>
              <th class="px-4 py-2.5 font-semibold">Status</th>
              <th class="px-4 py-2.5 font-semibold">Aksi</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-[#EEF2F3]">
            <tr v-if="loading">
              <td colspan="9" class="px-4 py-8 text-center text-[#617377] text-sm">
                <i class="fas fa-spinner fa-spin mr-2"></i>Memuat data…
              </td>
            </tr>
            <tr v-else-if="!alerts.length">
              <td colspan="9" class="px-4 py-8 text-center text-[#617377] text-sm">
                <i class="fas fa-check-circle text-success text-xl mb-2 block"></i>
                Tidak ada kejadian sesuai filter.
              </td>
            </tr>
            <tr v-else v-for="(a, idx) in alerts" :key="a.id" class="hover:bg-[#F7FAFA] transition-colors">
              <td class="px-4 py-2.5 text-[#617377]">{{ (page - 1) * perPage + idx + 1 }}</td>
              <td class="px-4 py-2.5 whitespace-nowrap">
                <div class="text-ink">{{ formatDate(a.triggered_at) }}</div>
                <div class="text-[11.5px] text-[#617377] font-mono">{{ formatTime(a.triggered_at) }}</div>
              </td>
              <td class="px-4 py-2.5 text-ink">{{ a.site_name }}</td>
              <td class="px-4 py-2.5 text-ink">
                <i v-if="a.category === 'data_quality'" class="fas fa-wrench text-[10px] text-[#617377] mr-1"></i>
                <i v-else-if="a.category === 'logger'" class="fas fa-hard-drive text-[10px] text-[#617377] mr-1"></i>
                {{ eventLabel(a) }}
              </td>
              <td class="px-4 py-2.5 font-mono text-ink">{{ formattedValue(a) }}</td>
              <td class="px-4 py-2.5 text-ink">{{ duration(a) }}</td>
              <td class="px-4 py-2.5 text-ink">{{ a.followup_by_name || '—' }}</td>
              <td class="px-4 py-2.5">
                <span class="px-2 py-1 rounded-full text-[11.5px] font-semibold" :style="statusStyle(a)">
                  {{ statusLabel(a) }}
                </span>
              </td>
              <td class="px-4 py-2.5">
                <div class="flex flex-wrap gap-1.5">
                  <template v-if="isOperator && a.status === 'active'">
                    <button class="px-2 py-1 rounded-md border border-[#C4D1D3] text-[11.5px] text-ink hover:bg-[#EEF2F3]" @click="openModal('followup', a)">
                      Tindak lanjut
                    </button>
                    <button class="px-2 py-1 rounded-md text-[11.5px] text-white bg-primary hover:bg-primary-dark" @click="openModal('resolve', a)">
                      Selesaikan
                    </button>
                  </template>
                  <template v-else-if="isOperator && a.status === 'acknowledged'">
                    <button class="px-2 py-1 rounded-md text-[11.5px] text-white bg-primary hover:bg-primary-dark" @click="openModal('resolve', a)">
                      Selesaikan
                    </button>
                  </template>
                  <template v-else-if="a.status === 'resolved'">
                    <button class="px-2 py-1 rounded-md border border-[#C4D1D3] text-[11.5px] text-ink hover:bg-[#EEF2F3]" @click="openModal('view', a)">
                      Catatan
                    </button>
                  </template>
                  <span v-else class="text-[11.5px] text-[#617377]">—</span>
                </div>
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
            :disabled="page <= 1 || loading"
            @click="changePage(page - 1)"
          >
            <i class="fas fa-chevron-left text-xs"></i>
          </button>
          <span class="text-ink font-semibold">{{ page }} / {{ totalPages }}</span>
          <button
            type="button"
            class="px-2.5 py-1.5 rounded-md border border-[#C4D1D3] disabled:opacity-40"
            :disabled="page >= totalPages || loading"
            @click="changePage(page + 1)"
          >
            <i class="fas fa-chevron-right text-xs"></i>
          </button>
        </div>
      </div>
    </div>

    <p class="text-[11.5px] text-[#617377] mt-3">
      Catatan tindak lanjut wajib diisi sebelum alarm dapat ditutup (SOP-ENV-014).
    </p>

    <AlertFollowupModal
      :open="modal.open && modal.mode !== 'view'"
      :mode="modal.mode"
      :alert="modal.alert"
      @close="closeModal"
      @submit="handleSubmit"
    />

    <!-- Read-only note viewer -->
    <div v-if="modal.open && modal.mode === 'view'" class="fixed inset-0 z-50 flex items-center justify-center bg-ink/40 p-4" @click.self="closeModal">
      <div class="bg-white rounded-lg border border-[#D7E0E1] w-full max-w-md p-5">
        <h3 class="text-[15px] font-bold text-ink mb-1">Catatan penyelesaian</h3>
        <p v-if="modal.alert" class="text-[12.5px] text-[#617377] mb-3">
          {{ modal.alert.site_name }} · {{ eventLabel(modal.alert) }}
        </p>
        <div class="bg-[#EEF2F3] rounded-md p-3 text-sm text-ink min-h-[64px] whitespace-pre-wrap">
          {{ modal.alert?.followup_note || 'Tidak ada catatan.' }}
        </div>
        <p class="text-[11.5px] text-[#617377] mt-2">
          Oleh {{ modal.alert?.followup_by_name || '—' }} · {{ modal.alert?.resolved_at ? formatDate(modal.alert.resolved_at) + ' ' + formatTime(modal.alert.resolved_at) : '—' }}
        </p>
        <div class="flex justify-end mt-4">
          <button class="px-3 py-2 rounded-md border border-[#C4D1D3] text-sm" @click="closeModal">Tutup</button>
        </div>
      </div>
    </div>
  </AppLayout>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue';
import AppLayout from '@/Layouts/AppLayout.vue';
import PageHeader from '@/Components/PageHeader.vue';
import AlertFollowupModal from '@/Components/AlertFollowupModal.vue';
import { useApi } from '@/Composables/useApi';
import { useAuth } from '@/Composables/useAuth';
import { useToast } from '@/Composables/useToast';
import { formatDate, formatTime, getSensorUnit } from '@/Utils/helpers';

const { getAlerts, getSites, followupAlert, resolveAlert } = useApi();
const { isOperator } = useAuth();
const toast = useToast();

const FIELD_LABELS = {
  ph: 'pH', tss: 'TSS', cod: 'COD', nh3n: 'NH3-N', temp: 'Temperatur',
  debit: 'Debit Air', noise: 'Kebisingan', pm25: 'PM2.5', pm10: 'PM10',
  device_offline: 'Perangkat Offline',
};
const ANOMALY_LABELS = {
  implausible: 'Nilai tidak wajar', flatline: 'Sensor nyangkut',
  spike: 'Lonjakan', drift: 'Drift kalibrasi',
};
const SENSOR_NAMES = { ph: 'pH', tss: 'TSS', debit: 'Debit', cod: 'COD', nh3n: 'NH3-N' };

function eventLabel(a) {
  if (a.category === 'logger') {
    if (a.field === 'logger_down') return 'Logger tidak terjangkau';
    if (a.field && a.field.startsWith('sensor_')) {
      const name = SENSOR_NAMES[a.field.slice(7)] || a.field.slice(7).toUpperCase();
      return `Sensor ${name} gagal dibaca`;
    }
    return 'Kejadian logger';
  }
  const field = FIELD_LABELS[a.field] || a.field;
  if (a.category === 'data_quality') {
    return `${field} — ${ANOMALY_LABELS[a.anomaly_type] || 'Kualitas data'}`;
  }
  return `${field} melampaui baku mutu`;
}

function formattedValue(a) {
  if (a.field === 'device_offline' || a.value == null) return '—';
  const unit = getSensorUnit(a.field);
  return `${Number(a.value).toFixed(2)}${unit ? ' ' + unit : ''}`;
}

function duration(a) {
  if (!a.triggered_at) return '—';
  const start = new Date(a.triggered_at.endsWith('Z') ? a.triggered_at : a.triggered_at + 'Z');
  const end = a.resolved_at
    ? new Date(a.resolved_at.endsWith('Z') ? a.resolved_at : a.resolved_at + 'Z')
    : new Date();
  const diffMs = Math.max(0, end - start);
  const minutes = Math.floor(diffMs / 60000);
  if (minutes < 60) return `${minutes} mnt`;
  const hours = Math.floor(minutes / 60);
  const rem = minutes % 60;
  return `${hours} j ${rem} m`;
}

const STATUS_STYLES = {
  active_danger: { background: '#F7E4E4', color: '#B03030' },
  active_warning: { background: '#F7EFD9', color: '#9A6B00' },
  acknowledged: { background: '#E4F1F2', color: '#0A5A62' },
  resolved: { background: '#E6F2EC', color: '#1F7A4D' },
};

function statusStyle(a) {
  if (a.status === 'active') {
    return a.threshold_type === 'danger' ? STATUS_STYLES.active_danger : STATUS_STYLES.active_warning;
  }
  if (a.status === 'acknowledged') return STATUS_STYLES.acknowledged;
  if (a.status === 'resolved') return STATUS_STYLES.resolved;
  return { background: '#EAEEEF', color: '#6E7E82' };
}

function statusLabel(a) {
  if (a.status === 'active') return 'Aktif';
  if (a.status === 'acknowledged') return 'Dalam tindak lanjut';
  if (a.status === 'resolved') return 'Selesai';
  return a.status;
}

const filters = reactive({
  threshold_type: '',
  category: '',
  site_uid: '',
  status: 'active',
});

const sites = ref([]);
const alerts = ref([]);
const total = ref(0);
const page = ref(1);
const perPage = ref(20);
const loading = ref(false);

const totalPages = computed(() => Math.max(1, Math.ceil(total.value / perPage.value)));
const paginationLabel = computed(() => {
  if (!total.value) return '0 dari 0 kejadian';
  const start = (page.value - 1) * perPage.value + 1;
  const end = Math.min(total.value, page.value * perPage.value);
  return `${start}–${end} dari ${total.value} kejadian`;
});

async function loadSites() {
  try {
    const res = await getSites({ per_page: 100 });
    sites.value = res?.items || (Array.isArray(res) ? res : []);
  } catch {
    sites.value = [];
  }
}

async function load() {
  loading.value = true;
  try {
    const params = { page: page.value, per_page: perPage.value };
    if (filters.threshold_type) params.threshold_type = filters.threshold_type;
    if (filters.category) params.category = filters.category;
    if (filters.site_uid) params.site_uid = filters.site_uid;
    if (filters.status && filters.status !== 'all') params.status = filters.status;
    const res = await getAlerts(params);
    alerts.value = res?.items || [];
    total.value = res?.total ?? alerts.value.length;
  } catch (err) {
    toast.error(err.response?.data?.detail || 'Gagal memuat data alarm');
    alerts.value = [];
    total.value = 0;
  } finally {
    loading.value = false;
  }
}

function applyFilters() {
  page.value = 1;
  load();
}

function changePage(p) {
  if (p < 1 || p > totalPages.value) return;
  page.value = p;
  load();
}

const modal = reactive({ open: false, mode: 'followup', alert: null });

function openModal(mode, alert) {
  modal.mode = mode;
  modal.alert = alert;
  modal.open = true;
}

function closeModal() {
  modal.open = false;
  modal.alert = null;
}

async function handleSubmit({ note }) {
  const alert = modal.alert;
  if (!alert) return;
  try {
    if (modal.mode === 'resolve') {
      await resolveAlert(alert.id, note);
      toast.success('Alarm berhasil diselesaikan');
    } else {
      await followupAlert(alert.id, note);
      toast.success('Catatan tindak lanjut tersimpan');
    }
    closeModal();
    load();
  } catch (err) {
    toast.error(err.response?.data?.detail || 'Gagal menyimpan tindak lanjut');
  }
}

onMounted(() => {
  loadSites();
  load();
});
</script>
