<template>
  <AppLayout>
    <div class="space-y-6">
      <!-- Header -->
      <div class="flex justify-between items-center">
        <div>
          <h2 class="text-xl font-bold text-slate-800">Manajemen Lokasi</h2>
          <p class="text-slate-500 text-sm mt-0.5">Kelola lokasi monitoring air limbah</p>
        </div>
        <button
          v-if="isOperator"
          @click="showAddModal = true"
          class="btn-primary flex items-center gap-2 text-sm"
        >
          <i class="fas fa-plus text-xs"></i>Tambah Lokasi
        </button>
      </div>

      <!-- Sites Map -->
      <div class="card p-4">
        <div class="flex items-center gap-3 mb-3">
          <h3 class="card-title flex-1">Peta Lokasi Monitoring</h3>
          <span class="text-xs font-mono text-slate-400">{{ sites.length }} lokasi</span>
        </div>
        <SiteMap
          :sites="sites"
          height="360px"
          :zoom="10"
          @site-click="viewSite"
        />
      </div>

      <!-- Sites Grid -->
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        <div
          v-for="site in sites"
          :key="site.uid"
          class="card p-5 flex flex-col gap-0"
          style="border-left: 4px solid #1e3a8a;"
        >
          <!-- Site header -->
          <div class="flex justify-between items-start mb-3">
            <div class="flex-1 min-w-0 mr-3">
              <h3 class="font-bold text-slate-800 leading-tight truncate">{{ site.name }}</h3>
              <p class="text-xs text-slate-500 mt-0.5 truncate">{{ site.company_name }}</p>
            </div>
            <span
              :class="[
                'shrink-0 text-[10px] font-bold px-2 py-0.5 rounded leading-none',
                site.is_active ? 'bg-emerald-50 text-emerald-700' : 'bg-slate-100 text-slate-500'
              ]"
            >
              {{ site.is_active ? 'AKTIF' : 'NONAKTIF' }}
            </span>
          </div>

          <!-- Site meta -->
          <div class="space-y-1.5 mb-4 flex-1">
            <div class="flex items-center gap-2 text-xs text-slate-500">
              <i class="fas fa-map-marker-alt w-3.5 text-center text-primary/60"></i>
              <span class="font-mono">{{ site.lat }}, {{ site.lon }}</span>
            </div>
            <div class="flex items-center gap-2 text-xs text-slate-500">
              <i class="fas fa-fingerprint w-3.5 text-center text-primary/60"></i>
              <span class="font-mono truncate">{{ site.uid }}</span>
            </div>
          </div>

          <!-- Actions -->
          <div class="flex gap-2 pt-3 border-t border-slate-100">
            <button @click="viewSite(site)" class="btn-primary flex-1 text-xs py-2">
              <i class="fas fa-chart-line mr-1.5"></i>Dashboard
            </button>
            <button
              v-if="isOperator"
              @click="editSite(site)"
              class="px-3 py-2 rounded-lg text-xs font-semibold border border-amber-200 text-amber-700 hover:bg-amber-50 transition-colors"
              title="Edit"
            >
              <i class="fas fa-edit"></i>
            </button>
            <button
              v-if="isAdmin"
              @click="deleteSiteHandler(site)"
              class="px-3 py-2 rounded-lg text-xs font-semibold border border-red-200 text-red-600 hover:bg-red-50 transition-colors"
              title="Hapus"
            >
              <i class="fas fa-trash"></i>
            </button>
          </div>
        </div>
      </div>

      <!-- Add/Edit Modal -->
      <div
        v-if="showAddModal || editingSite"
        class="fixed inset-0 bg-slate-900/60 backdrop-blur-sm flex items-center justify-center z-50 p-4"
        @click.self="closeModal"
      >
        <div class="bg-white rounded-2xl max-w-2xl w-full shadow-2xl max-h-[90vh] overflow-y-auto">
          <!-- Modal header -->
          <div class="flex justify-between items-center px-6 py-4 border-b border-slate-100">
            <div class="flex items-center gap-3">
              <div class="w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center">
                <i class="fas fa-map-marker-alt text-primary text-xs"></i>
              </div>
              <h3 class="font-bold text-slate-800">{{ editingSite ? 'Edit Lokasi' : 'Tambah Lokasi' }}</h3>
            </div>
            <button @click="closeModal" class="w-8 h-8 rounded-lg hover:bg-slate-100 flex items-center justify-center transition-colors">
              <i class="fas fa-times text-slate-400 text-sm"></i>
            </button>
          </div>

          <!-- Tabs (only when editing) -->
          <div v-if="editingSite" class="flex border-b border-slate-100 px-6">
            <button
              @click="modalTab = 'info'"
              class="px-4 py-2.5 text-sm font-semibold border-b-2 transition-colors"
              :class="modalTab === 'info' ? 'border-primary text-primary' : 'border-transparent text-slate-500 hover:text-slate-700'"
            >
              Info
            </button>
            <button
              v-if="isOperator"
              @click="modalTab = 'baku-mutu'"
              class="px-4 py-2.5 text-sm font-semibold border-b-2 transition-colors"
              :class="modalTab === 'baku-mutu' ? 'border-primary text-primary' : 'border-transparent text-slate-500 hover:text-slate-700'"
            >
              Baku Mutu
            </button>
            <button
              v-if="isAdmin"
              @click="modalTab = 'device-key'"
              class="px-4 py-2.5 text-sm font-semibold border-b-2 transition-colors"
              :class="modalTab === 'device-key' ? 'border-primary text-primary' : 'border-transparent text-slate-500 hover:text-slate-700'"
            >
              Device Key
            </button>
          </div>

          <form v-if="!editingSite || modalTab === 'info'" @submit.prevent="saveSite" class="p-6 space-y-4">
            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label class="block text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1.5">UID Lokasi</label>
                <input v-model="siteForm.uid" type="text" required :disabled="!!editingSite"
                  placeholder="aqmsFOEmmEPISI01"
                  class="form-input text-sm font-mono" :class="editingSite ? 'bg-slate-50 text-slate-400' : ''" />
              </div>
              <div>
                <label class="block text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1.5">Nama Lokasi</label>
                <input v-model="siteForm.name" type="text" required class="form-input text-sm" />
              </div>
            </div>

            <div>
              <label class="block text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1.5">Nama Perusahaan</label>
              <input v-model="siteForm.company_name" type="text" required class="form-input text-sm" />
            </div>

            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label class="block text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1.5">Latitude</label>
                <input v-model.number="siteForm.lat" type="number" step="any" required class="form-input text-sm font-mono" />
              </div>
              <div>
                <label class="block text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1.5">Longitude</label>
                <input v-model.number="siteForm.lon" type="number" step="any" required class="form-input text-sm font-mono" />
              </div>
            </div>

            <!-- Timezone -->
            <div>
              <label class="block text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1.5">Zona Waktu</label>
              <select v-model="siteForm.timezone" class="form-input text-sm">
                <option value="Asia/Jakarta">WIB – Waktu Indonesia Barat (UTC+7)</option>
                <option value="Asia/Makassar">WITA – Waktu Indonesia Tengah (UTC+8)</option>
                <option value="Asia/Jayapura">WIT – Waktu Indonesia Timur (UTC+9)</option>
              </select>
            </div>

            <div class="flex items-center gap-3">
              <input v-model="siteForm.is_active" type="checkbox" id="is_active"
                class="w-4 h-4 text-primary border-slate-300 rounded focus:ring-primary" />
              <label for="is_active" class="text-sm text-slate-700">Lokasi Aktif</label>
            </div>

            <div class="flex gap-3 justify-end pt-4 border-t border-slate-100">
              <button type="button" @click="closeModal" class="btn-secondary text-sm">Batal</button>
              <button type="submit" class="btn-primary text-sm">
                <i class="fas fa-save mr-1.5 text-xs"></i>{{ editingSite ? 'Simpan Perubahan' : 'Tambah Lokasi' }}
              </button>
            </div>
          </form>

          <!-- Baku Mutu Tab -->
          <div v-if="editingSite && modalTab === 'baku-mutu'" class="p-6">
            <div v-if="loadingRules" class="text-sm text-slate-400 text-center py-4">
              <i class="fas fa-spinner fa-spin mr-2"></i>Memuat aturan...
            </div>
            <div v-else>
              <div class="space-y-3 mb-4">
                <div v-if="!alertRules.length" class="text-sm text-slate-400 text-center py-4">
                  Belum ada aturan baku mutu. Klik "Tambah Aturan" untuk memulai.
                </div>
                <div
                  v-for="rule in alertRules"
                  :key="rule.id"
                  class="grid grid-cols-5 gap-2 items-center p-3 rounded-lg border border-slate-100 bg-slate-50 text-sm"
                >
                  <div class="font-semibold text-slate-700">{{ rule.field.toUpperCase() }}</div>
                  <input v-model.number="rule.warning_min" type="number" step="any" placeholder="Min peringatan"
                    class="form-input text-xs py-1.5" />
                  <input v-model.number="rule.warning_max" type="number" step="any" placeholder="Maks peringatan"
                    class="form-input text-xs py-1.5" />
                  <input v-model.number="rule.danger_max" type="number" step="any" placeholder="Maks bahaya"
                    class="form-input text-xs py-1.5" />
                  <button @click="saveRule(rule)" class="btn-primary text-xs py-1.5">Simpan</button>
                </div>
              </div>

              <div v-if="showAddRule" class="p-3 rounded-lg border border-primary/20 bg-primary/5 mb-3">
                <div class="grid grid-cols-5 gap-2 items-center">
                  <select v-model="newRule.field" class="form-input text-xs py-1.5">
                    <option value="">Pilih Parameter</option>
                    <option v-for="f in AVAILABLE_FIELDS" :key="f.key" :value="f.key">{{ f.label }}</option>
                  </select>
                  <input v-model.number="newRule.warning_min" type="number" step="any" placeholder="Min peringatan" class="form-input text-xs py-1.5" />
                  <input v-model.number="newRule.warning_max" type="number" step="any" placeholder="Maks peringatan" class="form-input text-xs py-1.5" />
                  <input v-model.number="newRule.danger_max" type="number" step="any" placeholder="Maks bahaya" class="form-input text-xs py-1.5" />
                  <button @click="addRule" class="btn-primary text-xs py-1.5">Tambah</button>
                </div>
              </div>

              <button
                v-if="!showAddRule"
                @click="showAddRule = true"
                class="btn-secondary text-xs flex items-center gap-1.5"
              >
                <i class="fas fa-plus text-xs"></i>Tambah Aturan
              </button>
            </div>
          </div>

          <!-- Device Key Tab -->
          <div v-if="editingSite && modalTab === 'device-key'" class="p-6">
            <div v-if="loadingKey" class="text-sm text-slate-400 text-center py-6">
              <i class="fas fa-spinner fa-spin mr-2"></i>Memuat...
            </div>
            <div v-else-if="!deviceKey" class="text-sm text-slate-400 text-center py-6">
              Gagal memuat device key.
            </div>
            <div v-else class="space-y-5">
              <!-- Secret display -->
              <div>
                <label class="block text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2">
                  Secret Perangkat
                </label>
                <div class="flex items-center gap-2">
                  <div class="flex-1 font-mono text-sm bg-slate-50 border border-slate-200 rounded-lg px-3 py-2.5 text-slate-800 truncate">
                    {{ showSecret ? deviceKey.device_secret : maskedSecret }}
                  </div>
                  <button
                    @click="showSecret = !showSecret"
                    class="px-3 py-2.5 rounded-lg border border-slate-200 text-xs font-semibold text-slate-600 hover:bg-slate-50 transition-colors shrink-0"
                  >
                    {{ showSecret ? 'Sembunyikan' : 'Tampilkan' }}
                  </button>
                  <button
                    @click="copySecret"
                    class="px-3 py-2.5 rounded-lg border border-slate-200 text-xs font-semibold text-slate-600 hover:bg-slate-50 transition-colors shrink-0"
                  >
                    <i class="fas fa-copy mr-1"></i>Copy
                  </button>
                </div>
              </div>

              <!-- Last ingest -->
              <div class="flex items-center gap-3 p-3 rounded-lg bg-slate-50 border border-slate-100">
                <div class="w-8 h-8 rounded-lg bg-emerald-50 flex items-center justify-center shrink-0">
                  <i class="fas fa-satellite-dish text-emerald-600 text-xs"></i>
                </div>
                <div>
                  <div class="text-xs text-slate-500">Terakhir menerima data</div>
                  <div class="text-sm font-semibold text-slate-800 font-mono">
                    {{ deviceKey.last_ingest_at ? getRelativeTime(deviceKey.last_ingest_at) : 'Belum pernah' }}
                  </div>
                </div>
              </div>

              <!-- Regenerate -->
              <div class="pt-3 border-t border-slate-100">
                <p class="text-xs text-slate-400 mb-3">
                  Regenerate akan membuat secret baru. Perangkat lama tidak bisa kirim data sampai secret-nya diperbarui.
                </p>
                <button
                  @click="handleRotateSecret"
                  :disabled="rotatingSecret"
                  class="px-4 py-2 rounded-lg text-sm font-semibold border border-red-200 text-red-600 hover:bg-red-50 transition-colors disabled:opacity-50"
                >
                  <i class="fas fa-sync-alt mr-1.5" :class="rotatingSecret ? 'fa-spin' : ''"></i>
                  Regenerate Secret
                </button>
              </div>

              <!-- Endpoint hint -->
              <div class="p-3 rounded-lg bg-slate-900 text-xs font-mono text-emerald-400">
                GET /api/get-key?uid={{ deviceKey.uid }}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </AppLayout>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import AppLayout from '@/Layouts/AppLayout.vue';
import StatusBadge from '@/Components/StatusBadge.vue';
import SiteMap from '@/Components/SiteMap.vue';
import { useApi } from '@/Composables/useApi';
import { useAuth } from '@/Composables/useAuth';
import { useToast } from '@/Composables/useToast';
import { useConfirm } from '@/Composables/useConfirm';
import logger from '@/Utils/logger';
import { getRelativeTime } from '@/Utils/helpers';

const router = useRouter();
const { getSites, createSite, updateSite, deleteSite, getAlertRules, updateAlertRule, createAlertRule, getSiteDeviceKey, rotateSiteSecret } = useApi();
const { isOperator, filterSitesByUser, isAdmin } = useAuth();
const toast = useToast();
const { confirm } = useConfirm();

const sites = ref([]);
const showAddModal = ref(false);
const editingSite = ref(null);
const modalTab = ref('info'); // 'info' | 'baku-mutu'
const alertRules = ref([]);
const loadingRules = ref(false);
const newRule = ref({ field: '', warning_min: null, warning_max: null, danger_min: null, danger_max: null });
const showAddRule = ref(false);

const AVAILABLE_FIELDS = [
  { key: 'ph', label: 'pH' }, { key: 'tss', label: 'TSS' },
  { key: 'cod', label: 'COD' }, { key: 'nh3n', label: 'NH3-N' },
  { key: 'temp', label: 'Temperatur' }, { key: 'noise', label: 'Kebisingan' },
  { key: 'pm25', label: 'PM2.5' }, { key: 'pm10', label: 'PM10' },
];

const deviceKey = ref(null);
const loadingKey = ref(false);
const showSecret = ref(false);
const rotatingSecret = ref(false);

const maskedSecret = computed(() => {
  if (!deviceKey.value?.device_secret) return '••••••••••••';
  const s = deviceKey.value.device_secret;
  return s.slice(0, 8) + '••••••••••••••••••••••••';
});

const loadDeviceKey = async (siteUid) => {
  loadingKey.value = true;
  showSecret.value = false;
  try {
    deviceKey.value = await getSiteDeviceKey(siteUid);
  } catch {
    deviceKey.value = null;
  } finally {
    loadingKey.value = false;
  }
};

const handleRotateSecret = async () => {
  if (!editingSite.value) return;
  const confirmed = await confirm(
    'Perangkat yang menggunakan secret lama akan berhenti mengirim data sampai diperbarui. Lanjutkan?'
  );
  if (!confirmed) return;
  rotatingSecret.value = true;
  try {
    deviceKey.value = await rotateSiteSecret(editingSite.value.uid);
    showSecret.value = true;
    toast.success('Secret berhasil diperbarui');
  } catch {
    toast.error('Gagal memperbarui secret');
  } finally {
    rotatingSecret.value = false;
  }
};

const copySecret = async () => {
  if (!deviceKey.value?.device_secret) return;
  try {
    await navigator.clipboard.writeText(deviceKey.value.device_secret);
    toast.success('Secret disalin ke clipboard');
  } catch {
    toast.error('Gagal menyalin');
  }
};

const siteForm = ref({
  uid: '',
  name: '',
  company_name: '',
  lat: 0,
  lon: 0,
  is_active: true,
  timezone: 'Asia/Jakarta',
});

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
      // Handle { data: [...] } structure
      sitesList = Array.isArray(response.data) ? response.data : [];
    } else {
      logger.warn('Unexpected API response format:', response);
    }

    // Filter sites based on user permissions
    sites.value = filterSitesByUser(sitesList);
  } catch (error) {
    logger.error('Failed to load sites:', error);
    sites.value = [];
  }
};

const loadAlertRules = async (siteUid) => {
  loadingRules.value = true;
  try {
    const res = await getAlertRules(siteUid);
    alertRules.value = Array.isArray(res) ? res : [];
  } catch {
    alertRules.value = [];
  } finally {
    loadingRules.value = false;
  }
};

const saveRule = async (rule) => {
  try {
    await updateAlertRule(rule.id, {
      warning_min: rule.warning_min,
      warning_max: rule.warning_max,
      danger_min: rule.danger_min,
      danger_max: rule.danger_max,
      is_active: rule.is_active,
    });
    toast.success('Aturan berhasil disimpan');
  } catch {
    toast.error('Gagal menyimpan aturan');
  }
};

const addRule = async () => {
  if (!editingSite.value || !newRule.value.field) return;
  try {
    await createAlertRule(editingSite.value.uid, newRule.value);
    await loadAlertRules(editingSite.value.uid);
    newRule.value = { field: '', warning_min: null, warning_max: null, danger_min: null, danger_max: null };
    showAddRule.value = false;
    toast.success('Aturan berhasil ditambahkan');
  } catch {
    toast.error('Gagal menambah aturan');
  }
};

const viewSite = (site) => {
  router.push(`/dashboard?site=${site.uid}`);
};

const editSite = (site) => {
  editingSite.value = site;
  siteForm.value = { ...site };
  modalTab.value = 'info';
  loadAlertRules(site.uid);
  if (isAdmin.value) loadDeviceKey(site.uid);
};

const saveSite = async () => {
  try {
    if (editingSite.value) {
      await updateSite(siteForm.value.uid, siteForm.value);
    } else {
      await createSite(siteForm.value);
    }
    await loadSites();
    closeModal();
  } catch (error) {
    toast.error('Gagal menyimpan lokasi');
  }
};

const deleteSiteHandler = async (site) => {
  const ok = await confirm(`Hapus lokasi "${site.name}"? Tindakan ini tidak dapat dibatalkan.`);
  if (!ok) return;

  try {
    await deleteSite(site.uid);
    await loadSites();
    toast.success('Lokasi berhasil dihapus');
  } catch (error) {
    logger.error('Failed to delete site:', error);
    toast.error('Gagal menghapus lokasi');
  }
};

const closeModal = () => {
  showAddModal.value = false;
  editingSite.value = null;
  modalTab.value = 'info';
  showAddRule.value = false;
  deviceKey.value = null;
  showSecret.value = false;
  siteForm.value = { uid: '', name: '', company_name: '', lat: 0, lon: 0, is_active: true, timezone: 'Asia/Jakarta' };
};

onMounted(() => {
  loadSites();
});
</script>
