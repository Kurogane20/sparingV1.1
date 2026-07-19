<template>
  <div class="util bg-white border-b border-[#D7E0E1] px-4 md:px-6 py-1.5 flex gap-4 items-center text-[11.5px] text-[#617377] flex-wrap">
    <span class="flex items-center">
      <span
        class="inline-block w-[7px] h-[7px] rounded-full mr-1.5"
        :class="serverOk ? 'bg-success' : 'bg-danger'"
      ></span>
      Server: {{ serverOk ? 'normal' : 'gangguan' }}
    </span>

    <span class="text-[#C4D1D3] hidden sm:inline">|</span>

    <span v-if="lastSync" class="hidden sm:inline">
      Sinkronisasi terakhir: <span class="font-mono">{{ lastSync }}</span>
    </span>

    <span class="ml-auto flex items-center gap-3">
      <span class="font-mono text-[11px] hidden md:inline">{{ clock }}</span>
      <slot name="bell" />
    </span>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue';
import { useApi } from '@/Composables/useApi';

defineProps({
  lastSync: { type: String, default: '' },
});

const { healthCheck } = useApi();

const serverOk = ref(true);
const clock = ref('');

let clockTimer = null;
let healthTimer = null;

const HARI = ['Min', 'Sen', 'Sel', 'Rab', 'Kam', 'Jum', 'Sab'];
const BULAN = ['Jan', 'Feb', 'Mar', 'Apr', 'Mei', 'Jun', 'Jul', 'Agu', 'Sep', 'Okt', 'Nov', 'Des'];

function tick() {
  // Compute wall-clock time in WIB (UTC+7) regardless of the browser's local timezone.
  const now = new Date(Date.now() + (7 * 60 + new Date().getTimezoneOffset()) * 60000);
  const p = (n) => String(n).padStart(2, '0');
  clock.value = `${HARI[now.getDay()]}, ${now.getDate()} ${BULAN[now.getMonth()]} ${now.getFullYear()} · ${p(now.getHours())}:${p(now.getMinutes())}:${p(now.getSeconds())} WIB`;
}

async function checkHealth() {
  try {
    await healthCheck();
    serverOk.value = true;
  } catch {
    serverOk.value = false;
  }
}

onMounted(() => {
  tick();
  clockTimer = setInterval(tick, 1000);
  checkHealth();
  healthTimer = setInterval(checkHealth, 60000);
});

onUnmounted(() => {
  clearInterval(clockTimer);
  clearInterval(healthTimer);
});
</script>
