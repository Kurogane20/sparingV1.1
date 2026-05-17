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

          <form @submit.prevent="saveSite" class="p-6 space-y-4">
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
        </div>
      </div>
    </div>
  </AppLayout>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import AppLayout from '@/Layouts/AppLayout.vue';
import StatusBadge from '@/Components/StatusBadge.vue';
import SiteMap from '@/Components/SiteMap.vue';
import { useApi } from '@/Composables/useApi';
import { useAuth } from '@/Composables/useAuth';
import { useToast } from '@/Composables/useToast';
import { useConfirm } from '@/Composables/useConfirm';
import logger from '@/Utils/logger';

const router = useRouter();
const { getSites, createSite, updateSite, deleteSite } = useApi();
const { isOperator, filterSitesByUser, isAdmin } = useAuth();
const toast = useToast();
const { confirm } = useConfirm();

const sites = ref([]);
const showAddModal = ref(false);
const editingSite = ref(null);

const siteForm = ref({
  uid: '',
  name: '',
  company_name: '',
  lat: 0,
  lon: 0,
  is_active: true,
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

const viewSite = (site) => {
  router.push(`/dashboard?site=${site.uid}`);
};

const editSite = (site) => {
  editingSite.value = site;
  siteForm.value = { ...site };
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
  siteForm.value = {
    uid: '',
    name: '',
    company_name: '',
    lat: 0,
    lon: 0,
    is_active: true,
  };
};

onMounted(() => {
  loadSites();
});
</script>
