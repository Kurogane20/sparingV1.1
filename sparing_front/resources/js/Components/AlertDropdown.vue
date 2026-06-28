<template>
  <div class="relative" ref="dropdownRef">
    <!-- Bell button -->
    <button
      @click="toggleDropdown"
      class="relative w-9 h-9 rounded-lg hover:bg-slate-100 flex items-center justify-center transition-colors"
      aria-label="Notifikasi"
    >
      <i class="fas fa-bell text-slate-500 text-sm"></i>
      <span
        v-if="activeCount > 0"
        class="absolute -top-0.5 -right-0.5 min-w-[18px] h-[18px] bg-red-500 text-white text-[10px] font-bold rounded-full flex items-center justify-center px-1 leading-none"
      >
        {{ activeCount > 99 ? '99+' : activeCount }}
      </span>
    </button>

    <!-- Dropdown panel -->
    <Transition name="dropdown">
      <div
        v-if="open"
        class="absolute right-0 top-full mt-2 w-80 bg-white rounded-xl shadow-lg border border-slate-100 z-50 overflow-hidden"
      >
        <!-- Header -->
        <div class="flex items-center justify-between px-4 py-3 border-b border-slate-100">
          <span class="text-sm font-bold text-slate-800">Notifikasi</span>
          <span v-if="activeCount > 0" class="text-xs font-mono text-red-500">{{ activeCount }} aktif</span>
        </div>

        <!-- Loading -->
        <div v-if="loading" class="px-4 py-6 text-center text-sm text-slate-400">
          <i class="fas fa-spinner fa-spin mr-2"></i>Memuat...
        </div>

        <!-- Empty -->
        <div v-else-if="!alerts.length" class="px-4 py-6 text-center text-sm text-slate-400">
          <i class="fas fa-check-circle text-emerald-400 text-2xl mb-2 block"></i>
          Tidak ada alert aktif
        </div>

        <!-- Alert list -->
        <div v-else class="divide-y divide-slate-50 max-h-80 overflow-y-auto">
          <div
            v-for="alert in alerts"
            :key="alert.id"
            class="px-4 py-3 hover:bg-slate-50 transition-colors"
            :class="alert.threshold_type === 'danger' ? 'border-l-2 border-red-500' : 'border-l-2 border-amber-400'"
          >
            <div class="flex items-start justify-between gap-2">
              <div class="flex-1 min-w-0">
                <div class="text-xs font-bold text-slate-700 truncate">{{ alert.site_name }}</div>
                <div class="text-sm font-semibold mt-0.5" :class="alert.threshold_type === 'danger' ? 'text-red-600' : 'text-amber-600'">
                  <i v-if="isDataQuality(alert)" class="fas fa-wrench text-[10px] mr-1"></i>
                  {{ getAlertTitle(alert) }}:
                  <span class="font-mono">{{ alert.field === 'device_offline' ? 'Offline' : formatAlertValue(alert) }}</span>
                </div>
                <div v-if="isDataQuality(alert) && alert.detail" class="text-[11px] text-slate-400 mt-0.5">{{ alert.detail }}</div>
                <div class="text-xs text-slate-400 mt-0.5 font-mono">{{ getRelativeTime(alert.triggered_at) }}</div>
              </div>
              <button
                @click.stop="handleAcknowledge(alert.id)"
                class="shrink-0 text-[10px] font-bold px-2 py-1 rounded border border-slate-200 text-slate-500 hover:bg-slate-100 transition-colors mt-0.5"
              >
                ACK
              </button>
            </div>
          </div>
        </div>

        <!-- Footer -->
        <div v-if="alerts.length" class="px-4 py-2.5 border-t border-slate-100 text-center">
          <span class="text-xs text-slate-400">Klik ACK untuk konfirmasi tiap alert</span>
        </div>
      </div>
    </Transition>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue';
import { useApi } from '@/Composables/useApi';
import { getRelativeTime, getSensorUnit } from '@/Utils/helpers';

const { getAlertCount, getAlerts, acknowledgeAlert } = useApi();

const open = ref(false);
const loading = ref(false);
const activeCount = ref(0);
const alerts = ref([]);
const dropdownRef = ref(null);

const FIELD_LABELS = {
  ph: 'pH', tss: 'TSS', cod: 'COD', nh3n: 'NH3-N', temp: 'Temperatur',
  debit: 'Debit Air', noise: 'Kebisingan', pm25: 'PM2.5', pm10: 'PM10',
  device_offline: 'Perangkat Offline',
};

const getFieldLabel = (field) => FIELD_LABELS[field] || field.toUpperCase();

const ANOMALY_LABELS = {
  implausible: 'Nilai tidak wajar', flatline: 'Sensor nyangkut',
  spike: 'Lonjakan', drift: 'Drift kalibrasi',
};
const isDataQuality = (a) => a.category === 'data_quality';
const getAlertTitle = (a) => isDataQuality(a)
  ? `${getFieldLabel(a.field)} — ${ANOMALY_LABELS[a.anomaly_type] || 'Kualitas data'}`
  : `${getFieldLabel(a.field)}`;

const formatAlertValue = (alert) => {
  const unit = getSensorUnit(alert.field);
  return `${Number(alert.value).toFixed(2)}${unit ? ' ' + unit : ''}`;
};

const fetchCount = async () => {
  try {
    const res = await getAlertCount('active');
    activeCount.value = res?.count ?? 0;
  } catch {
    // silent
  }
};

const fetchAlerts = async () => {
  loading.value = true;
  try {
    const res = await getAlerts({ status: 'active', limit: 20 });
    alerts.value = Array.isArray(res) ? res : [];
    activeCount.value = alerts.value.length;
  } catch {
    alerts.value = [];
  } finally {
    loading.value = false;
  }
};

const toggleDropdown = () => {
  open.value = !open.value;
  if (open.value) fetchAlerts();
};

const handleAcknowledge = async (alertId) => {
  try {
    await acknowledgeAlert(alertId);
    alerts.value = alerts.value.filter(a => a.id !== alertId);
    activeCount.value = Math.max(0, activeCount.value - 1);
  } catch {
    // silent
  }
};

const handleOutsideClick = (e) => {
  if (dropdownRef.value && !dropdownRef.value.contains(e.target)) {
    open.value = false;
  }
};

let pollInterval;

onMounted(() => {
  fetchCount();
  pollInterval = setInterval(fetchCount, 30000);
  document.addEventListener('click', handleOutsideClick);
});

onUnmounted(() => {
  clearInterval(pollInterval);
  document.removeEventListener('click', handleOutsideClick);
});
</script>

<style scoped>
.dropdown-enter-active { transition: all 0.15s ease-out; }
.dropdown-leave-active { transition: all 0.1s ease-in; }
.dropdown-enter-from   { opacity: 0; transform: translateY(-6px) scale(0.97); }
.dropdown-leave-to     { opacity: 0; transform: translateY(-4px) scale(0.97); }
</style>
