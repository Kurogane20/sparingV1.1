<template>
  <aside
    :class="[
      'sidebar fixed left-0 top-0 bottom-0 z-40 transition-all duration-500 ease-out',
      'flex flex-col overflow-hidden',
      isOpen ? 'w-64' : 'w-0 md:w-20',
    ]"
  >
    <!-- Gradient Overlay -->
    <div class="absolute inset-0 bg-gradient-to-b from-slate-800 via-slate-900 to-slate-950 opacity-95"></div>
    
    <!-- Decorative Elements -->
    <div class="absolute top-0 right-0 w-32 h-32 bg-primary/10 rounded-full blur-3xl"></div>
    <div class="absolute bottom-20 left-0 w-24 h-24 bg-secondary/10 rounded-full blur-2xl"></div>

    <!-- Content -->
    <div class="relative z-10 flex flex-col h-full">
      <!-- Logo -->
      <div class="p-6 flex items-center gap-3">
        <div class="w-10 h-10 rounded-xl bg-gradient-to-br from-primary to-emerald-400 flex items-center justify-center shadow-lg shadow-primary/30">
          <i class="fas fa-leaf text-white text-lg"></i>
        </div>
        <transition name="fade">
          <span
            v-show="isOpen"
            class="text-2xl font-bold bg-gradient-to-r from-primary to-emerald-300 bg-clip-text text-transparent"
          >
            SPARING
          </span>
        </transition>
      </div>

      <!-- Navigation Menu -->
      <nav class="flex-1 px-3 mt-4 space-y-1 overflow-y-auto scrollbar-thin">
        <router-link
          v-for="item in menuItems"
          :key="item.path"
          :to="item.path"
          :class="[
            'menu-item group relative',
            isActive(item.path)
              ? 'bg-white/10 text-white shadow-lg shadow-black/10'
              : 'text-gray-400 hover:text-white',
          ]"
        >
          <!-- Active Indicator -->
          <div
            v-if="isActive(item.path)"
            class="absolute left-0 top-1/2 -translate-y-1/2 w-1 h-8 bg-gradient-to-b from-primary to-emerald-400 rounded-r-full"
          ></div>
          
          <!-- Icon with glow on active -->
          <div
            :class="[
              'w-9 h-9 rounded-lg flex items-center justify-center transition-all duration-300',
              isActive(item.path) 
                ? 'bg-primary/20 text-primary' 
                : 'group-hover:bg-white/5'
            ]"
          >
            <i :class="[item.icon, 'text-base']"></i>
          </div>
          
          <!-- Label -->
          <transition name="slide-fade">
            <span v-show="isOpen" class="font-medium">{{ item.label }}</span>
          </transition>

          <!-- Hover indicator -->
          <div
            class="absolute right-3 w-1.5 h-1.5 rounded-full bg-primary opacity-0 group-hover:opacity-100 transition-opacity"
            v-if="!isActive(item.path)"
          ></div>
        </router-link>
      </nav>

      <!-- User Section -->
      <div class="p-4 border-t border-white/10">
        <button
          @click="handleLogout"
          class="menu-item w-full group text-gray-400 hover:text-red-400 hover:bg-red-500/10"
        >
          <div class="w-9 h-9 rounded-lg flex items-center justify-center group-hover:bg-red-500/10 transition-all">
            <i class="fas fa-sign-out-alt"></i>
          </div>
          <transition name="slide-fade">
            <span v-show="isOpen" class="font-medium">Keluar</span>
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

// Props
defineProps({
  isOpen: {
    type: Boolean,
    default: true,
  },
});

// Composables
const router = useRouter();
const route = useRoute();
const { logout, user } = useAuth();

// All menu items with role restrictions
const allMenuItems = [
  {
    path: '/dashboard',
    icon: 'fas fa-th-large',
    label: 'Dashboard',
    roles: ['admin', 'operator', 'viewer'],
  },
  {
    path: '/analytics',
    icon: 'fas fa-chart-line',
    label: 'Analisis',
    roles: ['admin', 'operator', 'viewer'],
  },
  {
    path: '/history',
    icon: 'fas fa-database',
    label: 'Riwayat Data',
    roles: ['admin', 'operator', 'viewer'],
  },
  {
    path: '/sites',
    icon: 'fas fa-map-marker-alt',
    label: 'Lokasi',
    roles: ['admin', 'operator', 'viewer'],
  },
  {
    path: '/devices',
    icon: 'fas fa-microchip',
    label: 'Perangkat',
    roles: ['admin', 'operator'],
  },
  {
    path: '/users',
    icon: 'fas fa-users',
    label: 'Pengguna',
    roles: ['admin'],
  },
  {
    path: '/settings',
    icon: 'fas fa-cog',
    label: 'Pengaturan',
    roles: ['admin', 'operator', 'viewer'],
  },
];

// Filter menu items based on user role
const menuItems = computed(() => {
  const userRole = user.value?.role || 'viewer';
  return allMenuItems.filter(item => item.roles.includes(userRole));
});

// Check if current route is active
const isActive = (path) => {
  return route.path === path;
};

// Handle logout
const handleLogout = async () => {
  try {
    await logout();
    router.push('/login');
  } catch (error) {
    console.error('Logout error:', error);
  }
};
</script>

<style scoped>
.sidebar {
  box-shadow: 4px 0 24px rgba(0, 0, 0, 0.15);
}

/* Transitions */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

.slide-fade-enter-active,
.slide-fade-leave-active {
  transition: all 0.3s ease;
}

.slide-fade-enter-from,
.slide-fade-leave-to {
  opacity: 0;
  transform: translateX(-10px);
}

@media (max-width: 768px) {
  .sidebar {
    transform: translateX(-100%);
  }
  
  .sidebar.w-64 {
    transform: translateX(0);
  }
}
</style>
