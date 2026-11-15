<template>
  <AppLayout>
    <PageHeader
      :crumb="['Beranda', 'Logger']"
      title="Monitoring Logger"
      subtitle="Kondisi logger di tiap lokasi: apa yang terjadi, sejak kapan, dan apa yang perlu dilakukan."
    >
      <template #actions>
        <div class="flex flex-wrap items-center gap-2 text-xs text-muted">
          <span class="tabular-nums">{{ summary }}</span>
          <button
            type="button"
            class="flex items-center gap-1.5 rounded-lg px-3 py-1.5 font-semibold text-muted transition-colors hover:bg-[#EEF4F4] disabled:opacity-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary"
            :disabled="loading"
            @click="refresh"
          >
            <i class="fas fa-sync-alt" :class="{ 'animate-spin': loading }" aria-hidden="true"></i>
            Muat ulang
          </button>
        </div>
      </template>
    </PageHeader>

    <p v-if="loadError" class="mb-3 rounded-lg bg-idle px-4 py-3 text-[13px] text-white" role="status">
      Diagnosis logger belum bisa dimuat. Muat ulang untuk mencoba lagi.
    </p>
    <div
      v-if="loading && !rows.length"
      class="h-40 animate-pulse rounded-xl bg-[#E3ECEC] motion-reduce:animate-none"
      aria-busy="true"
      aria-label="Memuat diagnosis logger"
    ></div>
    <ul v-else-if="rows.length" class="overflow-hidden rounded-xl border border-line bg-white" aria-label="Logger per lokasi">
      <LoggerRow
        v-for="row in rows"
        :key="row.site_uid"
        :row="row"
        :incidents="incidentsBySite[row.site_uid] || []"
        :expanded="expanded.has(row.site_uid)"
        :events="eventsBySite[row.site_uid] || []"
        :events-loading="eventsLoadingFor === row.site_uid"
        :now="nowTick"
        @toggle="toggle(row)"
      />
    </ul>
    <p v-else-if="!loadError" class="rounded-xl border border-line bg-white px-4 py-6 text-[13px] text-muted">
      Belum ada lokasi yang bisa ditampilkan.
    </p>

    <UnknownLoggers v-if="isAdmin" :rejections="unknownRejections" />
  </AppLayout>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue';
import AppLayout from '@/Layouts/AppLayout.vue';
import PageHeader from '@/Components/PageHeader.vue';
import LoggerRow from '@/Components/Loggers/LoggerRow.vue';
import UnknownLoggers from '@/Components/Loggers/UnknownLoggers.vue';
import { useApi } from '@/Composables/useApi';
import { useAuth } from '@/Composables/useAuth';
import { summaryText } from '@/Utils/loggerDiagnosis.js';
import logger from '@/Utils/logger';

// The Logger page as a diagnosis list (logger-diagnosis spec, Bagian 4): one
// row per logger, worst first, each saying what is wrong and what to do.
const { getLoggerDiagnosis, getLoggerIncidents, getLoggerRejections, getLoggerEvents } = useApi();
const { isAdmin } = useAuth();

const rows = ref([]);
const incidents = ref([]);
const rejections = ref([]);
const loading = ref(false);
const loadError = ref(false);
const expanded = ref(new Set());
const eventsBySite = ref({});
const eventsLoadingFor = ref(null);
const nowTick = ref(Date.now());
let timer = null;

const summary = computed(() => summaryText(rows.value));
const incidentsBySite = computed(() => {
  const map = {};
  for (const incident of incidents.value) (map[incident.site_uid] ||= []).push(incident);
  return map;
});
const unknownRejections = computed(() => rejections.value.filter((r) => !r.site_uid));

async function refresh() {
  loading.value = true;
  nowTick.value = Date.now();
  try {
    const [diagnosis, history] = await Promise.all([getLoggerDiagnosis(), getLoggerIncidents({ days: 30 })]);
    rows.value = Array.isArray(diagnosis) ? diagnosis : [];
    incidents.value = Array.isArray(history) ? history : [];
    loadError.value = false;
  } catch (e) {
    loadError.value = true;
    logger.error('Failed to load logger diagnosis:', e);
  } finally {
    loading.value = false;
  }
  if (isAdmin.value) {
    try {
      const list = await getLoggerRejections();
      rejections.value = Array.isArray(list) ? list : [];
    } catch (e) {
      rejections.value = [];
      logger.error('Failed to load device rejections:', e);
    }
  }
}

async function toggle(row) {
  const next = new Set(expanded.value);
  if (next.has(row.site_uid)) {
    next.delete(row.site_uid);
    expanded.value = next;
    return;
  }
  next.add(row.site_uid);
  expanded.value = next;
  // Raw events only for those who see the technical section, loaded once.
  if (!row.tech || eventsBySite.value[row.site_uid]) return;
  eventsLoadingFor.value = row.site_uid;
  try {
    const list = await getLoggerEvents({ site_uid: row.site_uid, limit: 50 });
    eventsBySite.value = { ...eventsBySite.value, [row.site_uid]: Array.isArray(list) ? list : (list?.items || []) };
  } catch (e) {
    eventsBySite.value = { ...eventsBySite.value, [row.site_uid]: [] };
    logger.error('Failed to load logger events:', e);
  } finally {
    if (eventsLoadingFor.value === row.site_uid) eventsLoadingFor.value = null;
  }
}

onMounted(() => {
  refresh();
  timer = setInterval(refresh, 60000);
});
onUnmounted(() => {
  if (timer) clearInterval(timer);
});
</script>
