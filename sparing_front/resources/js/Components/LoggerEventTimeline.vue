<template>
  <div class="bg-white border border-[#D7E0E1] rounded-lg p-4">
    <div v-if="loading" class="py-10 text-center text-[#617377] text-sm">
      <i class="fas fa-spinner fa-spin mr-2"></i>Memuat kejadian…
    </div>
    <div v-else-if="!events || !events.length" class="py-10 text-center text-[#617377] text-sm">
      <i class="fas fa-circle-info text-lg mb-2 block"></i>
      Belum ada kejadian tercatat.
    </div>
    <ol v-else class="relative">
      <li
        v-for="(ev, idx) in events"
        :key="ev.id"
        class="relative pl-9 pb-5 last:pb-0"
      >
        <!-- connector line -->
        <span
          v-if="idx < events.length - 1"
          class="absolute left-[13px] top-6 bottom-0 w-px bg-[#D7E0E1]"
        ></span>
        <!-- icon dot -->
        <span
          class="absolute left-0 top-0 w-7 h-7 rounded-full flex items-center justify-center"
          :style="{ backgroundColor: metaFor(ev.type).color + '1A' }"
        >
          <i
            class="fas text-[12px]"
            :class="metaFor(ev.type).icon"
            :style="{ color: metaFor(ev.type).color }"
          ></i>
        </span>

        <div class="flex items-start justify-between gap-3 flex-wrap">
          <div class="min-w-0">
            <div class="text-sm font-semibold text-ink">{{ metaFor(ev.type).label }}</div>
            <div class="text-[11.5px] text-[#617377] mt-0.5">
              {{ ev.site_name }}
            </div>
          </div>
          <div class="text-[11.5px] text-[#617377] font-mono whitespace-nowrap">
            {{ formatDate(ev.ts) }} {{ formatTime(ev.ts) }}
          </div>
        </div>

        <p v-if="ev.detail" class="text-[12.5px] text-[#617377] mt-1 break-words">
          {{ ev.detail }}
        </p>

        <p v-if="isDirtyRestart(ev)" class="text-[12.5px] text-[#B03030] font-semibold mt-1">
          Shutdown sebelumnya TIDAK bersih (crash/listrik padam)
        </p>
      </li>
    </ol>
  </div>
</template>

<script setup>
import { formatDate, formatTime } from '@/Utils/helpers';

defineProps({
  events: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false },
});

const EVENT_META = {
  started:        { label: 'Logger menyala',             icon: 'fa-play',                 color: '#1F7A4D' },
  stopping:       { label: 'Logger berhenti (normal)',   icon: 'fa-stop',                 color: '#617377' },
  stopped:        { label: 'Logger berhenti',            icon: 'fa-stop',                 color: '#617377' },
  sensor_fail:    { label: 'Sensor gagal dibaca',        icon: 'fa-triangle-exclamation', color: '#9A6B00' },
  sensor_recover: { label: 'Sensor pulih',               icon: 'fa-circle-check',         color: '#1F7A4D' },
  net_down:       { label: 'Internet terputus',          icon: 'fa-wifi',                 color: '#9A6B00' },
  net_up:         { label: 'Internet tersambung',        icon: 'fa-wifi',                 color: '#1F7A4D' },
  send_fail:      { label: 'Gagal kirim data',           icon: 'fa-cloud-arrow-up',       color: '#9A6B00' },
  opstatus_change:{ label: 'Status operasional berubah', icon: 'fa-sliders',              color: '#0E7C86' },
  buffer_high:    { label: 'Antrean data menumpuk',      icon: 'fa-layer-group',          color: '#9A6B00' },
  unknown:        { label: 'Kejadian',                   icon: 'fa-circle-info',          color: '#617377' },
};

function metaFor(type) {
  return EVENT_META[type] || EVENT_META.unknown;
}

function isDirtyRestart(ev) {
  return ev.type === 'started' && typeof ev.detail === 'string' && ev.detail.includes('previous_shutdown_clean=false');
}
</script>
