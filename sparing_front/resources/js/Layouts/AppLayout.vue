<template>
  <div class="flex min-h-screen">

    <!-- Mobile Overlay -->
    <transition name="fade">
      <div
        v-if="sidebarOpen && isMobile"
        class="fixed inset-0 bg-slate-900/50 z-30 md:hidden"
        @click="sidebarOpen = false"
      ></div>
    </transition>

    <!-- Sidebar -->
    <Sidebar :is-open="sidebarOpen" @close="sidebarOpen = false" />

    <!-- Main Content -->
    <div class="flex-1 flex flex-col min-h-screen min-w-0">

      <UtilityStrip :last-sync="lastSync">
        <template #bell>
          <AlertDropdown />
        </template>
      </UtilityStrip>

      <main class="flex-1 p-4 md:p-6 overflow-y-auto">
        <slot />
      </main>

      <footer class="app-foot px-4 md:px-6 py-3 border-t border-[#D7E0E1] bg-white flex flex-wrap items-center justify-between gap-2 text-[11.5px] text-[#617377]">
        <div class="flex flex-wrap items-center gap-x-4 gap-y-1">
          <span>SPARING Web v2</span>
          <span class="hidden sm:inline">Sesi berakhir otomatis setelah 30 menit tidak aktif</span>
          <a href="#" class="text-primary hover:underline">Helpdesk</a>
        </div>
        <div class="font-mono">Zona waktu tampilan: WIB (UTC+7)</div>
      </footer>
    </div>
  </div>
</template>

<script setup>
import { ref, provide, onMounted, onUnmounted } from 'vue';
import Sidebar from '@/Components/Sidebar.vue';
import UtilityStrip from '@/Components/UtilityStrip.vue';
import AlertDropdown from '@/Components/AlertDropdown.vue';

const sidebarOpen = ref(true);
const isMobile    = ref(false);
const lastSync    = ref('');

const toggleSidebar = () => { sidebarOpen.value = !sidebarOpen.value; };

// PageHeader (and any other descendant) can trigger the sidebar toggle
// without AppLayout needing to thread an emit through every page.
provide('toggleSidebar', toggleSidebar);

const checkScreen = () => {
  isMobile.value    = window.innerWidth < 768;
  sidebarOpen.value = !isMobile.value;
};

onMounted(() => {
  checkScreen();
  window.addEventListener('resize', checkScreen);
});

onUnmounted(() => {
  window.removeEventListener('resize', checkScreen);
});
</script>

<style scoped>
.fade-enter-active,
.fade-leave-active { transition: opacity 0.25s ease; }
.fade-enter-from,
.fade-leave-to     { opacity: 0; }
</style>
