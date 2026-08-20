<template>
  <AppLayout>
    <PageHeader
      :crumb="['Beranda', 'Administrasi', 'Perangkat']"
      title="Manajemen Perangkat"
      subtitle="Perangkat logger di tiap lokasi — status diambil dari heartbeat logger"
    >
      <template #actions>
        <select
          v-model="selectedSiteUid"
          @change="loadDevices"
          class="border border-[#C4D1D3] rounded-md px-3 py-2 text-sm text-ink bg-white max-w-[220px]"
        >
          <option value="">Pilih Lokasi</option>
          <option v-for="site in sites" :key="site.uid" :value="site.uid">
            {{ site.name }} — {{ site.company_name }}
          </option>
        </select>
        <button
          type="button"
          class="px-3 py-2 rounded-md border border-[#D7E0E1] text-sm text-ink hover:bg-[#EEF2F3] transition-colors flex items-center gap-2"
          @click="viewMode = viewMode === 'grid' ? 'table' : 'grid'"
        >
          <i :class="viewMode === 'grid' ? 'fas fa-list' : 'fas fa-th'" class="text-xs"></i>
          {{ viewMode === 'grid' ? 'Tabel' : 'Grid' }}
        </button>
        <button
          v-if="canManageDevices"
          type="button"
          class="px-3 py-2 rounded-md text-sm text-white bg-primary hover:bg-primary-dark transition-colors flex items-center gap-2"
          @click="showAddDeviceModal = true"
        >
          <i class="fas fa-plus text-xs"></i>Tambah Perangkat
        </button>
      </template>
    </PageHeader>

    <!-- Quick stats -->
    <div v-if="devices.length > 0" class="flex flex-wrap gap-3 mb-4">
      <div class="flex items-center gap-2 px-3 py-2 rounded-lg bg-white border border-[#D7E0E1]">
        <span class="w-2 h-2 rounded-full bg-success"></span>
        <span class="text-sm font-bold font-mono text-ink">{{ activeDevicesCount }}</span>
        <span class="text-xs text-[#617377]">aktif</span>
      </div>
      <div class="flex items-center gap-2 px-3 py-2 rounded-lg bg-white border border-[#D7E0E1]">
        <span class="w-2 h-2 rounded-full bg-[#C4D1D3]"></span>
        <span class="text-sm font-bold font-mono text-ink">{{ inactiveDevicesCount }}</span>
        <span class="text-xs text-[#617377]">nonaktif</span>
      </div>
      <div class="flex items-center gap-2 px-3 py-2 rounded-lg bg-[#E4F1F2] border border-[#D7E0E1]">
        <i class="fas fa-microchip text-[#0A5A62] text-xs"></i>
        <span class="text-sm font-bold font-mono text-[#0A5A62]">{{ devices.length }}</span>
        <span class="text-xs text-[#0A5A62]">total</span>
      </div>
      <label class="flex items-center gap-2 text-xs text-ink cursor-pointer ml-auto px-1">
        <input v-model="showInactiveDevices" type="checkbox"
          class="w-3.5 h-3.5 text-primary border-[#C4D1D3] rounded focus:ring-primary" />
        Tampilkan Nonaktif
      </label>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="bg-white border border-[#D7E0E1] rounded-lg p-10 text-center text-[#617377] text-sm">
      <i class="fas fa-spinner fa-spin mr-2"></i>Memuat perangkat…
    </div>

    <!-- Empty -->
    <div v-else-if="!filteredDevices.length" class="bg-white border border-[#D7E0E1] rounded-lg p-10 text-center text-[#617377] text-sm">
      Tidak ada perangkat terdaftar di lokasi ini.
    </div>

    <!-- Grid view -->
    <div v-else-if="viewMode === 'grid'" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      <div
        v-for="device in filteredDevices"
        :key="device.id"
        class="bg-white border border-[#D7E0E1] rounded-lg p-5 flex flex-col"
        :style="{ borderLeftWidth: '4px', borderLeftColor: device.is_active ? '#1F7A4D' : '#C4D1D3' }"
      >
        <!-- Device header -->
        <div class="flex justify-between items-start mb-3">
          <div class="flex-1 min-w-0 mr-3">
            <h3 class="font-bold text-ink leading-tight truncate">{{ device.name }}</h3>
            <p class="text-xs text-[#617377] mt-0.5 font-mono">{{ device.model || '—' }}</p>
          </div>
          <span :class="[
            'shrink-0 text-[10px] font-bold px-2 py-0.5 rounded leading-none',
            device.is_active ? 'bg-[#E6F2EC] text-success' : 'bg-[#EAEEEF] text-[#6E7E82]'
          ]">
            {{ device.is_active ? 'AKTIF' : 'NONAKTIF' }}
          </span>
        </div>

        <!-- Device meta -->
        <div class="space-y-1.5 mb-3 text-xs">
          <div class="flex items-center gap-2 text-[#617377]">
            <i class="fas fa-barcode w-3.5 text-center text-primary/60"></i>
            <span class="font-mono">{{ device.serial_no || '—' }}</span>
          </div>
          <div class="flex items-center gap-2 text-[#617377]">
            <i class="fas fa-network-wired w-3.5 text-center text-primary/60"></i>
            <span class="font-mono">Modbus {{ device.modbus_addr }}</span>
          </div>
        </div>

        <!-- Status block -->
        <div class="mb-4 flex-1 p-3 rounded-lg bg-[#F7FAFA] border border-[#EEF2F3]">
          <div class="flex items-center justify-between mb-1.5">
            <span class="px-2 py-1 rounded-full text-[11px] font-semibold" :style="deviceStatusView(device).style">
              {{ deviceStatusView(device).label }}
            </span>
            <span class="text-[10px] text-[#617377] italic">{{ deviceStatusView(device).source === 'logger' ? 'dari logger' : 'dari data' }}</span>
          </div>
          <div class="text-[11px] text-[#617377] mb-2">
            <i class="fas fa-clock w-3.5 text-center mr-1"></i>
            {{ deviceStatusView(device).lastSeen ? getRelativeTime(deviceStatusView(device).lastSeen) : 'Belum ada data' }}
          </div>

          <template v-if="deviceStatusView(device).source === 'logger'">
            <div class="flex items-center gap-1.5 mb-2">
              <span
                v-for="s in sensorDots(deviceStatusView(device).sensors)"
                :key="s.key"
                class="w-2.5 h-2.5 rounded-full"
                :class="s.class"
                :title="s.title"
              ></span>
            </div>
            <div class="text-[10.5px] text-[#617377] font-mono">
              <span v-if="deviceStatusView(device).cpu_pct != null">CPU {{ Math.round(deviceStatusView(device).cpu_pct) }}%</span>
              <span v-if="deviceStatusView(device).mem_pct != null"> · RAM {{ Math.round(deviceStatusView(device).mem_pct) }}%</span>
              <span v-if="deviceStatusView(device).disk_pct != null"> · Disk {{ Math.round(deviceStatusView(device).disk_pct) }}%</span>
            </div>
          </template>

          <!-- Health (data-derived) -->
          <div v-if="deviceHealth[device.id]" class="flex items-center gap-2 text-[11px] text-[#617377] mt-1.5">
            <i class="fas fa-database w-3.5 text-center text-primary/60"></i>
            <span class="font-mono">{{ deviceHealth[device.id].data_count_24h }} data/24j</span>
          </div>
        </div>

        <!-- Actions -->
        <div class="flex gap-2 pt-3 border-t border-[#EEF2F3]">
          <button @click="openMaintenanceModal(device)" class="flex-1 text-xs py-2 rounded-md text-white bg-primary hover:bg-primary-dark transition-colors">
            <i class="fas fa-clipboard-list mr-1.5"></i>Log
          </button>
          <button v-if="canManageDevices" @click="editDevice(device)"
            class="px-3 py-2 rounded-md text-xs font-semibold border border-[#F0DDA6] text-warning hover:bg-[#F7EFD9] transition-colors" title="Edit">
            <i class="fas fa-edit"></i>
          </button>
          <button v-if="canManageDevices" @click="deleteDeviceHandler(device)"
            class="px-3 py-2 rounded-md text-xs font-semibold border border-[#EEC5C5] text-danger hover:bg-[#F7E4E4] transition-colors" title="Hapus">
            <i class="fas fa-trash"></i>
          </button>
        </div>
      </div>
    </div>

    <!-- Table view -->
    <div v-else class="bg-white border border-[#D7E0E1] rounded-lg overflow-hidden">
      <div class="overflow-x-auto">
        <table class="w-full text-sm">
          <thead>
            <tr class="bg-[#EEF2F3] text-left text-[11.5px] text-[#617377] uppercase tracking-wide">
              <th class="px-4 py-2.5 font-semibold">ID</th>
              <th class="px-4 py-2.5 font-semibold">Nama Perangkat</th>
              <th class="px-4 py-2.5 font-semibold">Model</th>
              <th class="px-4 py-2.5 font-semibold">Serial</th>
              <th class="px-4 py-2.5 font-semibold">Modbus</th>
              <th class="px-4 py-2.5 font-semibold">Status</th>
              <th class="px-4 py-2.5 font-semibold">Sensor</th>
              <th class="px-4 py-2.5 font-semibold">Resource</th>
              <th class="px-4 py-2.5 font-semibold">Aksi</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-[#EEF2F3]">
            <tr v-for="device in filteredDevices" :key="device.id" class="hover:bg-[#F7FAFA] transition-colors">
              <td class="px-4 py-2.5 text-ink font-mono">#{{ String(device.id).padStart(3, '0') }}</td>
              <td class="px-4 py-2.5 text-ink font-medium">{{ device.name }}</td>
              <td class="px-4 py-2.5 text-ink font-mono">{{ device.model || '—' }}</td>
              <td class="px-4 py-2.5 text-ink font-mono">{{ device.serial_no || '—' }}</td>
              <td class="px-4 py-2.5 text-ink font-mono">{{ device.modbus_addr }}</td>
              <td class="px-4 py-2.5">
                <span class="px-2 py-1 rounded-full text-[11.5px] font-semibold" :style="deviceStatusView(device).style">
                  {{ deviceStatusView(device).label }}
                </span>
                <div class="text-[11px] text-[#617377] mt-0.5">
                  {{ deviceStatusView(device).lastSeen ? getRelativeTime(deviceStatusView(device).lastSeen) : 'Belum ada data' }}
                </div>
                <div class="text-[10px] text-[#617377] italic mt-0.5">
                  {{ deviceStatusView(device).source === 'logger' ? 'dari logger' : 'dari data' }}
                </div>
              </td>
              <td class="px-4 py-2.5">
                <div v-if="deviceStatusView(device).source === 'logger'" class="flex items-center gap-1.5">
                  <span
                    v-for="s in sensorDots(deviceStatusView(device).sensors)"
                    :key="s.key"
                    class="w-2.5 h-2.5 rounded-full"
                    :class="s.class"
                    :title="s.title"
                  ></span>
                </div>
                <span v-else class="text-[#617377]">—</span>
              </td>
              <td class="px-4 py-2.5">
                <div v-if="deviceStatusView(device).source === 'logger'" class="flex flex-col gap-1 w-28">
                  <div v-if="deviceStatusView(device).cpu_temp != null" class="flex items-center gap-1.5">
                    <span class="text-[10px] text-[#617377] w-8 shrink-0">Suhu</span>
                    <div class="h-1.5 rounded bg-[#E5EDED] flex-1 overflow-hidden">
                      <div class="h-full bg-primary rounded" :style="{ width: pct(deviceStatusView(device).cpu_temp, 80) + '%' }"></div>
                    </div>
                    <span class="text-[10px] font-mono text-[#617377] w-9 text-right shrink-0">{{ Math.round(deviceStatusView(device).cpu_temp) }}°C</span>
                  </div>
                  <div v-if="deviceStatusView(device).cpu_pct != null" class="flex items-center gap-1.5">
                    <span class="text-[10px] text-[#617377] w-8 shrink-0">CPU</span>
                    <div class="h-1.5 rounded bg-[#E5EDED] flex-1 overflow-hidden">
                      <div class="h-full bg-primary rounded" :style="{ width: pct(deviceStatusView(device).cpu_pct, 100) + '%' }"></div>
                    </div>
                    <span class="text-[10px] font-mono text-[#617377] w-9 text-right shrink-0">{{ Math.round(deviceStatusView(device).cpu_pct) }}%</span>
                  </div>
                  <div v-if="deviceStatusView(device).mem_pct != null" class="flex items-center gap-1.5">
                    <span class="text-[10px] text-[#617377] w-8 shrink-0">RAM</span>
                    <div class="h-1.5 rounded bg-[#E5EDED] flex-1 overflow-hidden">
                      <div class="h-full bg-primary rounded" :style="{ width: pct(deviceStatusView(device).mem_pct, 100) + '%' }"></div>
                    </div>
                    <span class="text-[10px] font-mono text-[#617377] w-9 text-right shrink-0">{{ Math.round(deviceStatusView(device).mem_pct) }}%</span>
                  </div>
                  <div v-if="deviceStatusView(device).disk_pct != null" class="flex items-center gap-1.5">
                    <span class="text-[10px] text-[#617377] w-8 shrink-0">Disk</span>
                    <div class="h-1.5 rounded bg-[#E5EDED] flex-1 overflow-hidden">
                      <div class="h-full bg-primary rounded" :style="{ width: pct(deviceStatusView(device).disk_pct, 100) + '%' }"></div>
                    </div>
                    <span class="text-[10px] font-mono text-[#617377] w-9 text-right shrink-0">{{ Math.round(deviceStatusView(device).disk_pct) }}%</span>
                  </div>
                </div>
                <span v-else class="text-[#617377]">—</span>
              </td>
              <td class="px-4 py-2.5">
                <div class="flex items-center gap-3">
                  <button @click="openMaintenanceModal(device)" class="text-primary hover:underline text-sm" title="Log Perawatan">
                    <i class="fas fa-clipboard-list"></i>
                  </button>
                  <button v-if="canManageDevices" @click="editDevice(device)" class="text-warning hover:underline text-sm" title="Edit">
                    <i class="fas fa-edit"></i>
                  </button>
                  <button v-if="canManageDevices" @click="deleteDeviceHandler(device)" class="text-danger hover:underline text-sm" title="Hapus">
                    <i class="fas fa-trash"></i>
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <div class="px-4 py-3 border-t border-[#D7E0E1]">
        <span class="text-xs text-[#617377] font-mono">{{ filteredDevices.length }} perangkat</span>
      </div>
    </div>

    <!-- Add/Edit Device Modal -->
    <div
      v-if="showAddDeviceModal || editingDevice"
      class="fixed inset-0 bg-ink/40 backdrop-blur-sm flex items-center justify-center z-50 p-4"
      @click.self="closeModal"
    >
      <div class="bg-white rounded-lg border border-[#D7E0E1] max-w-lg w-full shadow-2xl max-h-[90vh] overflow-y-auto">
        <div class="flex justify-between items-center px-6 py-4 border-b border-[#EEF2F3]">
          <div class="flex items-center gap-3">
            <div class="w-8 h-8 rounded-lg bg-[#E4F1F2] flex items-center justify-center">
              <i class="fas fa-microchip text-[#0A5A62] text-xs"></i>
            </div>
            <h3 class="font-bold text-ink">{{ editingDevice ? 'Edit Perangkat' : 'Tambah Perangkat' }}</h3>
          </div>
          <button @click="closeModal" class="w-8 h-8 rounded-lg hover:bg-[#EEF2F3] flex items-center justify-center transition-colors">
            <i class="fas fa-times text-[#617377] text-sm"></i>
          </button>
        </div>

        <form @submit.prevent="saveDevice" class="p-6 space-y-4">
          <div>
            <label class="block text-xs font-semibold text-[#617377] uppercase tracking-wide mb-1.5">
              Nama Perangkat <span class="text-danger normal-case font-normal">*</span>
            </label>
            <input v-model="deviceForm.name" type="text" required placeholder="e.g., pH Sensor"
              class="w-full border border-[#C4D1D3] rounded-md p-2 text-sm" />
          </div>

          <div class="grid grid-cols-2 gap-4">
            <div>
              <label class="block text-xs font-semibold text-[#617377] uppercase tracking-wide mb-1.5">Model</label>
              <input v-model="deviceForm.model" type="text" placeholder="e.g., PHM-100"
                class="w-full border border-[#C4D1D3] rounded-md p-2 text-sm font-mono" />
            </div>
            <div>
              <label class="block text-xs font-semibold text-[#617377] uppercase tracking-wide mb-1.5">Serial Number</label>
              <input v-model="deviceForm.serial_no" type="text" placeholder="e.g., SN123456"
                class="w-full border border-[#C4D1D3] rounded-md p-2 text-sm font-mono" />
            </div>
          </div>

          <div>
            <label class="block text-xs font-semibold text-[#617377] uppercase tracking-wide mb-1.5">
              Modbus Address <span class="text-danger normal-case font-normal">*</span>
            </label>
            <input v-model.number="deviceForm.modbus_addr" type="number" required min="1" max="247"
              placeholder="1–247" class="w-full border border-[#C4D1D3] rounded-md p-2 text-sm font-mono" />
          </div>

          <div class="flex items-center gap-3">
            <input v-model="deviceForm.is_active" type="checkbox" id="dev_is_active"
              class="w-4 h-4 text-primary border-[#C4D1D3] rounded focus:ring-primary" />
            <label for="dev_is_active" class="text-sm text-ink">Perangkat Aktif</label>
          </div>

          <div v-if="formError" class="p-3 bg-[#F7E4E4] border border-[#EEC5C5] rounded-lg text-xs text-danger flex items-center gap-2">
            <i class="fas fa-exclamation-circle shrink-0"></i>{{ formError }}
          </div>

          <div class="flex gap-3 justify-end pt-4 border-t border-[#EEF2F3]">
            <button type="button" @click="closeModal" class="px-3 py-2 rounded-md border border-[#C4D1D3] text-sm text-ink hover:bg-[#EEF2F3]">Batal</button>
            <button type="submit" :disabled="formLoading"
              class="px-3 py-2 rounded-md text-sm text-white bg-primary hover:bg-primary-dark disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2">
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
      class="fixed inset-0 bg-ink/40 backdrop-blur-sm flex items-center justify-center z-50 p-4"
      @click.self="closeMaintenanceModal"
    >
      <div class="bg-white rounded-lg border border-[#D7E0E1] max-w-2xl w-full shadow-2xl max-h-[90vh] overflow-y-auto">
        <!-- Modal header -->
        <div class="flex justify-between items-center px-6 py-4 border-b border-[#EEF2F3]">
          <div class="flex items-center gap-3">
            <div class="w-8 h-8 rounded-lg bg-[#E4F1F2] flex items-center justify-center">
              <i class="fas fa-microchip text-[#0A5A62] text-xs"></i>
            </div>
            <div>
              <h3 class="font-bold text-ink">{{ maintenanceDevice.name }}</h3>
              <p class="text-xs text-[#617377] font-mono">{{ maintenanceDevice.model || '—' }} · SN {{ maintenanceDevice.serial_no || '—' }}</p>
            </div>
          </div>
          <button @click="closeMaintenanceModal" class="w-8 h-8 rounded-lg hover:bg-[#EEF2F3] flex items-center justify-center transition-colors">
            <i class="fas fa-times text-[#617377] text-sm"></i>
          </button>
        </div>

        <!-- Tabs -->
        <div class="flex border-b border-[#EEF2F3] px-6">
          <button
            @click="maintenanceModalTab = 'info'"
            class="px-4 py-2.5 text-sm font-semibold border-b-2 transition-colors"
            :class="maintenanceModalTab === 'info' ? 'border-primary text-primary' : 'border-transparent text-[#617377] hover:text-ink'"
          >
            Info
          </button>
          <button
            @click="maintenanceModalTab = 'log'"
            class="px-4 py-2.5 text-sm font-semibold border-b-2 transition-colors"
            :class="maintenanceModalTab === 'log' ? 'border-primary text-primary' : 'border-transparent text-[#617377] hover:text-ink'"
          >
            Log Perawatan
            <span v-if="maintenanceLogs.length" class="ml-1 text-xs font-mono text-[#617377]">({{ maintenanceLogs.length }})</span>
          </button>
        </div>

        <!-- Info Tab -->
        <div v-if="maintenanceModalTab === 'info'" class="p-6 space-y-4">
          <div class="grid grid-cols-3 gap-3">
            <div class="p-3 rounded-lg bg-[#F7FAFA] border border-[#EEF2F3] text-center">
              <div class="text-[10px] text-[#617377] uppercase tracking-wide mb-1">Status</div>
              <div class="flex items-center justify-center gap-1.5">
                <span class="px-2 py-0.5 rounded-full text-[11px] font-semibold" :style="deviceStatusView(maintenanceDevice).style">
                  {{ deviceStatusView(maintenanceDevice).label }}
                </span>
              </div>
              <div class="text-[10px] text-[#617377] italic mt-1">
                {{ deviceStatusView(maintenanceDevice).source === 'logger' ? 'dari logger' : 'dari data' }}
              </div>
            </div>
            <div class="p-3 rounded-lg bg-[#F7FAFA] border border-[#EEF2F3] text-center">
              <div class="text-[10px] text-[#617377] uppercase tracking-wide mb-1">Data 24j</div>
              <div class="text-lg font-bold font-mono text-ink">{{ deviceHealth[maintenanceDevice.id]?.data_count_24h ?? '—' }}</div>
            </div>
            <div class="p-3 rounded-lg bg-[#F7FAFA] border border-[#EEF2F3] text-center">
              <div class="text-[10px] text-[#617377] uppercase tracking-wide mb-1">Data 7 Hari</div>
              <div class="text-lg font-bold font-mono text-ink">{{ deviceHealth[maintenanceDevice.id]?.data_count_7d ?? '—' }}</div>
            </div>
          </div>

          <div class="space-y-2 text-sm">
            <div class="flex justify-between py-2 border-b border-[#EEF2F3]">
              <span class="text-[#617377]">Nama</span>
              <span class="font-semibold text-ink">{{ maintenanceDevice.name }}</span>
            </div>
            <div class="flex justify-between py-2 border-b border-[#EEF2F3]">
              <span class="text-[#617377]">Model</span>
              <span class="font-mono text-ink">{{ maintenanceDevice.model || '—' }}</span>
            </div>
            <div class="flex justify-between py-2 border-b border-[#EEF2F3]">
              <span class="text-[#617377]">Serial Number</span>
              <span class="font-mono text-ink">{{ maintenanceDevice.serial_no || '—' }}</span>
            </div>
            <div class="flex justify-between py-2 border-b border-[#EEF2F3]">
              <span class="text-[#617377]">Modbus Address</span>
              <span class="font-mono text-ink">{{ maintenanceDevice.modbus_addr }}</span>
            </div>
            <div class="flex justify-between py-2">
              <span class="text-[#617377]">Aktif</span>
              <span :class="maintenanceDevice.is_active ? 'text-success font-bold' : 'text-[#617377]'">
                {{ maintenanceDevice.is_active ? 'Aktif' : 'Nonaktif' }}
              </span>
            </div>
            <div v-if="deviceHealth[maintenanceDevice.id]?.last_calibration_at" class="flex justify-between py-2 border-t border-[#EEF2F3]">
              <span class="text-[#617377]">Kalibrasi Terakhir</span>
              <span class="text-ink">{{ formatDate(deviceHealth[maintenanceDevice.id].last_calibration_at, false, siteTz) }}</span>
            </div>
            <div v-if="deviceHealth[maintenanceDevice.id]?.next_calibration_at" class="flex justify-between py-2 items-center">
              <span class="text-[#617377]">Kalibrasi Berikutnya</span>
              <span class="flex items-center gap-2">
                <span
                  v-if="deviceHealth[maintenanceDevice.id]?.calibration_overdue"
                  class="text-[10px] font-bold px-1.5 py-0.5 rounded uppercase tracking-wide bg-[#FBEAEA] text-danger border border-[#F0C6C6]"
                >Terlambat</span>
                <span
                  :class="parseUTC(deviceHealth[maintenanceDevice.id].next_calibration_at) < new Date() ? 'text-danger' : parseUTC(deviceHealth[maintenanceDevice.id].next_calibration_at) < new Date(Date.now() + 30*24*60*60*1000) ? 'text-warning' : 'text-ink'"
                >
                  {{ formatDate(deviceHealth[maintenanceDevice.id].next_calibration_at, false, siteTz) }}
                </span>
              </span>
            </div>
          </div>
        </div>

        <!-- Log Perawatan Tab -->
        <div v-if="maintenanceModalTab === 'log'" class="p-6">
          <div v-if="loadingLogs" class="text-center text-sm text-[#617377] py-4">
            <i class="fas fa-spinner fa-spin mr-2"></i>Memuat...
          </div>
          <div v-else>
            <div v-if="!maintenanceLogs.length && !showAddLogForm" class="text-center text-sm text-[#617377] py-4">
              Belum ada log perawatan.
            </div>
            <div v-else class="space-y-3 mb-4">
              <div
                v-for="log in maintenanceLogs"
                :key="log.id"
                class="flex gap-3 p-3 rounded-lg border border-[#EEF2F3] bg-[#F7FAFA]"
              >
                <div class="shrink-0 mt-0.5">
                  <span class="text-[10px] font-bold px-2 py-0.5 rounded uppercase tracking-wide bg-[#E6F2EC] text-success border border-[#C7E4D4]" v-if="log.type === 'calibration'">Kalibrasi</span>
                  <span class="text-[10px] font-bold px-2 py-0.5 rounded uppercase tracking-wide bg-[#F7E4E4] text-danger border border-[#EEC5C5]" v-else-if="log.type === 'repair'">Perbaikan</span>
                  <span class="text-[10px] font-bold px-2 py-0.5 rounded uppercase tracking-wide bg-[#E4F1F2] text-[#0A5A62] border border-[#D7E0E1]" v-else-if="log.type === 'inspection'">Inspeksi</span>
                  <span class="text-[10px] font-bold px-2 py-0.5 rounded uppercase tracking-wide bg-[#EAEEEF] text-[#6E7E82] border border-[#D7E0E1]" v-else>{{ getLogTypeLabel(log.type) }}</span>
                </div>
                <div class="flex-1 min-w-0">
                  <div class="text-xs text-[#617377] font-mono">{{ formatDate(log.performed_at, false, siteTz) }}</div>
                  <div v-if="log.notes" class="text-sm text-ink mt-0.5">{{ log.notes }}</div>
                  <div v-if="log.before_value != null || log.after_value != null" class="text-xs text-[#617377] mt-1 font-mono">
                    <i class="fas fa-sliders mr-1"></i>
                    <span v-if="log.field" class="uppercase mr-1">{{ log.field }}</span>
                    {{ log.before_value ?? '—' }} → {{ log.after_value ?? '—' }}
                    <span v-if="log.offset != null" :class="log.offset < 0 ? 'text-danger' : 'text-success'">({{ log.offset > 0 ? '+' : '' }}{{ formatNumber(log.offset, 3) }})</span>
                  </div>
                  <div v-if="log.next_due_at" class="text-xs text-warning mt-1">
                    <i class="fas fa-calendar-alt mr-1"></i>
                    Berikutnya: {{ formatDate(log.next_due_at, false, siteTz) }}
                  </div>
                  <div v-if="log.performed_by_name" class="text-xs text-[#617377] mt-1">
                    <i class="fas fa-user mr-1"></i>{{ log.performed_by_name }}
                  </div>
                </div>
                <button
                  v-if="canManageDevices"
                  @click="removeLog(log.id)"
                  class="shrink-0 text-[#C4D1D3] hover:text-danger transition-colors"
                >
                  <i class="fas fa-times text-xs"></i>
                </button>
              </div>
            </div>

            <div v-if="showAddLogForm && canManageDevices" class="p-4 rounded-lg border border-primary/20 bg-primary/5 space-y-3 mb-3">
              <div class="grid grid-cols-2 gap-3">
                <div>
                  <label class="block text-xs font-semibold text-[#617377] uppercase tracking-wide mb-1.5">Tipe</label>
                  <select v-model="newLog.type" class="w-full border border-[#C4D1D3] rounded-md p-2 text-sm">
                    <option v-for="t in LOG_TYPES" :key="t.key" :value="t.key">{{ t.label }}</option>
                  </select>
                </div>
                <div>
                  <label class="block text-xs font-semibold text-[#617377] uppercase tracking-wide mb-1.5">Tanggal Pelaksanaan</label>
                  <input v-model="newLog.performed_at" type="datetime-local" class="w-full border border-[#C4D1D3] rounded-md p-2 text-sm" />
                </div>
              </div>
              <div>
                <label class="block text-xs font-semibold text-[#617377] uppercase tracking-wide mb-1.5">Catatan</label>
                <textarea v-model="newLog.notes" rows="2" class="w-full border border-[#C4D1D3] rounded-md p-2 text-sm resize-none" placeholder="Opsional..."></textarea>
              </div>
              <template v-if="newLog.type === 'calibration'">
                <div class="grid grid-cols-3 gap-3">
                  <div>
                    <label class="block text-xs font-semibold text-[#617377] uppercase tracking-wide mb-1.5">Parameter</label>
                    <select v-model="newLog.field" class="w-full border border-[#C4D1D3] rounded-md p-2 text-sm">
                      <option value="">—</option>
                      <option value="ph">pH</option>
                      <option value="tss">TSS</option>
                      <option value="cod">COD</option>
                      <option value="nh3n">NH3-N</option>
                      <option value="debit">Debit</option>
                    </select>
                  </div>
                  <div>
                    <label class="block text-xs font-semibold text-[#617377] uppercase tracking-wide mb-1.5">Nilai Awal</label>
                    <input v-model="newLog.before_value" type="number" step="any" class="w-full border border-[#C4D1D3] rounded-md p-2 text-sm" placeholder="sebelum" />
                  </div>
                  <div>
                    <label class="block text-xs font-semibold text-[#617377] uppercase tracking-wide mb-1.5">Nilai Akhir</label>
                    <input v-model="newLog.after_value" type="number" step="any" class="w-full border border-[#C4D1D3] rounded-md p-2 text-sm" placeholder="sesudah" />
                  </div>
                </div>
                <div>
                  <label class="block text-xs font-semibold text-[#617377] uppercase tracking-wide mb-1.5">Jadwal Kalibrasi Berikutnya</label>
                  <input v-model="newLog.next_due_at" type="date" class="w-full border border-[#C4D1D3] rounded-md p-2 text-sm" />
                </div>
              </template>
              <div class="flex gap-2">
                <button @click="submitLog" :disabled="addingLog" class="px-3 py-2 rounded-md text-sm text-white bg-primary hover:bg-primary-dark disabled:opacity-50">
                  <i :class="addingLog ? 'fas fa-spinner fa-spin' : 'fas fa-save'" class="mr-1.5 text-xs"></i>Simpan
                </button>
                <button @click="showAddLogForm = false" class="px-3 py-2 rounded-md border border-[#C4D1D3] text-sm text-ink hover:bg-[#EEF2F3]">Batal</button>
              </div>
            </div>

            <button
              v-if="!showAddLogForm && canManageDevices"
              @click="showAddLogForm = true"
              class="px-3 py-2 rounded-md border border-[#C4D1D3] text-sm text-ink hover:bg-[#EEF2F3] flex items-center gap-1.5"
            >
              <i class="fas fa-plus text-xs"></i>Tambah Catatan
            </button>
          </div>
        </div>
      </div>
    </div>
  </AppLayout>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import AppLayout from '@/Layouts/AppLayout.vue';
import PageHeader from '@/Components/PageHeader.vue';
import { useApi } from '@/Composables/useApi';
import { useAuth } from '@/Composables/useAuth';
import { useToast } from '@/Composables/useToast';
import { useConfirm } from '@/Composables/useConfirm';
import { getRelativeTime, formatDate, parseUTC, formatNumber } from '@/Utils/helpers';
import logger from '@/Utils/logger';

// Composables
const {
  getSites, getDevices, createDevice, updateDevice, deleteDevice,
  getDeviceHealth, getMaintenanceLogs, addMaintenanceLog, deleteMaintenanceLog,
  getLoggerStatus,
} = useApi();
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

// Device health data keyed by device id
const deviceHealth = ref({});

// Logger status, keyed by site_id (from /logger/status, all sites)
const loggerStatuses = ref([]);
const loggerBySiteId = computed(() => {
  const map = {};
  for (const row of loggerStatuses.value) {
    map[row.site_id] = row;
  }
  return map;
});

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
  field: '',
  before_value: '',
  after_value: '',
});
const showAddLogForm = ref(false);

const LOG_TYPES = [
  { key: 'calibration', label: 'Kalibrasi', color: 'emerald' },
  { key: 'repair',      label: 'Perbaikan', color: 'red' },
  { key: 'inspection',  label: 'Inspeksi',  color: 'blue' },
  { key: 'note',        label: 'Catatan',   color: 'slate' },
];

const getLogTypeLabel = (type) => LOG_TYPES.find(t => t.key === type)?.label || type;

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

const siteTz = computed(() => {
  const site = sites.value.find(s => s.uid === selectedSiteUid.value);
  return site?.timezone || 'Asia/Jakarta';
});

// Device statistics
const activeDevicesCount = computed(() => devices.value.filter(d => d.is_active).length);
const inactiveDevicesCount = computed(() => devices.value.filter(d => !d.is_active).length);

// Filtered devices based on show inactive toggle
const filteredDevices = computed(() => {
  if (showInactiveDevices.value) return devices.value;
  return devices.value.filter(d => d.is_active !== false);
});

// ---- status styling tokens ----
const OK_STYLE = { background: '#E6F2EC', color: '#1F7A4D' };
const WARNING_STYLE = { background: '#F7EFD9', color: '#9A6B00' };
const DANGER_STYLE = { background: '#F7E4E4', color: '#B03030' };
const NEUTRAL_STYLE = { background: '#EAEEEF', color: '#6E7E82' };

const DATA_STATUS_MAP = {
  online: { label: 'Online', style: OK_STYLE },
  warning: { label: 'Waspada', style: WARNING_STYLE },
  offline: { label: 'Offline', style: DANGER_STYLE },
  unknown: { label: 'Belum ada data', style: NEUTRAL_STYLE },
};

// Normalized status view for a device: prefer logger heartbeat, fall back to
// the device's own data-derived status when the site has no logger heartbeat.
function deviceStatusView(device) {
  const logRow = loggerBySiteId.value[device.site_id];
  if (logRow) {
    const isAlive = logRow.state === 'alive';
    return {
      source: 'logger',
      state: logRow.state,
      label: isAlive ? 'Hidup' : 'Mati',
      style: isAlive ? OK_STYLE : DANGER_STYLE,
      lastSeen: logRow.last_heartbeat_at,
      sensors: {
        ph_ok: logRow.ph_ok,
        tss_ok: logRow.tss_ok,
        debit_ok: logRow.debit_ok,
        cod_ok: logRow.cod_ok,
        nh3n_ok: logRow.nh3n_ok,
      },
      cpu_temp: logRow.cpu_temp,
      cpu_pct: logRow.cpu_pct,
      mem_pct: logRow.mem_pct,
      disk_pct: logRow.disk_pct,
      op_status: logRow.op_status,
      internet_ok: logRow.internet_ok,
      buffer_depth: logRow.buffer_depth,
    };
  }

  const s = device.status || 'unknown';
  const m = DATA_STATUS_MAP[s] || DATA_STATUS_MAP.unknown;
  return {
    source: 'data',
    state: s,
    label: m.label,
    style: m.style,
    lastSeen: device.last_seen,
  };
}

const SENSOR_FIELDS = [
  { key: 'ph_ok', label: 'pH' },
  { key: 'tss_ok', label: 'TSS' },
  { key: 'debit_ok', label: 'Debit' },
  { key: 'cod_ok', label: 'COD' },
  { key: 'nh3n_ok', label: 'NH₃-N' },
];

function sensorDots(sensors) {
  return SENSOR_FIELDS.map(f => {
    const val = sensors?.[f.key];
    let cls = 'bg-[#C4D1D3]';
    let state = '—';
    if (val === true) { cls = 'bg-success'; state = 'OK'; }
    else if (val === false) { cls = 'bg-danger'; state = 'Gagal'; }
    return { key: f.key, class: cls, title: `${f.label}: ${state}` };
  });
}

function pct(value, max) {
  if (value == null) return 0;
  return Math.min(100, Math.max(0, (value / max) * 100));
}

// Load sites
const loadSites = async () => {
  try {
    const response = await getSites({ per_page: 100 });
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

    sites.value = filterSitesByUser(sitesList);

    if (sites.value.length > 0) {
      selectedSiteUid.value = sites.value[0].uid;
      await loadDevices();
    }
  } catch (error) {
    logger.error('Failed to load sites:', error);
    sites.value = [];
  }
};

// Load logger status for all sites (used to source live status per site)
const loadLoggerStatuses = async () => {
  try {
    const res = await getLoggerStatus();
    loggerStatuses.value = Array.isArray(res) ? res : (res?.items || []);
  } catch (error) {
    logger.error('Failed to load logger status:', error);
    loggerStatuses.value = [];
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

    await loadLoggerStatuses();
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
    const isCal = newLog.value.type === 'calibration';
    await addMaintenanceLog(maintenanceDevice.value.id, {
      type: newLog.value.type,
      notes: newLog.value.notes || null,
      performed_at: new Date(newLog.value.performed_at).toISOString(),
      next_due_at: newLog.value.next_due_at ? new Date(newLog.value.next_due_at).toISOString() : null,
      field: isCal && newLog.value.field ? newLog.value.field : null,
      before_value: isCal && newLog.value.before_value !== '' ? Number(newLog.value.before_value) : null,
      after_value: isCal && newLog.value.after_value !== '' ? Number(newLog.value.after_value) : null,
    });
    await loadMaintenanceLogs(maintenanceDevice.value.id);
    showAddLogForm.value = false;
    newLog.value = { type: 'calibration', notes: '', performed_at: new Date().toISOString().slice(0, 16), next_due_at: '', field: '', before_value: '', after_value: '' };
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

// Edit device
const editDevice = (device) => {
  editingDevice.value = device;
  deviceForm.value = { ...device };
  formError.value = null;
};

// Toggle device status (kept for parity with previous behavior)
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
      await updateDevice(editingDevice.value.id, payload);
      await loadDevices();
      closeModal();
    } else {
      await createDevice(payload);
      await loadDevices();
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
  await Promise.allSettled([loadSites(), loadLoggerStatuses()]);
});
</script>
