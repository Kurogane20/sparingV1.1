<template>
  <div
    v-if="secondsLeft !== null"
    class="fixed inset-0 z-[9999] flex items-center justify-center bg-ink/40 p-4"
    role="alertdialog"
    aria-modal="true"
    aria-labelledby="idle-logout-title"
    aria-describedby="idle-logout-desc"
  >
    <div class="bg-white rounded-lg border border-[#D7E0E1] w-full max-w-sm p-5">
      <h3 id="idle-logout-title" class="text-[15px] font-bold text-ink mb-1">Sesi akan berakhir</h3>
      <p id="idle-logout-desc" class="text-[12.5px] text-[#617377]">
        Tidak ada aktivitas selama hampir 30 menit. Anda akan keluar otomatis dalam
        <span class="font-semibold text-ink tabular-nums">{{ secondsLeft }} detik</span>.
      </p>
      <div class="flex justify-end gap-2 mt-4">
        <button type="button" class="px-3 py-2 rounded-md border border-[#C4D1D3] text-sm" @click="endSession(null)">
          Keluar sekarang
        </button>
        <button
          ref="stayButton"
          type="button"
          class="px-3 py-2 rounded-md text-sm text-white bg-primary hover:bg-primary-dark"
          @click="stay"
        >
          Tetap masuk
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, nextTick, onMounted, onUnmounted } from 'vue';
import { useAuth } from '@/Composables/useAuth';
import { idleStatus, recordActivity } from '@/Utils/idleSession.js';

// Ends the session after 30 minutes without input (see Utils/idleSession.js).
// API polling does not count; only the person at the screen does.

const ACTIVITY_EVENTS = ['mousemove', 'mousedown', 'keydown', 'touchstart', 'wheel', 'scroll'];
const ACTIVITY_WRITE_GAP_MS = 5000;

const { logout } = useAuth();

const secondsLeft = ref(null);
const stayButton = ref(null);
let ending = false;
let timer = null;

const onActivity = () => {
  // While the warning is up only "Tetap masuk" keeps the session: otherwise
  // the mouse moving towards a button would close the dialog under it.
  if (secondsLeft.value !== null) return;
  recordActivity(localStorage, Date.now(), ACTIVITY_WRITE_GAP_MS);
};

const endSession = (reason) => {
  if (ending) return;
  ending = true;
  secondsLeft.value = null;
  logout(reason);
};

const tick = () => {
  if (ending) return;
  const status = idleStatus(localStorage, Date.now());
  if (status.expired) {
    endSession('idle');
    return;
  }
  const opening = secondsLeft.value === null && status.secondsLeft !== null;
  secondsLeft.value = status.secondsLeft;
  if (opening) nextTick(() => stayButton.value?.focus());
};

const stay = () => {
  recordActivity(localStorage, Date.now());
  secondsLeft.value = null;
};

// Background tabs run timers late; check as soon as the tab is seen again.
const onVisibility = () => {
  if (document.visibilityState === 'visible') tick();
};

onMounted(() => {
  ACTIVITY_EVENTS.forEach((type) => window.addEventListener(type, onActivity, { capture: true, passive: true }));
  document.addEventListener('visibilitychange', onVisibility);
  timer = setInterval(tick, 1000);
  tick();
});

onUnmounted(() => {
  ACTIVITY_EVENTS.forEach((type) => window.removeEventListener(type, onActivity, { capture: true }));
  document.removeEventListener('visibilitychange', onVisibility);
  clearInterval(timer);
});
</script>
