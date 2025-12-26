<template>
  <div class="flex min-h-screen">
    <!-- Mobile Overlay -->
    <transition name="fade">
      <div 
        v-if="sidebarOpen && isMobile" 
        class="fixed inset-0 bg-black/50 z-30 md:hidden"
        @click="sidebarOpen = false"
      ></div>
    </transition>

    <!-- Sidebar -->
    <Sidebar :is-open="sidebarOpen" @close="sidebarOpen = false" />

    <!-- Main Content Area -->
    <div :class="['flex-1 flex flex-col min-h-screen transition-all duration-300', sidebarOpen ? 'md:ml-64' : 'md:ml-20']">
      <!-- Header -->
      <Header @toggle-sidebar="toggleSidebar" />

      <!-- Page Content -->
      <main class="flex-1 p-4 md:p-6 lg:p-8 overflow-y-auto">
        <!-- Gradient background for content area -->
        <div class="relative">
          <slot />
        </div>
      </main>

      <!-- Footer -->
      <footer class="py-4 px-6 text-center text-sm text-gray-500 border-t border-gray-200/50">
        <p>&copy; 2025 SPARING Environmental Monitoring System. All rights reserved.</p>
      </footer>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue';
import Sidebar from '@/Components/Sidebar.vue';
import Header from '@/Components/Header.vue';

// Sidebar state
const sidebarOpen = ref(true);
const isMobile = ref(false);

// Toggle sidebar
const toggleSidebar = () => {
  sidebarOpen.value = !sidebarOpen.value;
};

// Check screen size
const checkScreenSize = () => {
  isMobile.value = window.innerWidth < 768;
  if (isMobile.value) {
    sidebarOpen.value = false;
  } else {
    sidebarOpen.value = true;
  }
};

onMounted(() => {
  checkScreenSize();
  window.addEventListener('resize', checkScreenSize);
});

onUnmounted(() => {
  window.removeEventListener('resize', checkScreenSize);
});
</script>

<style scoped>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
