<template>
  <AppLayout>
    <div class="space-y-6">
      <!-- Header -->
      <div class="flex justify-between items-center">
        <div>
          <h2 class="text-2xl font-bold text-gray-900">Manajemen Pengguna</h2>
          <p class="text-gray-600 text-sm mt-1">Kelola akun pengguna dan hak akses sistem</p>
        </div>
        <button
          v-if="isAdmin"
          @click="showAddModal = true"
          class="px-4 py-2 bg-primary text-white rounded-lg hover:bg-opacity-90 flex items-center gap-2"
        >
          <i class="fas fa-plus"></i>
          Tambah Pengguna
        </button>
      </div>

      <!-- Users Table -->
      <DataTable
        title="Daftar Pengguna"
        :data="users"
        :columns="userColumns"
        :loading="loading"
        empty-message="Belum ada pengguna terdaftar"
      >
        <template #cell-role="{ value }">
          <span
            :class="[
              'px-2 py-1 rounded-full text-xs font-medium',
              value === 'admin'
                ? 'bg-purple-100 text-purple-800'
                : value === 'operator'
                ? 'bg-blue-100 text-blue-800'
                : 'bg-gray-100 text-gray-800',
            ]"
          >
            {{ value.toUpperCase() }}
          </span>
        </template>

        <template #cell-created_at="{ value }">
          {{ formatDate(value, false) }}
        </template>

        <template #cell-sites="{ row }">
          <div class="flex items-center gap-2">
            <span class="text-sm text-gray-600">
              {{ row.sites?.length || 0 }} site(s)
            </span>
            <button
              v-if="row.role !== 'admin'"
              @click="manageSites(row)"
              class="text-primary hover:text-opacity-80"
              title="Kelola Akses Site"
            >
              <i class="fas fa-map-marked-alt"></i>
            </button>
          </div>
        </template>

        <template #cell-actions="{ row }">
          <div class="flex items-center gap-3">
            <button
              @click="updateUser(row)"
              class="text-blue-600 hover:text-blue-800"
              title="Edit"
            >
              <i class="fas fa-edit"></i>
            </button>
            <button
              v-if="row.id !== currentUser?.id"
              @click="deleteUser(row)"
              class="text-red-600 hover:text-red-800"
              title="Hapus"
            >
              <i class="fas fa-trash"></i>
            </button>
          </div>
        </template>
      </DataTable>

      <!-- Add/Edit Modal -->
      <div
        v-if="showAddModal || editingUser"
        class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4"
        @click.self="closeModal"
      >
        <div class="bg-white rounded-2xl max-w-md w-full p-6">
          <div class="flex justify-between items-center mb-4">
            <h3 class="text-xl font-bold text-gray-900">
              {{ editingUser ? 'Edit Pengguna' : 'Tambah Pengguna' }}
            </h3>
            <button @click="closeModal" class="text-gray-400 hover:text-gray-600">
              <i class="fas fa-times text-xl"></i>
            </button>
          </div>

          <form @submit.prevent="saveUser" class="space-y-4">
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-2">Nama</label>
              <input
                v-model="userForm.name"
                type="text"
                required
                class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary"
              />
            </div>

            <div>
              <label class="block text-sm font-medium text-gray-700 mb-2">Email</label>
              <input
                v-model="userForm.email"
                type="email"
                required
                class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary"
              />
            </div>

            <div v-if="!editingUser">
              <label class="block text-sm font-medium text-gray-700 mb-2">Password</label>
              <input
                v-model="userForm.password"
                type="password"
                required
                minlength="8"
                class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary"
              />
            </div>

            <div>
              <label class="block text-sm font-medium text-gray-700 mb-2">Role</label>
              <select
                v-model="userForm.role"
                required
                class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary"
              >
                <option value="viewer">Viewer</option>
                <option value="operator">Operator</option>
                <option value="admin">Admin</option>
              </select>
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
                {{ editingUser ? 'Simpan' : 'Tambah' }}
              </button>
            </div>
          </form>
        </div>
      </div>

      <!-- Manage Sites Modal -->
      <div
        v-if="showSitesModal && managingUser"
        class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4"
        @click.self="closeSitesModal"
      >
        <div class="bg-white rounded-2xl max-w-2xl w-full p-6 max-h-[80vh] overflow-y-auto">
          <div class="flex justify-between items-center mb-4">
            <div>
              <h3 class="text-xl font-bold text-gray-900">Kelola Akses Site</h3>
              <p class="text-sm text-gray-600 mt-1">
                {{ managingUser.name }} ({{ managingUser.email }})
              </p>
            </div>
            <button @click="closeSitesModal" class="text-gray-400 hover:text-gray-600">
              <i class="fas fa-times text-xl"></i>
            </button>
          </div>

          <div class="mb-4">
            <p class="text-sm text-gray-600 mb-3">
              Pilih site yang dapat diakses oleh user ini:
            </p>

            <div v-if="loadingSites" class="text-center py-8">
              <i class="fas fa-spinner fa-spin text-2xl text-gray-400"></i>
              <p class="text-sm text-gray-600 mt-2">Memuat daftar site...</p>
            </div>

            <div v-else class="space-y-2 max-h-96 overflow-y-auto">
              <label
                v-for="site in allSites"
                :key="site.uid"
                class="flex items-center gap-3 p-3 border border-gray-200 rounded-lg hover:bg-gray-50 cursor-pointer transition-colors"
                :class="selectedSites.includes(site.uid) ? 'bg-primary bg-opacity-5 border-primary' : ''"
              >
                <input
                  type="checkbox"
                  :value="site.uid"
                  v-model="selectedSites"
                  class="w-4 h-4 text-primary border-gray-300 rounded focus:ring-primary"
                />
                <div class="flex-1">
                  <div class="font-medium text-gray-900">{{ site.name }}</div>
                  <div class="text-sm text-gray-600">{{ site.company_name }} • {{ site.uid }}</div>
                </div>
                <i class="fas fa-map-marker-alt text-primary"></i>
              </label>

              <div v-if="allSites.length === 0" class="text-center py-8 text-gray-500">
                <i class="fas fa-inbox text-3xl mb-2"></i>
                <p>Tidak ada site tersedia</p>
              </div>
            </div>
          </div>

          <div class="flex gap-3 justify-between items-center pt-4 border-t">
            <div class="text-sm text-gray-600">
              {{ selectedSites.length }} site dipilih
            </div>
            <div class="flex gap-3">
              <button
                type="button"
                @click="closeSitesModal"
                class="px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300"
              >
                Batal
              </button>
              <button
                @click="saveUserSites"
                :disabled="savingSites"
                class="px-4 py-2 bg-primary text-white rounded-lg hover:bg-opacity-90 disabled:opacity-50 flex items-center gap-2"
              >
                <i v-if="savingSites" class="fas fa-spinner fa-spin"></i>
                <i v-else class="fas fa-save"></i>
                {{ savingSites ? 'Menyimpan...' : 'Simpan' }}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </AppLayout>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import AppLayout from '@/Layouts/AppLayout.vue';
import DataTable from '@/Components/DataTable.vue';
import { useApi } from '@/Composables/useApi';
import { useAuth } from '@/Composables/useAuth';
import { formatDate } from '@/Utils/helpers';
import logger from '@/Utils/logger';

const { getUsers, registerUser, updateUser: apiUpdateUser, deleteUser: apiDeleteUser, getSites, updateUserSites, getViewerSites } = useApi();
const { isAdmin, user: currentUser } = useAuth();

const users = ref([]);
const loading = ref(false);
const showAddModal = ref(false);
const editingUser = ref(null);

// Sites management
const showSitesModal = ref(false);
const managingUser = ref(null);
const allSites = ref([]);
const selectedSites = ref([]);
const loadingSites = ref(false);
const savingSites = ref(false);

const userForm = ref({
  name: '',
  email: '',
  password: '',
  role: 'viewer',
});

const userColumns = [
  { key: 'id', label: 'ID' },
  { key: 'name', label: 'Nama' },
  { key: 'email', label: 'Email' },
  { key: 'role', label: 'Role' },
  { key: 'sites', label: 'Akses Site' },
  { key: 'created_at', label: 'Dibuat' },
  { key: 'actions', label: 'Aksi' },
];

const loadUsers = async () => {
  loading.value = true;
  try {
    const response = await getUsers();
    logger.log('Users API Response:', response);

    // Handle different possible response structures
    let usersList = [];
    if (response && response.items) {
      usersList = response.items;
    } else if (response && response.users) {
      // Handle { users: [...] } structure
      usersList = Array.isArray(response.users) ? response.users : [];
    } else if (Array.isArray(response)) {
      usersList = response;
    } else if (response && response.data) {
      // Handle { data: [...] } structure
      usersList = Array.isArray(response.data) ? response.data : [];
    } else {
      usersList = [];
      logger.warn('Unexpected API response format:', response);
    }

    // Get viewer-site assignments and sites in parallel
    try {
      const [viewerSitesResponse, sitesResponse] = await Promise.all([
        getViewerSites(),
        getSites({ per_page: 100 })
      ]);

      logger.log('Viewer-Sites API Response:', viewerSitesResponse);
      logger.log('Sites API Response for mapping:', sitesResponse);

      const viewerSites = viewerSitesResponse?.viewer_sites || [];

      // Extract all sites for mapping
      let allSites = [];
      if (sitesResponse?.items) {
        allSites = sitesResponse.items;
      } else if (Array.isArray(sitesResponse)) {
        allSites = sitesResponse;
      }

      // Create site_id to site_uid mapping
      const siteIdToUidMap = {};
      allSites.forEach(site => {
        if (site.id && site.uid) {
          siteIdToUidMap[site.id] = site.uid;
        }
      });

      logger.log('Site ID to UID map:', siteIdToUidMap);

      // Map sites to users (convert site_id to site_uid)
      users.value = usersList.map(user => {
        // Find all site assignments for this user
        const userSiteIds = viewerSites
          .filter(vs => vs.user_id === user.id)
          .map(vs => vs.site_id);

        // Convert site_ids to site_uids
        const userSiteUids = userSiteIds
          .map(siteId => siteIdToUidMap[siteId])
          .filter(uid => uid !== undefined);

        logger.log(`User ${user.id}: site_ids=[${userSiteIds}] → site_uids=[${userSiteUids}]`);

        return {
          ...user,
          sites: userSiteUids
        };
      });
    } catch (error) {
      logger.error('Failed to load viewer-sites, using users without site info:', error);
      users.value = usersList;
    }

    logger.log('Users array after parsing:', users.value);
    logger.log('First user object:', users.value[0]);
  } catch (error) {
    logger.error('Failed to load users:', error);
    users.value = [];
  } finally {
    loading.value = false;
  }
};

const updateUser = (user) => {
  editingUser.value = user;
  userForm.value = {
    name: user.name,
    email: user.email,
    role: user.role,
  };
};

const deleteUser = async (user) => {
  if (!confirm(`Apakah Anda yakin ingin menghapus pengguna "${user.username || user.email}"? Tindakan ini tidak dapat dibatalkan.`)) {
    return;
  }

  try {
    await apiDeleteUser(user.id);
    await loadUsers();
    alert('Pengguna berhasil dihapus');
  } catch (error) {
    logger.error('Failed to delete user:', error);
    alert('Gagal menghapus pengguna');
  }
};

const saveUser = async () => {
  try {
    if (editingUser.value) {
      // Update existing user
      await apiUpdateUser(editingUser.value.id, userForm.value);
      await loadUsers();
      closeModal();
    } else {
      // Create new user
      await registerUser(userForm.value);
      await loadUsers();
      closeModal();
    }
  } catch (error) {
    logger.error('Failed to save user:', error);
    alert('Gagal menyimpan pengguna');
  }
};

const closeModal = () => {
  showAddModal.value = false;
  editingUser.value = null;
  userForm.value = {
    name: '',
    email: '',
    password: '',
    role: 'viewer',
  };
};

// Manage sites for user
const manageSites = async (user) => {
  managingUser.value = user;
  selectedSites.value = user.sites || [];
  showSitesModal.value = true;

  // Load all sites
  loadingSites.value = true;
  try {
    const response = await getSites({ per_page: 100 });
    // Handle different possible response structures
    if (response && response.items) {
      allSites.value = response.items;
    } else if (Array.isArray(response)) {
      allSites.value = response;
    } else if (response && response.data) {
      allSites.value = Array.isArray(response.data) ? response.data : [];
    } else {
      allSites.value = [];
      logger.warn('Unexpected API response format:', response);
    }
  } catch (error) {
    logger.error('Failed to load sites:', error);
    allSites.value = [];
    alert('Gagal memuat daftar site');
  } finally {
    loadingSites.value = false;
  }
};

const saveUserSites = async () => {
  if (!managingUser.value) return;

  savingSites.value = true;
  try {
    const result = await updateUserSites(managingUser.value.id, selectedSites.value);

    // Update local user data
    const userIndex = users.value.findIndex(u => u.id === managingUser.value.id);
    if (userIndex !== -1) {
      users.value[userIndex].sites = [...selectedSites.value];
    }

    // Show success message with details
    const message = result.added > 0 || result.removed > 0
      ? `Akses site berhasil diperbarui!\n\n` +
        `- ${result.added} site ditambahkan\n` +
        `- ${result.removed} site dihapus`
      : 'Tidak ada perubahan akses site';

    alert(message);
    closeSitesModal();
  } catch (error) {
    logger.error('Failed to save user sites:', error);

    // Show detailed error message
    const errorMessage = error.response?.data?.detail || error.message || 'Gagal menyimpan akses site';
    alert(`Error: ${errorMessage}\n\nPeriksa console untuk detail lebih lanjut.`);
  } finally {
    savingSites.value = false;
  }
};

const closeSitesModal = () => {
  showSitesModal.value = false;
  managingUser.value = null;
  selectedSites.value = [];
  allSites.value = [];
};

onMounted(() => {
  loadUsers();
});
</script>
