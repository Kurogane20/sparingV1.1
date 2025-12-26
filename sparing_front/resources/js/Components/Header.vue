<template>
  <header class="glass sticky top-0 z-30 px-6 py-4">
    <div class="flex justify-between items-center">
      <!-- Left: Hamburger + Page Title -->
      <div class="flex items-center gap-4">
        <button
          @click="$emit('toggle-sidebar')"
          class="md:hidden w-10 h-10 rounded-xl bg-white/50 hover:bg-white/80 flex items-center justify-center transition-all duration-300"
        >
          <i class="fas fa-bars text-gray-600"></i>
        </button>

        <div>
          <h1 class="text-2xl font-bold bg-gradient-to-r from-gray-900 to-gray-600 bg-clip-text text-transparent">
            {{ pageTitle }}
          </h1>
          <p class="text-sm text-gray-500 flex items-center gap-2">
            <span class="w-2 h-2 rounded-full bg-primary animate-pulse"></span>
            {{ pageSubtitle }}
          </p>
        </div>
      </div>

      <!-- Right: Status + User Profile -->
      <div class="flex items-center gap-4">
        <!-- System Status Badge -->
        <div
          :class="[
            'hidden sm:flex items-center gap-2 px-4 py-2 rounded-full text-sm font-medium transition-all duration-300',
            systemStatus === 'online' 
              ? 'bg-emerald-50 text-emerald-700 shadow-sm shadow-emerald-200' 
              : 'bg-red-50 text-red-700'
          ]"
        >
          <span 
            :class="[
              'w-2.5 h-2.5 rounded-full',
              systemStatus === 'online' ? 'bg-emerald-500 animate-pulse' : 'bg-red-500'
            ]"
          ></span>
          <i :class="systemStatus === 'online' ? 'fas fa-wifi' : 'fas fa-wifi-slash'"></i>
          <span>{{ systemStatus === 'online' ? 'Sistem Online' : 'Sistem Offline' }}</span>
        </div>

        <!-- User Profile -->
        <div class="hidden md:flex items-center gap-3 pl-4 border-l border-gray-200">
          <div class="text-right">
            <div class="font-semibold text-gray-900">{{ userName }}</div>
            <div class="text-xs text-gray-500">{{ currentDate }}</div>
          </div>

          <div class="relative group">
            <div class="w-11 h-11 rounded-xl bg-gradient-to-br from-primary to-emerald-400 flex items-center justify-center shadow-lg shadow-primary/20 cursor-pointer transition-transform hover:scale-105">
              <span class="text-white font-semibold text-sm">{{ userInitials }}</span>
            </div>
            <!-- Online indicator -->
            <span class="absolute -bottom-0.5 -right-0.5 w-3.5 h-3.5 bg-emerald-500 border-2 border-white rounded-full"></span>
          </div>
        </div>
      </div>
    </div>
  </header>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue';
import { useRoute } from 'vue-router';
import { useAuth } from '@/Composables/useAuth';
import { useApi } from '@/Composables/useApi';
import { formatDate } from '@/Utils/helpers';

// Emit
defineEmits(['toggle-sidebar']);

// Composables
const route = useRoute();
const { user } = useAuth();
const { healthCheck } = useApi();

// State
const systemStatus = ref('online');
const currentDate = ref(formatDate(new Date(), true));

// Route-based titles
const pageTitles = {
  '/dashboard': 'Dashboard Lingkungan',
  '/analytics': 'Analisis Data',
  '/history': 'Riwayat Data Sensor',
  '/sites': 'Manajemen Lokasi',
  '/devices': 'Manajemen Perangkat IoT',
  '/users': 'Manajemen Pengguna',
  '/settings': 'Pengaturan Sistem',
};

// Computed
const pageTitle = computed(() => pageTitles[route.path] || 'Dashboard');
const pageSubtitle = computed(() => 'Monitoring Real-time & Analisis Kualitas Air');
const userName = computed(() => user.value?.name || user.value?.email || 'User');
const userInitials = computed(() => {
  const name = user.value?.name || user.value?.email || 'U';
  const parts = name.split(' ');
  if (parts.length >= 2) {
    return (parts[0][0] + parts[1][0]).toUpperCase();
  }
  return name.substring(0, 2).toUpperCase();
});

// Check system health periodically
let healthCheckInterval;

const checkHealth = async () => {
  try {
    await healthCheck();
    systemStatus.value = 'online';
  } catch (error) {
    systemStatus.value = 'offline';
  }
};

// Update date every minute
let dateInterval;

const updateDate = () => {
  currentDate.value = formatDate(new Date(), true);
};

onMounted(() => {
  checkHealth();
  healthCheckInterval = setInterval(checkHealth, 30000);
  dateInterval = setInterval(updateDate, 60000);
});

onUnmounted(() => {
  clearInterval(healthCheckInterval);
  clearInterval(dateInterval);
});
</script>
