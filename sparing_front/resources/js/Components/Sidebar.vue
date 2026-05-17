<template>
  <aside
    :class="[
      'sidebar fixed left-0 top-0 bottom-0 z-40 transition-all duration-300 flex flex-col overflow-hidden',
      isOpen ? 'w-64' : 'w-0 md:w-[72px]',
    ]"
  >
    <!-- Dot grid texture -->
    <svg class="absolute inset-0 w-full h-full pointer-events-none" xmlns="http://www.w3.org/2000/svg">
      <defs>
        <pattern id="sidebar-dots" x="0" y="0" width="16" height="16" patternUnits="userSpaceOnUse">
          <circle cx="2" cy="2" r="1" fill="white" fill-opacity="0.12"/>
        </pattern>
      </defs>
      <rect width="100%" height="100%" fill="url(#sidebar-dots)"/>
    </svg>

    <!-- Content -->
    <div class="relative z-10 flex flex-col h-full">

      <!-- Logo -->
      <div class="flex items-center gap-3 px-4 py-5 border-b border-white/10">
        <div class="w-9 h-9 rounded-lg bg-white/15 flex items-center justify-center shrink-0">
          <i class="fas fa-water text-white text-base"></i>
        </div>
        <transition name="fade">
          <div v-show="isOpen">
            <div class="text-white font-bold text-base leading-tight tracking-wide">SPARING</div>
            <div class="text-blue-200 text-[11px] font-medium leading-none mt-0.5">Monitoring Lingkungan</div>
          </div>
        </transition>
      </div>

      <!-- Navigation Menu -->
      <nav class="flex-1 px-2 py-4 space-y-0.5 overflow-y-auto scrollbar-thin">
        <router-link
          v-for="item in menuItems"
          :key="item.path"
          :to="item.path"
          :class="[
            'menu-item group',
            isActive(item.path) ? 'active' : '',
          ]"
          :title="!isOpen ? item.label : undefined"
        >
          <!-- Icon -->
          <div class="w-8 h-8 rounded-md flex items-center justify-center shrink-0 transition-colors"
            :class="isActive(item.path) ? 'bg-white/20' : 'group-hover:bg-white/10'"
          >
            <i :class="[item.icon, 'text-sm']"></i>
          </div>

          <!-- Label -->
          <transition name="slide-fade">
            <span v-show="isOpen" class="truncate">{{ item.label }}</span>
          </transition>
        </router-link>
      </nav>

      <!-- Logout -->
      <div class="px-2 py-3 border-t border-white/10">
        <button
          @click="handleLogout"
          class="menu-item w-full hover:!bg-red-600/20 hover:!text-red-300"
        >
          <div class="w-8 h-8 rounded-md flex items-center justify-center shrink-0 group-hover:bg-red-500/10 transition-colors">
            <i class="fas fa-sign-out-alt text-sm"></i>
          </div>
          <transition name="slide-fade">
            <span v-show="isOpen">Keluar</span>
          </transition>
        </button>
      </div>
    </div>
  </aside>
</template>

<script setup>
import { computed } from 'vue';
import { useRouter, useRoute } from 'vue-router';
import { useAuth } from '@/Composables/useAuth';

defineProps({
  isOpen: { type: Boolean, default: true },
});

const router = useRouter();
const route  = useRoute();
const { logout, user } = useAuth();

const allMenuItems = [
  { path: '/dashboard', icon: 'fas fa-th-large',       label: 'Dashboard',    roles: ['admin','operator','viewer'] },
  { path: '/analytics', icon: 'fas fa-chart-line',     label: 'Analisis',     roles: ['admin','operator','viewer'] },
  { path: '/history',   icon: 'fas fa-database',       label: 'Riwayat Data', roles: ['admin','operator','viewer'] },
  { path: '/sites',     icon: 'fas fa-map-marker-alt', label: 'Lokasi',       roles: ['admin','operator','viewer'] },
  { path: '/devices',   icon: 'fas fa-microchip',      label: 'Perangkat',    roles: ['admin','operator'] },
  { path: '/users',     icon: 'fas fa-users',          label: 'Pengguna',     roles: ['admin'] },
  { path: '/settings',  icon: 'fas fa-cog',            label: 'Pengaturan',   roles: ['admin','operator','viewer'] },
];

const menuItems = computed(() => {
  const role = user.value?.role || 'viewer';
  return allMenuItems.filter(item => item.roles.includes(role));
});

const isActive = (path) => route.path === path;

const handleLogout = async () => {
  try {
    await logout();
    router.push('/login');
  } catch (e) {
    console.error('Logout error:', e);
  }
};
</script>

<style scoped>
.fade-enter-active,
.fade-leave-active { transition: opacity 0.2s ease; }
.fade-enter-from,
.fade-leave-to     { opacity: 0; }

.slide-fade-enter-active,
.slide-fade-leave-active { transition: all 0.2s ease; }
.slide-fade-enter-from,
.slide-fade-leave-to     { opacity: 0; transform: translateX(-8px); }

@media (max-width: 768px) {
  .sidebar            { transform: translateX(-100%); }
  .sidebar.w-64       { transform: translateX(0); }
}
</style>
