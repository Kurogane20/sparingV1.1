<template>
  <AppLayout>
    <div class="space-y-6">
      <!-- Page Header -->
      <div class="flex justify-between items-center">
        <div>
          <h2 class="text-2xl font-bold text-gray-900">Manajemen Perangkat IoT</h2>
          <p class="text-gray-600 text-sm mt-1">
            Kelola perangkat sensor dan data logger
          </p>
        </div>
        <button
          v-if="canManageDevices"
          @click="showAddDeviceModal = true"
          class="px-4 py-2 bg-primary text-white rounded-lg hover:bg-opacity-90 flex items-center gap-2"
        >
          <i class="fas fa-plus"></i>
          Tambah Perangkat
        </button>
      </div>

      <!-- Site Selector & Stats -->
      <div class="bg-white rounded-2xl p-6 shadow-sm">
        <div class="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div class="flex-1">
            <label class="block text-sm font-medium text-gray-700 mb-2">
              <i class="fas fa-map-marker-alt text-primary mr-1"></i>
              Pilih Lokasi
            </label>
            <select
              v-model="selectedSiteUid"
              @change="loadDevices"
              class="w-full md:w-96 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary"
            >
              <option value="">Pilih Lokasi</option>
              <option v-for="site in sites" :key="site.uid" :value="site.uid">
                {{ site.name }} - {{ site.company_name }}
              </option>
            </select>
          </div>

          <!-- Quick Stats -->
          <div v-if="devices.length > 0" class="flex gap-4">
            <div class="text-center">
              <div class="text-2xl font-bold text-green-600">{{ activeDevicesCount }}</div>
              <div class="text-xs text-gray-600">Aktif</div>
            </div>
            <div class="text-center">
              <div class="text-2xl font-bold text-gray-400">{{ inactiveDevicesCount }}</div>
              <div class="text-xs text-gray-600">Nonaktif</div>
            </div>
            <div class="text-center">
              <div class="text-2xl font-bold text-primary">{{ devices.length }}</div>
              <div class="text-xs text-gray-600">Total</div>
            </div>
          </div>
        </div>
      </div>

      <!-- Device Cards Grid (Optional, can toggle view) -->
      <div v-if="viewMode === 'grid' && filteredDevices.length > 0">
        <div class="flex justify-between items-center mb-4">
          <h3 class="text-lg font-semibold text-gray-900">
            <i class="fas fa-microchip text-primary mr-2"></i>
            Daftar Perangkat
          </h3>
          <div class="flex items-center gap-3">
            <label class="flex items-center gap-2 text-sm text-gray-700 cursor-pointer">
              <input
                v-model="showInactiveDevices"
                type="checkbox"
                class="w-4 h-4 text-primary border-gray-300 rounded focus:ring-primary"
              />
              Tampilkan Nonaktif
            </label>
            <button
              @click="viewMode = 'table'"
              class="px-3 py-1.5 text-sm bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 flex items-center gap-2"
            >
              <i class="fas fa-list"></i> Table View
            </button>
          </div>
        </div>
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        <div
          v-for="device in filteredDevices"
          :key="device.id"
          class="bg-white rounded-2xl p-6 shadow-sm hover:shadow-md transition-shadow"
        >
          <div class="flex justify-between items-start mb-4">
            <div class="flex-1">
              <h3 class="text-lg font-semibold text-gray-900">{{ device.name }}</h3>
              <p class="text-sm text-gray-600">{{ device.model || 'No model' }}</p>
            </div>
            <StatusBadge
              :status="device.is_active ? 'active' : 'inactive'"
              :label="device.is_active ? 'Aktif' : 'Nonaktif'"
            />
          </div>

          <div class="space-y-2 text-sm mb-4">
            <div class="flex items-center gap-2 text-gray-600">
              <i class="fas fa-barcode text-primary w-4"></i>
              <span>SN: {{ device.serial_no || '-' }}</span>
            </div>
            <div class="flex items-center gap-2 text-gray-600">
              <i class="fas fa-network-wired text-primary w-4"></i>
              <span>Modbus: {{ device.modbus_addr }}</span>
            </div>
            <div class="flex items-center gap-2">
              <i class="fas fa-clock text-primary w-4"></i>
              <span :class="getLastSeenColorClass(device)">
                {{ getConnectionStatus(device) }}
              </span>
            </div>
          </div>

          <div class="flex gap-2 pt-4 border-t">
            <button
              @click="viewDeviceDetail(device)"
              class="flex-1 px-3 py-2 bg-primary text-white rounded-lg hover:bg-opacity-90 text-sm"
            >
              <i class="fas fa-eye mr-1"></i> Detail
            </button>
            <button
              v-if="canManageDevices"
              @click="editDevice(device)"
              class="px-3 py-2 bg-yellow-500 text-white rounded-lg hover:bg-opacity-90 text-sm"
              title="Edit"
            >
              <i class="fas fa-edit"></i>
            </button>
            <button
              v-if="canManageDevices"
              @click="deleteDeviceHandler(device)"
              class="px-3 py-2 bg-red-500 text-white rounded-lg hover:bg-opacity-90 text-sm"
              title="Hapus"
            >
              <i class="fas fa-trash"></i>
            </button>
          </div>
        </div>
        </div>
      </div>

      <!-- View Mode Toggle & Devices Table -->
      <div v-if="viewMode === 'table'">
        <DataTable
          title="Daftar Perangkat"
          :data="filteredDevices"
          :columns="deviceColumns"
          :loading="loading"
          empty-message="Tidak ada perangkat terdaftar di lokasi ini"
        >
          <template #actions>
            <div class="flex items-center gap-3">
              <label class="flex items-center gap-2 text-sm text-gray-700 cursor-pointer">
                <input
                  v-model="showInactiveDevices"
                  type="checkbox"
                  class="w-4 h-4 text-primary border-gray-300 rounded focus:ring-primary"
                />
                Tampilkan Nonaktif
              </label>
              <button
                @click="viewMode = 'grid'"
                class="px-3 py-1.5 text-sm bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 flex items-center gap-2"
              >
                <i class="fas fa-th"></i> Grid View
              </button>
              <div class="text-sm text-gray-600">
                Total: {{ filteredDevices.length }} perangkat
              </div>
            </div>
          </template>

        <template #cell-status="{ row }">
          <StatusBadge
            :status="row.is_active ? 'active' : 'inactive'"
            :label="row.is_active ? 'Aktif' : 'Nonaktif'"
          />
        </template>

        <template #cell-last_seen="{ row }">
          <div class="text-sm">
            <div>{{ getLastSeenText(row) }}</div>
            <div class="text-xs" :class="getLastSeenColorClass(row)">
              {{ getConnectionStatus(row) }}
            </div>
          </div>
        </template>

        <template #cell-actions="{ row }">
          <div class="flex items-center gap-3">
            <button
              @click="viewDeviceDetail(row)"
              class="text-secondary hover:underline text-sm"
              title="Lihat Detail"
            >
              <i class="fas fa-eye"></i>
            </button>
            <button
              v-if="canManageDevices"
              @click="editDevice(row)"
              class="text-yellow-600 hover:underline text-sm"
              title="Edit"
            >
              <i class="fas fa-edit"></i>
            </button>
            <button
              v-if="canManageDevices"
              @click="deleteDeviceHandler(row)"
              class="text-red-600 hover:underline text-sm"
              title="Hapus"
            >
              <i class="fas fa-trash"></i>
            </button>
          </div>
        </template>
      </DataTable>
      </div>

      <!-- Add/Edit Device Modal -->
      <div
        v-if="showAddDeviceModal || editingDevice"
        class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4"
        @click.self="closeModal"
      >
        <div class="bg-white rounded-2xl max-w-2xl w-full p-6 max-h-[90vh] overflow-y-auto">
          <div class="flex justify-between items-center mb-4">
            <h3 class="text-xl font-bold text-gray-900">
              {{ editingDevice ? 'Edit Perangkat' : 'Tambah Perangkat Baru' }}
            </h3>
            <button @click="closeModal" class="text-gray-400 hover:text-gray-600">
              <i class="fas fa-times text-xl"></i>
            </button>
          </div>

          <form @submit.prevent="saveDevice" class="space-y-4">
            <!-- Device Name -->
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-2">
                Nama Perangkat <span class="text-red-500">*</span>
              </label>
              <input
                v-model="deviceForm.name"
                type="text"
                required
                class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary"
                placeholder="e.g., pH Sensor"
              />
            </div>

            <!-- Model -->
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-2">
                Model
              </label>
              <input
                v-model="deviceForm.model"
                type="text"
                class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary"
                placeholder="e.g., PHM-100"
              />
            </div>

            <!-- Serial Number -->
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-2">
                Serial Number
              </label>
              <input
                v-model="deviceForm.serial_no"
                type="text"
                class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary"
                placeholder="e.g., SN123456"
              />
            </div>

            <!-- Modbus Address -->
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-2">
                Modbus Address <span class="text-red-500">*</span>
              </label>
              <input
                v-model.number="deviceForm.modbus_addr"
                type="number"
                required
                min="1"
                max="247"
                class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary"
                placeholder="1-247"
              />
            </div>

            <!-- Active Status -->
            <div class="flex items-center gap-3">
              <input
                v-model="deviceForm.is_active"
                type="checkbox"
                id="is_active"
                class="w-4 h-4 text-primary border-gray-300 rounded focus:ring-primary"
              />
              <label for="is_active" class="text-sm font-medium text-gray-700">
                Perangkat Aktif
              </label>
            </div>

            <!-- Error Message -->
            <div
              v-if="formError"
              class="p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-800"
            >
              {{ formError }}
            </div>

            <!-- Form Actions -->
            <div class="flex gap-3 justify-end pt-4 border-t">
              <button
                type="button"
                @click="closeModal"
                class="px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300"
              >
                Batal
              </button>
              <button
                type="submit"
                :disabled="formLoading"
                class="px-4 py-2 bg-primary text-white rounded-lg hover:bg-opacity-90 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
              >
                <i v-if="formLoading" class="fas fa-spinner fa-spin"></i>
                {{ editingDevice ? 'Simpan Perubahan' : 'Tambah Perangkat' }}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  </AppLayout>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import AppLayout from '@/Layouts/AppLayout.vue';
import DataTable from '@/Components/DataTable.vue';
import StatusBadge from '@/Components/StatusBadge.vue';
import { useApi } from '@/Composables/useApi';
import { useAuth } from '@/Composables/useAuth';
import { getRelativeTime } from '@/Utils/helpers';

// Composables
const { getSites, getDevices, createDevice, updateDevice, deleteDevice, getSiteStats } = useApi();
const { isOperator, filterSitesByUser } = useAuth();

// State
const sites = ref([]);
const devices = ref([]);
const selectedSiteUid = ref('');
const loading = ref(false);
const showAddDeviceModal = ref(false);
const editingDevice = ref(null);
const formLoading = ref(false);
const formError = ref(null);
const viewMode = ref('table'); // 'table' or 'grid'
const showInactiveDevices = ref(false); // Toggle to show inactive devices

// Device stats (last seen timestamps)
const deviceStats = ref({});

// Device form
const deviceForm = ref({
  name: '',
  model: '',
  serial_no: '',
  modbus_addr: 1,
  is_active: true,
});

// Permission check
const canManageDevices = computed(() => isOperator.value);

// Device statistics
const activeDevicesCount = computed(() => {
  return devices.value.filter(d => d.is_active).length;
});

const inactiveDevicesCount = computed(() => {
  return devices.value.filter(d => !d.is_active).length;
});

// Filtered devices based on show inactive toggle
const filteredDevices = computed(() => {
  if (showInactiveDevices.value) {
    return devices.value; // Show all devices
  }
  return devices.value.filter(d => d.is_active !== false); // Show only active devices
});

// Device table columns
const deviceColumns = [
  { key: 'id', label: 'ID', format: (val) => `#${String(val).padStart(3, '0')}` },
  { key: 'name', label: 'Nama Perangkat' },
  { key: 'model', label: 'Model' },
  { key: 'serial_no', label: 'Serial Number' },
  { key: 'modbus_addr', label: 'Modbus Addr' },
  { key: 'last_seen', label: 'Terakhir Terlihat' },
  { key: 'status', label: 'Status' },
  { key: 'actions', label: 'Aksi' },
];

// Load sites
const loadSites = async () => {
  try {
    const response = await getSites({ per_page: 100 });
    // Handle different possible response structures
    let sitesList = [];
    if (response && response.items) {
      sitesList = response.items;
    } else if (Array.isArray(response)) {
      sitesList = response;
    } else if (response && response.data) {
      sitesList = Array.isArray(response.data) ? response.data : [];
    } else {
      console.warn('Unexpected sites API response format:', response);
    }

    // Filter sites based on user permissions
    sites.value = filterSitesByUser(sitesList);

    // Auto-select first site
    if (sites.value.length > 0) {
      selectedSiteUid.value = sites.value[0].uid;
      await loadDevices();
    }
  } catch (error) {
    console.error('Failed to load sites:', error);
    sites.value = [];
  }
};

// Load devices for selected site
const loadDevices = async () => {
  if (!selectedSiteUid.value) {
    devices.value = [];
    return;
  }

  loading.value = true;

  try {
    const response = await getDevices({ site_uid: selectedSiteUid.value });
    // Handle different possible response structures
    let devicesList = [];
    if (response && response.items) {
      devicesList = response.items;
    } else if (Array.isArray(response)) {
      devicesList = response;
    } else if (response && response.data) {
      devicesList = Array.isArray(response.data) ? response.data : [];
    } else {
      console.warn('Unexpected devices API response format:', response);
    }

    devices.value = devicesList;

    // Load last seen stats for the site
    await loadSiteStats();
  } catch (error) {
    console.error('Failed to load devices:', error);
    devices.value = [];
  } finally {
    loading.value = false;
  }
};

// Load site stats to get last seen time
const loadSiteStats = async () => {
  if (!selectedSiteUid.value) return;

  try {
    const stats = await getSiteStats(selectedSiteUid.value);
    deviceStats.value[selectedSiteUid.value] = stats;
  } catch (error) {
    console.error('Failed to load site stats:', error);
  }
};

// Get last seen text for device
const getLastSeenText = (device) => {
  const stats = deviceStats.value[selectedSiteUid.value];
  if (!stats?.last_seen_at) return 'Tidak ada data';
  return getRelativeTime(stats.last_seen_at);
};

// Get connection status text
const getConnectionStatus = (device) => {
  const stats = deviceStats.value[selectedSiteUid.value];
  if (!stats?.last_seen_at) return 'Belum pernah terhubung';

  const minutesAgo = stats.minutes_ago || 0;
  if (minutesAgo < 5) return 'Online';
  if (minutesAgo < 30) return 'Idle';
  return 'Offline';
};

// Get color class for last seen
const getLastSeenColorClass = (device) => {
  const stats = deviceStats.value[selectedSiteUid.value];
  if (!stats?.last_seen_at) return 'text-gray-400';

  const minutesAgo = stats.minutes_ago || 0;
  if (minutesAgo < 5) return 'text-green-600';
  if (minutesAgo < 30) return 'text-yellow-600';
  return 'text-red-600';
};

// View device detail
const viewDeviceDetail = (device) => {
  // TODO: Navigate to device detail page or show detail modal
  console.log('View device detail:', device);
  alert(`Detail perangkat: ${device.name}\nModel: ${device.model}\nModbus: ${device.modbus_addr}`);
};

// Edit device
const editDevice = (device) => {
  editingDevice.value = device;
  deviceForm.value = { ...device };
  formError.value = null;
};

// Toggle device status
const toggleDeviceStatus = async (device) => {
  const action = device.is_active ? 'menonaktifkan' : 'mengaktifkan';
  if (!confirm(`Apakah Anda yakin ingin ${action} perangkat ini?`)) {
    return;
  }

  try {
    await updateDevice(device.id, { is_active: !device.is_active });
    await loadDevices(); // Reload devices
  } catch (error) {
    console.error('Failed to toggle device status:', error);
    alert('Gagal mengubah status perangkat');
  }
};

// Delete device
const deleteDeviceHandler = async (device) => {
  if (!confirm(`Apakah Anda yakin ingin menghapus perangkat "${device.name}"? Tindakan ini tidak dapat dibatalkan.`)) {
    return;
  }

  try {
    await deleteDevice(device.id);
    await loadDevices(); // Reload devices
    alert('Perangkat berhasil dihapus');
  } catch (error) {
    console.error('Failed to delete device:', error);
    alert('Gagal menghapus perangkat');
  }
};

// Save device (create or update)
const saveDevice = async () => {
  formLoading.value = true;
  formError.value = null;

  try {
    const payload = {
      ...deviceForm.value,
      site_uid: selectedSiteUid.value,
    };

    if (editingDevice.value) {
      // Update existing device
      await updateDevice(editingDevice.value.id, payload);
      await loadDevices(); // Reload devices
      closeModal();
    } else {
      // Create new device
      await createDevice(payload);
      await loadDevices(); // Reload devices
      closeModal();
    }
  } catch (error) {
    formError.value = error.response?.data?.detail || 'Gagal menyimpan perangkat';
  } finally {
    formLoading.value = false;
  }
};

// Close modal
const closeModal = () => {
  showAddDeviceModal.value = false;
  editingDevice.value = null;
  deviceForm.value = {
    name: '',
    model: '',
    serial_no: '',
    modbus_addr: 1,
    is_active: true,
  };
  formError.value = null;
};

// Initialize
onMounted(async () => {
  await loadSites();
});
</script>
