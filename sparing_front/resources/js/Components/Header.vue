<template>
  <header class="sticky top-0 z-30 bg-white border-b border-slate-200 px-5 py-3.5" style="box-shadow: 0 1px 0 #e2e8f0;">
    <!-- Top accent gradient bar -->
    <div class="absolute top-0 left-0 right-0 h-[3px]" style="background: linear-gradient(90deg, #1e3a8a 0%, #2563eb 40%, #7c3aed 80%, #0ea5e9 100%);"></div>
    <div class="flex items-center justify-between">

      <!-- Left: Hamburger + Page Title -->
      <div class="flex items-center gap-3">
        <button
          @click="$emit('toggle-sidebar')"
          class="w-9 h-9 rounded-lg hover:bg-slate-100 flex items-center justify-center transition-colors"
          aria-label="Toggle sidebar"
        >
          <i class="fas fa-bars text-slate-500 text-sm"></i>
        </button>

        <div class="h-5 w-px bg-slate-200 hidden sm:block"></div>

        <div class="hidden sm:block">
          <h1 class="text-base font-semibold text-slate-800 leading-tight">{{ pageTitle }}</h1>
          <p class="text-xs text-slate-400 mt-0.5 flex items-center gap-1.5">
            <span class="w-1.5 h-1.5 rounded-full inline-block"
              :class="systemStatus === 'online' ? 'bg-emerald-500 animate-pulse' : 'bg-red-400'"
            ></span>
            {{ systemStatus === 'online' ? 'Sistem Online' : 'Sistem Offline' }}
          </p>
        </div>
      </div>

      <!-- Right: Date + Alert Bell + User avatar -->
      <div class="flex items-center gap-3">

        <div class="hidden md:block text-right">
          <div class="text-xs text-slate-400">{{ currentDate }}</div>
        </div>

        <div class="h-5 w-px bg-slate-200 hidden md:block"></div>

        <!-- Alert Bell -->
        <AlertDropdown />

        <div class="h-5 w-px bg-slate-200"></div>

        <!-- Avatar + Dropdown -->
        <div class="relative" ref="dropdownRef">
          <button
            @click="toggleDropdown"
            class="flex items-center gap-2.5 rounded-xl px-2 py-1.5 hover:bg-slate-50 transition-colors"
          >
            <!-- Avatar -->
            <div class="relative">
              <div class="w-8 h-8 rounded-lg bg-primary flex items-center justify-center">
                <span class="text-white font-semibold text-xs">{{ userInitials }}</span>
              </div>
              <span
                class="absolute -bottom-0.5 -right-0.5 w-2.5 h-2.5 rounded-full border-2 border-white"
                :class="systemStatus === 'online' ? 'bg-emerald-500' : 'bg-red-400'"
              ></span>
            </div>

            <!-- Name (desktop) -->
            <div class="hidden md:block text-left">
              <div class="text-sm font-semibold text-slate-800 leading-tight">{{ userName }}</div>
              <div class="text-xs text-slate-400 capitalize">{{ userRole }}</div>
            </div>

            <i class="fas fa-chevron-down text-slate-400 text-xs hidden md:block transition-transform duration-200"
              :class="{ 'rotate-180': dropdownOpen }"
            ></i>
          </button>

          <!-- Dropdown Menu -->
          <Transition name="dropdown">
            <div
              v-if="dropdownOpen"
              class="absolute right-0 top-full mt-2 w-52 bg-white rounded-xl shadow-lg border border-slate-100 py-1.5 z-50"
            >
              <!-- User info header -->
              <div class="px-4 py-2.5 border-b border-slate-100 mb-1">
                <div class="text-sm font-semibold text-slate-800 truncate">{{ userName }}</div>
                <div class="text-xs text-slate-400 capitalize">{{ userRole }}</div>
              </div>

              <!-- Settings link -->
              <router-link
                to="/settings"
                @click="dropdownOpen = false"
                class="flex items-center gap-3 px-4 py-2 text-sm text-slate-700 hover:bg-slate-50 transition-colors"
              >
                <div class="w-7 h-7 rounded-lg bg-slate-100 flex items-center justify-center">
                  <i class="fas fa-cog text-slate-500 text-xs"></i>
                </div>
                Pengaturan
              </router-link>

              <div class="h-px bg-slate-100 my-1"></div>

              <!-- Logout -->
              <button
                @click="handleLogout"
                class="w-full flex items-center gap-3 px-4 py-2 text-sm text-red-600 hover:bg-red-50 transition-colors"
              >
                <div class="w-7 h-7 rounded-lg bg-red-50 flex items-center justify-center">
                  <i class="fas fa-sign-out-alt text-red-500 text-xs"></i>
                </div>
                Keluar
              </button>
            </div>
          </Transition>
        </div>
      </div>

    </div>
  </header>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useAuth } from '@/Composables/useAuth';
import { useApi } from '@/Composables/useApi';
import { formatDate } from '@/Utils/helpers';
import AlertDropdown from '@/Components/AlertDropdown.vue';

defineEmits(['toggle-sidebar']);

const route  = useRoute();
const router = useRouter();
const { user, logout } = useAuth();
const { healthCheck } = useApi();

const systemStatus  = ref('online');
const currentDate   = ref(formatDate(new Date(), true));
const dropdownOpen  = ref(false);
const dropdownRef   = ref(null);

const pageTitles = {
  '/dashboard': 'Dashboard Lingkungan',
  '/analytics': 'Analisis Data',
  '/history':   'Riwayat Data Sensor',
  '/sites':     'Manajemen Lokasi',
  '/devices':   'Manajemen Perangkat IoT',
  '/users':     'Manajemen Pengguna',
  '/settings':  'Pengaturan Sistem',
  '/alerts':    'Notifikasi & Alert',
};

const pageTitle    = computed(() => pageTitles[route.path] || 'Dashboard');
const userName     = computed(() => user.value?.name || user.value?.email || 'User');
const userRole     = computed(() => user.value?.role || 'viewer');
const userInitials = computed(() => {
  const name  = user.value?.name || user.value?.email || 'U';
  const parts = name.split(' ');
  return parts.length >= 2
    ? (parts[0][0] + parts[1][0]).toUpperCase()
    : name.substring(0, 2).toUpperCase();
});

const toggleDropdown = () => { dropdownOpen.value = !dropdownOpen.value; };

const handleLogout = async () => {
  dropdownOpen.value = false;
  try {
    await logout();
  } catch (e) {
    // ignore — clear client-side regardless
  }
  router.push('/login');
};

// Close dropdown on outside click
const handleOutsideClick = (e) => {
  if (dropdownRef.value && !dropdownRef.value.contains(e.target)) {
    dropdownOpen.value = false;
  }
};

let healthInterval, dateInterval;

const checkHealth = async () => {
  try {
    await healthCheck();
    systemStatus.value = 'online';
  } catch {
    systemStatus.value = 'offline';
  }
};

onMounted(() => {
  checkHealth();
  healthInterval = setInterval(checkHealth, 30000);
  dateInterval   = setInterval(() => { currentDate.value = formatDate(new Date(), true); }, 60000);
  document.addEventListener('click', handleOutsideClick);
});

onUnmounted(() => {
  clearInterval(healthInterval);
  clearInterval(dateInterval);
  document.removeEventListener('click', handleOutsideClick);
});
</script>

<style scoped>
.dropdown-enter-active { transition: all 0.15s ease-out; }
.dropdown-leave-active { transition: all 0.1s ease-in; }
.dropdown-enter-from   { opacity: 0; transform: translateY(-6px) scale(0.97); }
.dropdown-leave-to     { opacity: 0; transform: translateY(-4px) scale(0.97); }
</style>
