<template>
  <AppLayout>
    <PageHeader
      :crumb="['Beranda', 'Logger']"
      title="Monitoring Logger"
      subtitle="Status perangkat logger di tiap lokasi — heartbeat, kesehatan sensor, dan riwayat kejadian."
    >
      <template #actions>
        <button
          type="button"
          class="px-3 py-2 rounded-md border border-[#D7E0E1] text-sm text-ink hover:bg-[#EEF2F3] transition-colors flex items-center gap-2"
          @click="refreshAll"
          :disabled="statusLoading"
        >
          <i class="fas fa-rotate text-xs" :class="{ 'fa-spin': statusLoading }"></i>
          Muat ulang
        </button>
      </template>
    </PageHeader>

    <!-- KPI row -->
    <div class="grid grid-cols-1 md:grid-cols-3 gap-3 mb-4">
      <div class="bg-white border border-[#D7E0E1] rounded-lg p-4">
        <div class="text-[11px] text-[#617377] uppercase font-bold">Logger hidup</div>
        <div class="font-mono text-2xl text-ink mt-1">{{ aliveCount }}/{{ totalCount }}</div>
      </div>
      <div class="bg-white border border-[#D7E0E1] rounded-lg p-4">
        <div class="text-[11px] text-[#617377] uppercase font-bold">Alarm logger aktif</div>
        <div class="font-mono text-2xl text-ink mt-1">{{ activeLoggerAlarms }}</div>
      </div>
      <div class="bg-white border border-[#D7E0E1] rounded-lg p-4">
        <div class="text-[11px] text-[#617377] uppercase font-bold">Event 24 jam terakhir</div>
        <div class="font-mono text-2xl text-ink mt-1">{{ events24h }}</div>
      </div>
    </div>

    <!-- Per-site status table -->
    <div class="bg-white border border-[#D7E0E1] rounded-lg overflow-hidden mb-4">
      <div class="overflow-x-auto">
        <table class="w-full text-sm">
          <thead>
            <tr class="bg-[#EEF2F3] text-left text-[11.5px] text-[#617377] uppercase tracking-wide">
              <th class="px-4 py-2.5 font-semibold">Lokasi</th>
              <th class="px-4 py-2.5 font-semibold">Status</th>
              <th class="px-4 py-2.5 font-semibold">Heartbeat</th>
              <th class="px-4 py-2.5 font-semibold">Uptime</th>
              <th class="px-4 py-2.5 font-semibold">Versi</th>
              <th class="px-4 py-2.5 font-semibold">Status Operasional</th>
              <th class="px-4 py-2.5 font-semibold">Sensor</th>
              <th class="px-4 py-2.5 font-semibold">Internet</th>
              <th class="px-4 py-2.5 font-semibold">Buffer</th>
              <th class="px-4 py-2.5 font-semibold">Terkirim</th>
              <th class="px-4 py-2.5 font-semibold">Resource</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-[#EEF2F3]">
            <tr v-if="statusLoading">
              <td colspan="11" class="px-4 py-8 text-center text-[#617377] text-sm">
                <i class="fas fa-spinner fa-spin mr-2"></i>Memuat data…
              </td>
            </tr>
            <tr v-else-if="!statuses.length">
              <td colspan="11" class="px-4 py-8 text-center text-[#617377] text-sm">
                Belum ada logger yang mengirim heartbeat.
              </td>
            </tr>
            <tr
              v-else
              v-for="row in statuses"
              :key="row.site_id"
              class="hover:bg-[#F7FAFA] transition-colors cursor-pointer"
              :class="{ 'bg-[#E4F1F2]': selectedSiteUid === row.site_uid }"
              @click="selectSite(row.site_uid)"
            >
              <td class="px-4 py-2.5 text-ink font-medium">{{ row.site_name }}</td>
              <td class="px-4 py-2.5">
                <span class="px-2 py-1 rounded-full text-[11.5px] font-semibold" :style="aliveStyle(row.state)">
                  {{ row.state === 'alive' ? 'Hidup' : 'Mati' }}
                </span>
                <div v-if="row.state !== 'alive'" class="text-[11px] text-[#617377] mt-0.5">
                  {{ getRelativeTime(row.state_since) }}
                </div>
              </td>
              <td class="px-4 py-2.5 text-ink whitespace-nowrap">
                {{ row.last_heartbeat_at ? getRelativeTime(row.last_heartbeat_at) : '—' }}
              </td>
              <td class="px-4 py-2.5 font-mono text-ink">{{ fmtUptime(row.uptime_s) }}</td>
              <td class="px-4 py-2.5 text-ink">{{ row.logger_version || '—' }}</td>
              <td class="px-4 py-2.5">
                <span class="px-2 py-1 rounded-full text-[11.5px] font-semibold" :style="opStatusStyle(row.op_status)">
                  {{ opStatusLabel(row.op_status) }}
                </span>
              </td>
              <td class="px-4 py-2.5">
                <div class="flex items-center gap-1.5">
                  <span
                    v-for="s in sensorDots(row)"
                    :key="s.key"
                    class="w-2.5 h-2.5 rounded-full"
                    :class="s.class"
                    :title="s.title"
                  ></span>
                </div>
              </td>
              <td class="px-4 py-2.5">
                <span class="px-2 py-1 rounded-full text-[11.5px] font-semibold" :style="internetStyle(row.internet_ok)">
                  {{ row.internet_ok ? 'Online' : 'Offline' }}
                </span>
              </td>
              <td class="px-4 py-2.5 font-mono text-ink">{{ row.buffer_depth ?? '—' }}</td>
              <td class="px-4 py-2.5 font-mono text-ink">{{ row.daily_sent ?? '—' }}</td>
              <td class="px-4 py-2.5">
                <div class="flex flex-col gap-1 w-32">
                  <div v-if="row.cpu_temp != null" class="flex items-center gap-1.5">
                    <span class="text-[10px] text-[#617377] w-8 shrink-0">Suhu</span>
                    <div class="h-1.5 rounded bg-[#E5EDED] flex-1 overflow-hidden">
                      <div class="h-full bg-primary rounded" :style="{ width: pct(row.cpu_temp, 80) + '%' }"></div>
                    </div>
                    <span class="text-[10px] font-mono text-[#617377] w-9 text-right shrink-0">{{ Math.round(row.cpu_temp) }}°C</span>
                  </div>
                  <div v-if="row.cpu_pct != null" class="flex items-center gap-1.5">
                    <span class="text-[10px] text-[#617377] w-8 shrink-0">CPU</span>
                    <div class="h-1.5 rounded bg-[#E5EDED] flex-1 overflow-hidden">
                      <div class="h-full bg-primary rounded" :style="{ width: pct(row.cpu_pct, 100) + '%' }"></div>
                    </div>
                    <span class="text-[10px] font-mono text-[#617377] w-9 text-right shrink-0">{{ Math.round(row.cpu_pct) }}%</span>
                  </div>
                  <div v-if="row.mem_pct != null" class="flex items-center gap-1.5">
                    <span class="text-[10px] text-[#617377] w-8 shrink-0">RAM</span>
                    <div class="h-1.5 rounded bg-[#E5EDED] flex-1 overflow-hidden">
                      <div class="h-full bg-primary rounded" :style="{ width: pct(row.mem_pct, 100) + '%' }"></div>
                    </div>
                    <span class="text-[10px] font-mono text-[#617377] w-9 text-right shrink-0">{{ Math.round(row.mem_pct) }}%</span>
                  </div>
                  <div v-if="row.disk_pct != null" class="flex items-center gap-1.5">
                    <span class="text-[10px] text-[#617377] w-8 shrink-0">Disk</span>
                    <div class="h-1.5 rounded bg-[#E5EDED] flex-1 overflow-hidden">
                      <div class="h-full bg-primary rounded" :style="{ width: pct(row.disk_pct, 100) + '%' }"></div>
                    </div>
                    <span class="text-[10px] font-mono text-[#617377] w-9 text-right shrink-0">{{ Math.round(row.disk_pct) }}%</span>
                  </div>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Event timeline -->
    <div class="mb-2 flex items-center justify-between flex-wrap gap-2">
      <h3 class="text-[15px] font-bold text-ink">Riwayat Kejadian</h3>
      <p class="text-[11.5px] text-[#617377]">
        Menampilkan kejadian untuk
        <b class="text-ink">{{ selectedSiteName || 'semua lokasi' }}</b>
        <button
          v-if="selectedSiteUid"
          type="button"
          class="ml-2 text-primary hover:text-primary-dark underline"
          @click="selectSite(null)"
        >
          Tampilkan semua
        </button>
      </p>
    </div>
    <LoggerEventTimeline :events="events" :loading="eventsLoading" />
  </AppLayout>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue';
import AppLayout from '@/Layouts/AppLayout.vue';
import PageHeader from '@/Components/PageHeader.vue';
import LoggerEventTimeline from '@/Components/LoggerEventTimeline.vue';
import { useApi } from '@/Composables/useApi';
import { getRelativeTime } from '@/Utils/helpers';

const { getLoggerStatus, getLoggerEvents, getAlerts } = useApi();

const statuses = ref([]);
const statusLoading = ref(false);

const events = ref([]);
const eventsLoading = ref(false);

const selectedSiteUid = ref(null);

const activeLoggerAlarms = ref(0);
const events24h = ref(0);

const totalCount = computed(() => statuses.value.length);
const aliveCount = computed(() => statuses.value.filter(s => s.state === 'alive').length);

const selectedSiteName = computed(() => {
  if (!selectedSiteUid.value) return '';
  const row = statuses.value.find(s => s.site_uid === selectedSiteUid.value);
  return row ? row.site_name : '';
});

function selectSite(uid) {
  selectedSiteUid.value = selectedSiteUid.value === uid ? null : uid;
}

async function loadStatuses() {
  statusLoading.value = true;
  try {
    const res = await getLoggerStatus();
    statuses.value = Array.isArray(res) ? res : (res?.items || []);
  } catch {
    statuses.value = [];
  } finally {
    statusLoading.value = false;
  }
}

async function loadEvents() {
  eventsLoading.value = true;
  try {
    const params = {};
    if (selectedSiteUid.value) params.site_uid = selectedSiteUid.value;
    const res = await getLoggerEvents(params);
    events.value = Array.isArray(res) ? res : (res?.items || []);
  } catch {
    events.value = [];
  } finally {
    eventsLoading.value = false;
  }
}

async function loadActiveLoggerAlarms() {
  try {
    const res = await getAlerts({ status: 'active', category: 'logger' });
    const list = Array.isArray(res) ? res : (res?.items || []);
    activeLoggerAlarms.value = list.length;
  } catch {
    activeLoggerAlarms.value = 0;
  }
}

async function loadEvents24h() {
  try {
    const dateFrom = new Date(Date.now() - 24 * 3600 * 1000).toISOString();
    const res = await getLoggerEvents({ date_from: dateFrom });
    const list = Array.isArray(res) ? res : (res?.items || []);
    events24h.value = list.length;
  } catch {
    events24h.value = 0;
  }
}

function refreshAll() {
  loadStatuses();
  loadEvents();
  loadActiveLoggerAlarms();
  loadEvents24h();
}

watch(selectedSiteUid, () => {
  loadEvents();
});

onMounted(() => {
  refreshAll();
});

// ---- formatting helpers ----

function fmtUptime(uptimeS) {
  if (uptimeS == null) return '—';
  const totalMin = Math.floor(uptimeS / 60);
  const hours = Math.floor(totalMin / 60);
  const mins = totalMin % 60;
  return `${hours}j ${mins}m`;
}

function pct(value, max) {
  if (value == null) return 0;
  return Math.min(100, Math.max(0, (value / max) * 100));
}

const OK_STYLE = { background: '#E6F2EC', color: '#1F7A4D' };
const WARNING_STYLE = { background: '#F7EFD9', color: '#9A6B00' };
const DANGER_STYLE = { background: '#F7E4E4', color: '#B03030' };
const OFFLINE_STYLE = { background: '#EAEEEF', color: '#6E7E82' };
const TEAL_SOFT_STYLE = { background: '#E4F1F2', color: '#0A5A62' };

function aliveStyle(state) {
  return state === 'alive' ? OK_STYLE : DANGER_STYLE;
}

function internetStyle(ok) {
  return ok ? OK_STYLE : OFFLINE_STYLE;
}

const OP_STATUS_LABELS = {
  0: 'Normal',
  '-1': 'Berhenti',
  '-2': 'Kalibrasi',
  '-3': 'Rusak',
};

function opStatusLabel(opStatus) {
  if (opStatus == null || opStatus === 0) return 'Normal';
  return OP_STATUS_LABELS[String(opStatus)] || 'Normal';
}

function opStatusStyle(opStatus) {
  if (opStatus == null || opStatus === 0) return TEAL_SOFT_STYLE;
  return OFFLINE_STYLE;
}

const SENSOR_FIELDS = [
  { key: 'ph_ok', label: 'pH' },
  { key: 'tss_ok', label: 'TSS' },
  { key: 'debit_ok', label: 'Debit' },
  { key: 'cod_ok', label: 'COD' },
  { key: 'nh3n_ok', label: 'NH₃-N' },
];

function sensorDots(row) {
  return SENSOR_FIELDS.map(f => {
    const val = row[f.key];
    let cls = 'bg-[#C4D1D3]';
    let state = '—';
    if (val === true) { cls = 'bg-success'; state = 'OK'; }
    else if (val === false) { cls = 'bg-danger'; state = 'Gagal'; }
    return { key: f.key, class: cls, title: `${f.label}: ${state}` };
  });
}
</script>
