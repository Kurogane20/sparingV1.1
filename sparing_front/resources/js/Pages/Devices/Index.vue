<template>
  <AppLayout>
    <div class="space-y-6">
      <!-- Page Header -->
      <div class="flex justify-between items-center">
        <div>
          <h2 class="text-xl font-bold text-slate-800">Manajemen Perangkat IoT</h2>
          <p class="text-slate-500 text-sm mt-0.5">Kelola perangkat sensor dan data logger</p>
        </div>
        <button
          v-if="canManageDevices"
          @click="showAddDeviceModal = true"
          class="btn-primary flex items-center gap-2 text-sm"
        >
          <i class="fas fa-plus text-xs"></i>Tambah Perangkat
        </button>
      </div>

      <!-- Site Selector & Stats -->
      <div class="card p-4 md:p-5">
        <div class="flex flex-col md:flex-row md:items-end gap-4">
          <div class="flex-1">
            <label class="block text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1.5">Lokasi</label>
            <select v-model="selectedSiteUid" @change="loadDevices" class="form-input text-sm md:max-w-sm">
              <option value="">Pilih Lokasi</option>
              <option v-for="site in sites" :key="site.uid" :value="site.uid">
                {{ site.name }} — {{ site.company_name }}
              </option>
            </select>
          </div>

          <!-- Quick Stats -->
          <div v-if="devices.length > 0" class="flex gap-3 shrink-0">
            <div class="flex items-center gap-2 px-3 py-2 rounded-lg bg-emerald-50 border border-emerald-100">
              <span class="w-2 h-2 rounded-full bg-emerald-500"></span>
              <span class="text-sm font-bold font-mono text-emerald-700">{{ activeDevicesCount }}</span>
              <span class="text-xs text-emerald-600">aktif</span>
            </div>
            <div class="flex items-center gap-2 px-3 py-2 rounded-lg bg-slate-50 border border-slate-100">
              <span class="w-2 h-2 rounded-full bg-slate-300"></span>
              <span class="text-sm font-bold font-mono text-slate-500">{{ inactiveDevicesCount }}</span>
              <span class="text-xs text-slate-400">nonaktif</span>
            </div>
            <div class="flex items-center gap-2 px-3 py-2 rounded-lg bg-primary/5 border border-primary/10">
              <i class="fas fa-microchip text-primary/60 text-xs"></i>
              <span class="text-sm font-bold font-mono text-primary">{{ devices.length }}</span>
              <span class="text-xs text-primary/60">total</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Device Cards Grid -->
      <div v-if="viewMode === 'grid' && filteredDevices.length > 0">
        <div class="flex justify-between items-center mb-3">
          <h3 class="card-title">Daftar Perangkat</h3>
          <div class="flex items-center gap-3">
            <label class="flex items-center gap-2 text-xs text-slate-600 cursor-pointer">
              <input v-model="showInactiveDevices" type="checkbox"
                class="w-3.5 h-3.5 text-primary border-slate-300 rounded focus:ring-primary" />
              Tampilkan Nonaktif
            </label>
            <button @click="viewMode = 'table'"
              class="btn-secondary text-xs py-1.5 px-3 flex items-center gap-1.5">
              <i class="fas fa-list text-[10px]"></i>Table
            </button>
          </div>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          <div
            v-for="device in filteredDevices"
            :key="device.id"
            class="card p-5 flex flex-col"
            :style="{ borderLeftWidth: '4px', borderLeftColor: device.is_active ? '#10b981' : '#cbd5e1' }"
          >
            <!-- Device header -->
            <div class="flex justify-between items-start mb-3">
              <div class="flex-1 min-w-0 mr-3">
                <h3 class="font-bold text-slate-800 leading-tight truncate">{{ device.name }}</h3>
                <p class="text-xs text-slate-400 mt-0.5 font-mono">{{ device.model || '—' }}</p>
              </div>
              <span :class="[
                'shrink-0 text-[10px] font-bold px-2 py-0.5 rounded leading-none',
                device.is_active ? 'bg-emerald-50 text-emerald-700' : 'bg-slate-100 text-slate-500'
              ]">
                {{ device.is_active ? 'AKTIF' : 'NONAKTIF' }}
              </span>
            </div>

            <!-- Device meta -->
            <div class="space-y-1.5 mb-4 flex-1 text-xs">
              <div class="flex items-center gap-2 text-slate-500">
                <i class="fas fa-barcode w-3.5 text-center text-primary/60"></i>
                <span class="font-mono">{{ device.serial_no || '—' }}</span>
              </div>
              <div class="flex items-center gap-2 text-slate-500">
                <i class="fas fa-network-wired w-3.5 text-center text-primary/60"></i>
                <span class="font-mono">Modbus {{ device.modbus_addr }}</span>
              </div>
              <!-- Health status -->
              <div class="flex items-center gap-2 text-xs">
                <span class="w-2 h-2 rounded-full shrink-0" :class="healthDotClass(device)"></span>
                <span :class="healthStatusClass(device)" class="capitalize">
                  {{ getHealthStatus(device) !== 'unknown' ? getHealthStatus(device) : 'Tidak diketahui' }}
                </span>
              </div>
              <!-- Last data time -->
              <div v-if="deviceHealth[device.id]" class="flex items-center gap-2 text-xs text-slate-500">
                <i class="fas fa-clock w-3.5 text-center text-primary/60"></i>
                <span>{{ healthLabel(device) }}</span>
              </div>
              <!-- Data count -->
              <div v-if="deviceHealth[device.id]" class="flex items-center gap-2 text-xs text-slate-500">
                <i class="fas fa-database w-3.5 text-center text-primary/60"></i>
                <span class="font-mono">{{ deviceHealth[device.id].data_count_24h }} data/24j</span>
              </div>
              <!-- Last calibration -->
              <div v-if="deviceHealth[device.id]?.last_calibration_at" class="flex items-center gap-2 text-xs text-slate-500">
                <i class="fas fa-tools w-3.5 text-center text-primary/60"></i>
                <span>Kalibrasi: {{ formatDate(deviceHealth[device.id].last_calibration_at) }}</span>
              </div>
              <!-- Next calibration due -->
              <div v-if="deviceHealth[device.id]?.next_calibration_at" class="flex items-center gap-2 text-xs"
                :class="parseUTC(deviceHealth[device.id].next_calibration_at) < new Date() ? 'text-red-500' : parseUTC(deviceHealth[device.id].next_calibration_at) < new Date(Date.now() + 30*24*60*60*1000) ? 'text-amber-500' : 'text-slate-500'"
              >
                <i class="fas fa-calendar-check w-3.5 text-center"></i>
                <span>Berikutnya: {{ formatDate(deviceHealth[device.id].next_calibration_at) }}</span>
              </div>
            </div>

            <!-- Actions -->
            <div class="flex gap-2 pt-3 border-t border-slate-100">
              <button @click="openMaintenanceModal(device)" class="btn-primary flex-1 text-xs py-2">
                <i class="fas fa-clipboard-list mr-1.5"></i>Log
              </button>
              <button v-if="canManageDevices" @click="editDevice(device)"
                class="px-3 py-2 rounded-lg text-xs font-semibold border border-amber-200 text-amber-700 hover:bg-amber-50 transition-colors" title="Edit">
                <i class="fas fa-edit"></i>
              </button>
              <button v-if="canManageDevices" @click="deleteDeviceHandler(device)"
                class="px-3 py-2 rounded-lg text-xs font-semibold border border-red-200 text-red-600 hover:bg-red-50 transition-colors" title="Hapus">
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
              <label class="flex items-center gap-2 text-xs text-slate-600 cursor-pointer">
                <input v-model="showInactiveDevices" type="checkbox"
                  class="w-3.5 h-3.5 text-primary border-slate-300 rounded focus:ring-primary" />
                Tampilkan Nonaktif
              </label>
              <button @click="viewMode = 'grid'"
                class="btn-secondary text-xs py-1.5 px-3 flex items-center gap-1.5">
                <i class="fas fa-th text-[10px]"></i>Grid
              </button>
              <span class="text-xs font-mono text-slate-400">{{ filteredDevices.length }} perangkat</span>
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
        class="fixed inset-0 bg-slate-900/60 backdrop-blur-sm flex items-center justify-center z-50 p-4"
        @click.self="closeModal"
      >
        <div class="bg-white rounded-2xl max-w-lg w-full shadow-2xl max-h-[90vh] overflow-y-auto">
          <div class="flex justify-between items-center px-6 py-4 border-b border-slate-100">
            <div class="flex items-center gap-3">
              <div class="w-8 h-8 rounded-lg bg-emerald-50 flex items-center justify-center">
                <i class="fas fa-microchip text-emerald-600 text-xs"></i>
              </div>
              <h3 class="font-bold text-slate-800">{{ editingDevice ? 'Edit Perangkat' : 'Tambah Perangkat' }}</h3>
            </div>
            <button @click="closeModal" class="w-8 h-8 rounded-lg hover:bg-slate-100 flex items-center justify-center transition-colors">
              <i class="fas fa-times text-slate-400 text-sm"></i>
            </button>
          </div>

          <form @submit.prevent="saveDevice" class="p-6 space-y-4">
            <div>
              <label class="block text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1.5">
                Nama Perangkat <span class="text-red-400 normal-case font-normal">*</span>
              </label>
              <input v-model="deviceForm.name" type="text" required placeholder="e.g., pH Sensor" class="form-input text-sm" />
            </div>

            <div class="grid grid-cols-2 gap-4">
              <div>
                <label class="block text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1.5">Model</label>
                <input v-model="deviceForm.model" type="text" placeholder="e.g., PHM-100" class="form-input text-sm font-mono" />
              </div>
              <div>
                <label class="block text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1.5">Serial Number</label>
                <input v-model="deviceForm.serial_no" type="text" placeholder="e.g., SN123456" class="form-input text-sm font-mono" />
              </div>
            </div>

            <div>
              <label class="block text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1.5">
                Modbus Address <span class="text-red-400 normal-case font-normal">*</span>
              </label>
              <input v-model.number="deviceForm.modbus_addr" type="number" required min="1" max="247"
                placeholder="1–247" class="form-input text-sm font-mono" />
            </div>

            <div class="flex items-center gap-3">
              <input v-model="deviceForm.is_active" type="checkbox" id="dev_is_active"
                class="w-4 h-4 text-primary border-slate-300 rounded focus:ring-primary" />
              <label for="dev_is_active" class="text-sm text-slate-700">Perangkat Aktif</label>
            </div>

            <div v-if="formError" class="p-3 bg-red-50 border border-red-100 rounded-lg text-xs text-red-700 flex items-center gap-2">
              <i class="fas fa-exclamation-circle shrink-0"></i>{{ formError }}
            </div>

            <div class="flex gap-3 justify-end pt-4 border-t border-slate-100">
              <button type="button" @click="closeModal" class="btn-secondary text-sm">Batal</button>
              <button type="submit" :disabled="formLoading"
                class="btn-primary text-sm disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2">
                <i :class="formLoading ? 'fas fa-spinner fa-spin' : 'fas fa-save'" class="text-xs"></i>
                {{ editingDevice ? 'Simpan Perubahan' : 'Tambah Perangkat' }}
              </button>
            </div>
          </form>
        </div>
      </div>

      <!-- Maintenance / Detail Modal -->
      <div
        v-if="maintenanceDevice"
        class="fixed inset-0 bg-slate-900/60 backdrop-blur-sm flex items-center justify-center z-50 p-4"
        @click.self="closeMaintenanceModal"
      >
        <div class="bg-white rounded-2xl max-w-2xl w-full shadow-2xl max-h-[90vh] overflow-y-auto">
          <!-- Modal header -->
          <div class="flex justify-between items-center px-6 py-4 border-b border-slate-100">
            <div class="flex items-center gap-3">
              <div class="w-8 h-8 rounded-lg bg-emerald-50 flex items-center justify-center">
                <i class="fas fa-microchip text-emerald-600 text-xs"></i>
              </div>
              <div>
                <h3 class="font-bold text-slate-800">{{ maintenanceDevice.name }}</h3>
                <p class="text-xs text-slate-400 font-mono">{{ maintenanceDevice.model || '—' }} · SN {{ maintenanceDevice.serial_no || '—' }}</p>
              </div>
            </div>
            <button @click="closeMaintenanceModal" class="w-8 h-8 rounded-lg hover:bg-slate-100 flex items-center justify-center transition-colors">
              <i class="fas fa-times text-slate-400 text-sm"></i>
            </button>
          </div>

          <!-- Tabs -->
          <div class="flex border-b border-slate-100 px-6">
            <button
              @click="maintenanceModalTab = 'info'"
              class="px-4 py-2.5 text-sm font-semibold border-b-2 transition-colors"
              :class="maintenanceModalTab === 'info' ? 'border-primary text-primary' : 'border-transparent text-slate-500 hover:text-slate-700'"
            >
              Info
            </button>
            <button
              @click="maintenanceModalTab = 'log'"
              class="px-4 py-2.5 text-sm font-semibold border-b-2 transition-colors"
              :class="maintenanceModalTab === 'log' ? 'border-primary text-primary' : 'border-transparent text-slate-500 hover:text-slate-700'"
            >
              Log Perawatan
              <span v-if="maintenanceLogs.length" class="ml-1 text-xs font-mono text-slate-400">({{ maintenanceLogs.length }})</span>
            </button>
          </div>

          <!-- Info Tab -->
          <div v-if="maintenanceModalTab === 'info'" class="p-6 space-y-4">
            <div v-if="deviceHealth[maintenanceDevice.id]" class="grid grid-cols-3 gap-3">
              <div class="p-3 rounded-lg bg-slate-50 border border-slate-100 text-center">
                <div class="text-[10px] text-slate-400 uppercase tracking-wide mb-1">Status</div>
                <div class="flex items-center justify-center gap-1.5">
                  <span class="w-2 h-2 rounded-full" :class="healthDotClass(maintenanceDevice)"></span>
                  <span class="text-sm font-bold capitalize" :class="healthStatusClass(maintenanceDevice)">
                    {{ getHealthStatus(maintenanceDevice) }}
                  </span>
                </div>
              </div>
              <div class="p-3 rounded-lg bg-slate-50 border border-slate-100 text-center">
                <div class="text-[10px] text-slate-400 uppercase tracking-wide mb-1">Data 24j</div>
                <div class="text-lg font-bold font-mono text-slate-800">{{ deviceHealth[maintenanceDevice.id].data_count_24h }}</div>
              </div>
              <div class="p-3 rounded-lg bg-slate-50 border border-slate-100 text-center">
                <div class="text-[10px] text-slate-400 uppercase tracking-wide mb-1">Data 7 Hari</div>
                <div class="text-lg font-bold font-mono text-slate-800">{{ deviceHealth[maintenanceDevice.id].data_count_7d }}</div>
              </div>
            </div>

            <div class="space-y-2 text-sm">
              <div class="flex justify-between py-2 border-b border-slate-50">
                <span class="text-slate-500">Nama</span>
                <span class="font-semibold text-slate-800">{{ maintenanceDevice.name }}</span>
              </div>
              <div class="flex justify-between py-2 border-b border-slate-50">
                <span class="text-slate-500">Model</span>
                <span class="font-mono text-slate-700">{{ maintenanceDevice.model || '—' }}</span>
              </div>
              <div class="flex justify-between py-2 border-b border-slate-50">
                <span class="text-slate-500">Serial Number</span>
                <span class="font-mono text-slate-700">{{ maintenanceDevice.serial_no || '—' }}</span>
              </div>
              <div class="flex justify-between py-2 border-b border-slate-50">
                <span class="text-slate-500">Modbus Address</span>
                <span class="font-mono text-slate-700">{{ maintenanceDevice.modbus_addr }}</span>
              </div>
              <div class="flex justify-between py-2">
                <span class="text-slate-500">Status</span>
                <span :class="maintenanceDevice.is_active ? 'text-emerald-600 font-bold' : 'text-slate-400'">
                  {{ maintenanceDevice.is_active ? 'Aktif' : 'Nonaktif' }}
                </span>
              </div>
            </div>
          </div>

          <!-- Log Perawatan Tab -->
          <div v-if="maintenanceModalTab === 'log'" class="p-6">
            <div v-if="loadingLogs" class="text-center text-sm text-slate-400 py-4">
              <i class="fas fa-spinner fa-spin mr-2"></i>Memuat...
            </div>
            <div v-else>
              <div v-if="!maintenanceLogs.length && !showAddLogForm" class="text-center text-sm text-slate-400 py-4">
                Belum ada log perawatan.
              </div>
              <div v-else class="space-y-3 mb-4">
                <div
                  v-for="log in maintenanceLogs"
                  :key="log.id"
                  class="flex gap-3 p-3 rounded-lg border border-slate-100 bg-slate-50"
                >
                  <div class="shrink-0 mt-0.5">
                    <span class="text-[10px] font-bold px-2 py-0.5 rounded uppercase tracking-wide bg-emerald-50 text-emerald-700 border border-emerald-100" v-if="log.type === 'calibration'">Kalibrasi</span>
                    <span class="text-[10px] font-bold px-2 py-0.5 rounded uppercase tracking-wide bg-red-50 text-red-700 border border-red-100" v-else-if="log.type === 'repair'">Perbaikan</span>
                    <span class="text-[10px] font-bold px-2 py-0.5 rounded uppercase tracking-wide bg-blue-50 text-blue-700 border border-blue-100" v-else-if="log.type === 'inspection'">Inspeksi</span>
                    <span class="text-[10px] font-bold px-2 py-0.5 rounded uppercase tracking-wide bg-slate-100 text-slate-600 border border-slate-200" v-else>{{ getLogTypeLabel(log.type) }}</span>
                  </div>
                  <div class="flex-1 min-w-0">
                    <div class="text-xs text-slate-500 font-mono">{{ formatDate(log.performed_at) }}</div>
                    <div v-if="log.notes" class="text-sm text-slate-700 mt-0.5">{{ log.notes }}</div>
                    <div v-if="log.next_due_at" class="text-xs text-amber-600 mt-1">
                      <i class="fas fa-calendar-alt mr-1"></i>
                      Berikutnya: {{ formatDate(log.next_due_at) }}
                    </div>
                    <div v-if="log.performed_by_name" class="text-xs text-slate-400 mt-1">
                      <i class="fas fa-user mr-1"></i>{{ log.performed_by_name }}
                    </div>
                  </div>
                  <button
                    v-if="canManageDevices"
                    @click="removeLog(log.id)"
                    class="shrink-0 text-slate-300 hover:text-red-400 transition-colors"
                  >
                    <i class="fas fa-times text-xs"></i>
                  </button>
                </div>
              </div>

              <div v-if="showAddLogForm && canManageDevices" class="p-4 rounded-lg border border-primary/20 bg-primary/5 space-y-3 mb-3">
                <div class="grid grid-cols-2 gap-3">
                  <div>
                    <label class="block text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1.5">Tipe</label>
                    <select v-model="newLog.type" class="form-input text-sm">
                      <option v-for="t in LOG_TYPES" :key="t.key" :value="t.key">{{ t.label }}</option>
                    </select>
                  </div>
                  <div>
                    <label class="block text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1.5">Tanggal Pelaksanaan</label>
                    <input v-model="newLog.performed_at" type="datetime-local" class="form-input text-sm" />
                  </div>
                </div>
                <div>
                  <label class="block text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1.5">Catatan</label>
                  <textarea v-model="newLog.notes" rows="2" class="form-input text-sm resize-none" placeholder="Opsional..."></textarea>
                </div>
                <div v-if="newLog.type === 'calibration'">
                  <label class="block text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1.5">Jadwal Kalibrasi Berikutnya</label>
                  <input v-model="newLog.next_due_at" type="date" class="form-input text-sm" />
                </div>
                <div class="flex gap-2">
                  <button @click="submitLog" :disabled="addingLog" class="btn-primary text-sm disabled:opacity-50">
                    <i :class="addingLog ? 'fas fa-spinner fa-spin' : 'fas fa-save'" class="mr-1.5 text-xs"></i>Simpan
                  </button>
                  <button @click="showAddLogForm = false" class="btn-secondary text-sm">Batal</button>
                </div>
              </div>

              <button
                v-if="!showAddLogForm && canManageDevices"
                @click="showAddLogForm = true"
                class="btn-secondary text-sm flex items-center gap-1.5"
              >
                <i class="fas fa-plus text-xs"></i>Tambah Catatan
              </button>
            </div>
          </div>
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
import { useToast } from '@/Composables/useToast';
import { useConfirm } from '@/Composables/useConfirm';
import { getRelativeTime, formatDate, parseUTC } from '@/Utils/helpers';
import logger from '@/Utils/logger';

// Composables
const { getSites, getDevices, createDevice, updateDevice, deleteDevice, getSiteStats, getDeviceHealth, getMaintenanceLogs, addMaintenanceLog, deleteMaintenanceLog } = useApi();
const { isOperator, filterSitesByUser } = useAuth();
const toast = useToast();
const { confirm } = useConfirm();

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

// Device health data keyed by device id
const deviceHealth = ref({});

// Maintenance modal state
const maintenanceDevice = ref(null);
const maintenanceModalTab = ref('info');
const maintenanceLogs = ref([]);
const loadingLogs = ref(false);
const addingLog = ref(false);
const newLog = ref({
  type: 'calibration',
  notes: '',
  performed_at: new Date().toISOString().slice(0, 16),
  next_due_at: '',
});
const showAddLogForm = ref(false);

const LOG_TYPES = [
  { key: 'calibration', label: 'Kalibrasi', color: 'emerald' },
  { key: 'repair',      label: 'Perbaikan', color: 'red' },
  { key: 'inspection',  label: 'Inspeksi',  color: 'blue' },
  { key: 'note',        label: 'Catatan',   color: 'slate' },
];

const getLogTypeLabel = (type) => LOG_TYPES.find(t => t.key === type)?.label || type;
const getLogTypeColor = (type) => LOG_TYPES.find(t => t.key === type)?.color || 'slate';

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
      logger.warn('Unexpected sites API response format:', response);
    }

    // Filter sites based on user permissions
    sites.value = filterSitesByUser(sitesList);

    // Auto-select first site
    if (sites.value.length > 0) {
      selectedSiteUid.value = sites.value[0].uid;
      await loadDevices();
    }
  } catch (error) {
    logger.error('Failed to load sites:', error);
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
      logger.warn('Unexpected devices API response format:', response);
    }

    devices.value = devicesList;

    if (devices.value.length > 0) {
      loadHealthForDevices(devices.value);
    }

    // Load last seen stats for the site
    await loadSiteStats();
  } catch (error) {
    logger.error('Failed to load devices:', error);
    devices.value = [];
  } finally {
    loading.value = false;
  }
};

const loadHealthForDevices = async (deviceList) => {
  await Promise.allSettled(
    deviceList.map(async (device) => {
      try {
        const health = await getDeviceHealth(device.id);
        deviceHealth.value = { ...deviceHealth.value, [device.id]: health };
      } catch {
        // silent
      }
    })
  );
};

const getHealthStatus = (device) => deviceHealth.value[device.id]?.status || 'unknown';

const healthStatusClass = (device) => {
  const s = getHealthStatus(device);
  if (s === 'online')  return 'text-emerald-600';
  if (s === 'warning') return 'text-amber-500';
  if (s === 'offline') return 'text-red-500';
  return 'text-slate-400';
};

const healthDotClass = (device) => {
  const s = getHealthStatus(device);
  if (s === 'online')  return 'bg-emerald-500 animate-pulse';
  if (s === 'warning') return 'bg-amber-400';
  if (s === 'offline') return 'bg-red-500';
  return 'bg-slate-300';
};

const healthLabel = (device) => {
  const h = deviceHealth.value[device.id];
  const s = getHealthStatus(device);
  if (s === 'unknown') return 'Belum ada data';
  if (!h?.last_seen) return 'Tidak diketahui';
  return getRelativeTime(h.last_seen);
};

const openMaintenanceModal = async (device) => {
  maintenanceDevice.value = device;
  maintenanceModalTab.value = 'info';
  showAddLogForm.value = false;
  newLog.value = { type: 'calibration', notes: '', performed_at: new Date().toISOString().slice(0, 16), next_due_at: '' };
  await loadMaintenanceLogs(device.id);
};

const loadMaintenanceLogs = async (deviceId) => {
  loadingLogs.value = true;
  try {
    const res = await getMaintenanceLogs(deviceId);
    maintenanceLogs.value = Array.isArray(res) ? res : [];
  } catch {
    maintenanceLogs.value = [];
  } finally {
    loadingLogs.value = false;
  }
};

const submitLog = async () => {
  if (!maintenanceDevice.value) return;
  addingLog.value = true;
  try {
    await addMaintenanceLog(maintenanceDevice.value.id, {
      type: newLog.value.type,
      notes: newLog.value.notes || null,
      performed_at: new Date(newLog.value.performed_at).toISOString(),
      next_due_at: newLog.value.next_due_at ? new Date(newLog.value.next_due_at).toISOString() : null,
    });
    await loadMaintenanceLogs(maintenanceDevice.value.id);
    showAddLogForm.value = false;
    newLog.value = { type: 'calibration', notes: '', performed_at: new Date().toISOString().slice(0, 16), next_due_at: '' };
    toast.success('Log berhasil ditambahkan');
  } catch {
    toast.error('Gagal menyimpan log');
  } finally {
    addingLog.value = false;
  }
};

const removeLog = async (logId) => {
  if (!maintenanceDevice.value) return;
  const ok = await confirm('Hapus catatan ini?');
  if (!ok) return;
  try {
    await deleteMaintenanceLog(maintenanceDevice.value.id, logId);
    maintenanceLogs.value = maintenanceLogs.value.filter(l => l.id !== logId);
    toast.success('Log dihapus');
  } catch {
    toast.error('Gagal menghapus log');
  }
};

const closeMaintenanceModal = () => {
  maintenanceDevice.value = null;
  maintenanceLogs.value = [];
  showAddLogForm.value = false;
};

// Load site stats to get last seen time
const loadSiteStats = async () => {
  if (!selectedSiteUid.value) return;

  try {
    const stats = await getSiteStats(selectedSiteUid.value);
    deviceStats.value[selectedSiteUid.value] = stats;
  } catch (error) {
    logger.error('Failed to load site stats:', error);
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
  if (!stats?.last_seen_at) return 'text-slate-400';

  const minutesAgo = stats.minutes_ago || 0;
  if (minutesAgo < 5) return 'text-green-600';
  if (minutesAgo < 30) return 'text-yellow-600';
  return 'text-red-600';
};

// View device detail
const viewDeviceDetail = (device) => {
  logger.log('View device detail:', device);
  toast.info(`${device.name} | Model: ${device.model || '-'} | Modbus: ${device.modbus_addr || '-'}`);
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
  const ok = await confirm(`${action.charAt(0).toUpperCase() + action.slice(1)} perangkat "${device.name}"?`);
  if (!ok) return;

  try {
    await updateDevice(device.id, { is_active: !device.is_active });
    await loadDevices();
  } catch (error) {
    logger.error('Failed to toggle device status:', error);
    toast.error('Gagal mengubah status perangkat');
  }
};

// Delete device
const deleteDeviceHandler = async (device) => {
  const ok = await confirm(`Hapus perangkat "${device.name}"? Tindakan ini tidak dapat dibatalkan.`);
  if (!ok) return;

  try {
    await deleteDevice(device.id);
    await loadDevices();
    toast.success('Perangkat berhasil dihapus');
  } catch (error) {
    logger.error('Failed to delete device:', error);
    toast.error('Gagal menghapus perangkat');
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
