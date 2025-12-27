<template>
  <AppLayout>
    <div class="space-y-6">
      <!-- Header -->
      <div class="flex justify-between items-center">
        <div>
          <h2 class="text-2xl font-bold text-gray-900">Manajemen Lokasi</h2>
          <p class="text-gray-600 text-sm mt-1">Kelola lokasi monitoring air limbah</p>
        </div>
        <button
          v-if="isOperator"
          @click="showAddModal = true"
          class="px-4 py-2 bg-primary text-white rounded-lg hover:bg-opacity-90 flex items-center gap-2"
        >
          <i class="fas fa-plus"></i>
          Tambah Lokasi
        </button>
      </div>

      <!-- Sites Grid -->
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        <div
          v-for="site in sites"
          :key="site.uid"
          class="bg-white rounded-2xl p-6 shadow-sm hover:shadow-md transition-shadow"
        >
          <div class="flex justify-between items-start mb-4">
            <div>
              <h3 class="text-lg font-semibold text-gray-900">{{ site.name }}</h3>
              <p class="text-sm text-gray-600">{{ site.company_name }}</p>
            </div>
            <StatusBadge
              :status="site.is_active ? 'active' : 'inactive'"
              :label="site.is_active ? 'Aktif' : 'Nonaktif'"
            />
          </div>

          <div class="space-y-2 text-sm text-gray-600 mb-4">
            <div class="flex items-start gap-2">
              <i class="fas fa-map-marker-alt mt-0.5 text-primary"></i>
              <span>{{ site.lat }}, {{ site.lon }}</span>
            </div>
            <div class="flex items-start gap-2">
              <i class="fas fa-fingerprint mt-0.5 text-primary"></i>
              <span>UID: {{ site.uid }}</span>
            </div>
          </div>

          <div class="flex gap-2">
            <button
              @click="viewSite(site)"
              class="flex-1 px-3 py-2 bg-primary text-white rounded-lg hover:bg-opacity-90 text-sm"
            >
              <i class="fas fa-eye mr-1"></i> Lihat
            </button>
            <button
              v-if="isOperator"
              @click="editSite(site)"
              class="px-3 py-2 bg-yellow-500 text-white rounded-lg hover:bg-opacity-90 text-sm"
              title="Edit"
            >
              <i class="fas fa-edit"></i>
            </button>
            <button
              v-if="isAdmin"
              @click="deleteSiteHandler(site)"
              class="px-3 py-2 bg-red-500 text-white rounded-lg hover:bg-opacity-90 text-sm"
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
        class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4"
        @click.self="closeModal"
      >
        <div class="bg-white rounded-2xl max-w-2xl w-full p-6 max-h-[90vh] overflow-y-auto">
          <div class="flex justify-between items-center mb-4">
            <h3 class="text-xl font-bold text-gray-900">
              {{ editingSite ? 'Edit Lokasi' : 'Tambah Lokasi' }}
            </h3>
            <button @click="closeModal" class="text-gray-400 hover:text-gray-600">
              <i class="fas fa-times text-xl"></i>
            </button>
          </div>

          <form @submit.prevent="saveSite" class="space-y-4">
            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label class="block text-sm font-medium text-gray-700 mb-2">UID Lokasi</label>
                <input
                  v-model="siteForm.uid"
                  type="text"
                  required
                  :disabled="!!editingSite"
                  class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary disabled:bg-gray-100"
                  placeholder="aqmsFOEmmEPISI01"
                />
              </div>

              <div>
                <label class="block text-sm font-medium text-gray-700 mb-2">Nama Lokasi</label>
                <input
                  v-model="siteForm.name"
                  type="text"
                  required
                  class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary"
                />
              </div>
            </div>

            <div>
              <label class="block text-sm font-medium text-gray-700 mb-2">Nama Perusahaan</label>
              <input
                v-model="siteForm.company_name"
                type="text"
                required
                class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary"
              />
            </div>

            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label class="block text-sm font-medium text-gray-700 mb-2">Latitude</label>
                <input
                  v-model.number="siteForm.lat"
                  type="number"
                  step="any"
                  required
                  class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary"
                />
              </div>

              <div>
                <label class="block text-sm font-medium text-gray-700 mb-2">Longitude</label>
                <input
                  v-model.number="siteForm.lon"
                  type="number"
                  step="any"
                  required
                  class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary"
                />
              </div>
            </div>

            <div class="flex items-center gap-3">
              <input
                v-model="siteForm.is_active"
                type="checkbox"
                id="is_active"
                class="w-4 h-4 text-primary border-gray-300 rounded focus:ring-primary"
              />
              <label for="is_active" class="text-sm font-medium text-gray-700">
                Lokasi Aktif
              </label>
            </div>

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
                class="px-4 py-2 bg-primary text-white rounded-lg hover:bg-opacity-90"
              >
                {{ editingSite ? 'Simpan' : 'Tambah' }}
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
import { useApi } from '@/Composables/useApi';
import { useAuth } from '@/Composables/useAuth';
import logger from '@/Utils/logger';

const router = useRouter();
const { getSites, createSite, updateSite, deleteSite } = useApi();
const { isOperator, filterSitesByUser, isAdmin } = useAuth();

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
    alert('Gagal menyimpan lokasi');
  }
};

const deleteSiteHandler = async (site) => {
  if (!confirm(`Apakah Anda yakin ingin menghapus lokasi "${site.name}"? Tindakan ini tidak dapat dibatalkan.`)) {
    return;
  }

  try {
    await deleteSite(site.uid);
    await loadSites();
    alert('Lokasi berhasil dihapus');
  } catch (error) {
    logger.error('Failed to delete site:', error);
    alert('Gagal menghapus lokasi');
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
