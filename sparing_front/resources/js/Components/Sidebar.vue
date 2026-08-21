<template>
  <aside
    class="sidebar fixed md:static inset-y-0 left-0 z-40 w-64 shrink-0 flex flex-col transition-transform duration-300 transform"
    :class="isOpen ? 'translate-x-0' : '-translate-x-full md:translate-x-0'"
    style="background: #12333B;"
  >
    <!-- Logo head -->
    <div class="sb-head flex items-center gap-3 px-4 py-5 border-b border-white/10 shrink-0">
      <div class="w-9 h-9 rounded-lg bg-white/15 flex items-center justify-center shrink-0">
        <i class="fas fa-water text-white text-base"></i>
      </div>
      <div class="min-w-0">
        <div class="text-white font-bold text-base leading-tight tracking-wide">SPARING Web</div>
        <div class="text-[#7FA6AC] text-[11px] font-medium leading-none mt-1">Mitra Mutiara &middot; WIB</div>
      </div>
    </div>

    <!-- Grouped navigation -->
    <nav class="flex-1 px-2 py-4 space-y-4 overflow-y-auto scrollbar-thin">
      <div v-for="group in visibleGroups" :key="group.label">
        <div class="nav-label text-[10.5px] font-bold uppercase tracking-wider text-[#7FA6AC] px-3 mb-1.5">
          {{ group.label }}
        </div>
        <div class="space-y-0.5">
          <router-link
            v-for="item in group.items"
            :key="item.path"
            :to="item.path"
            class="nav-item group flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors"
            :class="isActive(item.path)
              ? 'bg-white text-[#12333B] font-semibold'
              : 'text-white/70 hover:bg-white/10 hover:text-white'"
            @click="$emit('close')"
          >
            <i :class="[item.icon, 'text-sm w-4 text-center shrink-0']"></i>
            <span class="truncate flex-1">{{ item.label }}</span>
            <span
              v-if="item.pill && pillValue(item) > 0"
              class="pill inline-flex items-center justify-center min-w-[18px] h-[18px] px-1 rounded-full bg-danger text-white text-[10px] font-bold leading-none shrink-0"
            >
              {{ pillValue(item) > 99 ? '99+' : pillValue(item) }}
            </span>
          </router-link>
        </div>
      </div>
    </nav>

    <!-- Foot -->
    <div class="sb-foot px-3 py-3.5 border-t border-white/10 shrink-0">
      <div class="flex items-center gap-2.5 mb-2.5">
        <div class="avatar w-8 h-8 rounded-lg bg-white/15 flex items-center justify-center shrink-0">
          <span class="text-white font-semibold text-xs">{{ userInitials }}</span>
        </div>
        <div class="min-w-0 flex-1">
          <div class="text-white text-sm font-semibold leading-tight truncate">{{ userName }}</div>
          <div class="text-[#7FA6AC] text-[11px] capitalize leading-tight">{{ userRole }}</div>
        </div>
      </div>
      <button
        type="button"
        class="btn-logout w-full flex items-center justify-center gap-2 px-3 py-2 rounded-md text-xs font-semibold text-white/80 border border-white/15 hover:bg-red-600/20 hover:text-red-200 hover:border-red-400/30 transition-colors"
        @click="handleLogout"
      >
        <i class="fas fa-sign-out-alt text-xs"></i>
        Keluar
      </button>
    </div>
  </aside>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue';
import { useRoute } from 'vue-router';
import { useAuth } from '@/Composables/useAuth';
import { useApi } from '@/Composables/useApi';

defineProps({
  isOpen: { type: Boolean, default: true },
});
defineEmits(['close']);

const route = useRoute();
const { logout, user, isAdmin, isViewer } = useAuth();
const { getAlertCount, getLoggerStatus } = useApi();

const alertCount = ref(0);
const loggerDownCount = ref(0);
let pollInterval = null;

// Each pill item names its source via pillKey; the value is looked up here.
const pillValue = (item) => (item.pillKey === 'loggers' ? loggerDownCount.value : alertCount.value);

const fetchCounts = async () => {
  try {
    const res = await getAlertCount('active');
    alertCount.value = res?.count ?? 0;
  } catch {
    // silent — sidebar pill just stays at its last known value
  }
  try {
    const rows = await getLoggerStatus();
    loggerDownCount.value = Array.isArray(rows) ? rows.filter((r) => r.state === 'down').length : 0;
  } catch {
    // silent
  }
};

onMounted(() => {
  fetchCounts();
  pollInterval = setInterval(fetchCounts, 60000);
});

onUnmounted(() => {
  clearInterval(pollInterval);
});

const allGroups = [
  {
    label: 'Pemantauan',
    items: [
      { path: '/overview', icon: 'fas fa-satellite-dish', label: 'Command Center', adminOnly: true },
      { path: '/dashboard', icon: 'fas fa-th-large', label: 'Dashboard' },
      { path: '/alarms', icon: 'fas fa-bell', label: 'Alarm', pill: true, pillKey: 'alerts' },
      { path: '/loggers', icon: 'fas fa-hard-drive', label: 'Logger', pill: true, pillKey: 'loggers' },
    ],
  },
  {
    label: 'Data',
    items: [
      { path: '/history', icon: 'fas fa-database', label: 'Riwayat Data' },
      { path: '/analytics', icon: 'fas fa-chart-line', label: 'Analisis' },
      { path: '/reports', icon: 'fas fa-file-alt', label: 'Laporan' },
    ],
  },
  {
    label: 'Administrasi',
    items: [
      { path: '/sites', icon: 'fas fa-map-marker-alt', label: 'Lokasi' },
      { path: '/devices', icon: 'fas fa-microchip', label: 'Perangkat', hideViewer: true },
      { path: '/users', icon: 'fas fa-users', label: 'Pengguna', adminOnly: true },
      { path: '/settings', icon: 'fas fa-cog', label: 'Pengaturan' },
    ],
  },
];

const visibleGroups = computed(() => {
  return allGroups
    .map((group) => ({
      label: group.label,
      items: group.items.filter((item) => {
        if (item.adminOnly && !isAdmin.value) return false;
        if (item.hideViewer && isViewer.value) return false;
        return true;
      }),
    }))
    .filter((group) => group.items.length > 0);
});

const isActive = (path) => route.path === path;

const userName = computed(() => user.value?.name || user.value?.email || 'User');
const userRole = computed(() => user.value?.role || 'viewer');
const userInitials = computed(() => {
  const name = user.value?.name || user.value?.email || 'U';
  const parts = name.trim().split(/\s+/);
  return parts.length >= 2
    ? (parts[0][0] + parts[1][0]).toUpperCase()
    : name.substring(0, 2).toUpperCase();
});

const handleLogout = async () => {
  await logout();
};
</script>
