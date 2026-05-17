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
    <div :class="['flex-1 flex flex-col min-h-screen transition-all duration-300', sidebarOpen ? 'md:ml-64' : 'md:ml-[72px]']">

      <Header @toggle-sidebar="toggleSidebar" />

      <main class="flex-1 p-4 md:p-6 overflow-y-auto">
        <slot />
      </main>

      <footer class="py-3 px-5 text-center text-xs text-slate-400 border-t border-slate-200 bg-white">
        &copy; 2025 SPARING Environmental Monitoring System
      </footer>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue';
import Sidebar from '@/Components/Sidebar.vue';
import Header  from '@/Components/Header.vue';

const sidebarOpen = ref(true);
const isMobile    = ref(false);

const toggleSidebar = () => { sidebarOpen.value = !sidebarOpen.value; };

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
