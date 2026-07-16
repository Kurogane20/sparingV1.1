<template>
  <AppLayout>
    <div class="space-y-6">
      <!-- Header -->
      <div class="flex justify-between items-center">
        <div>
          <h2 class="text-xl font-bold text-slate-800">Manajemen Pengguna</h2>
          <p class="text-slate-500 text-sm mt-0.5">Kelola akun pengguna dan hak akses sistem</p>
        </div>
        <button
          v-if="isAdmin"
          @click="showAddModal = true"
          class="btn-primary flex items-center gap-2 text-sm"
        >
          <i class="fas fa-plus text-xs"></i>Tambah Pengguna
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
              'inline-flex items-center gap-1 text-[10px] font-bold px-2 py-0.5 rounded tracking-wide',
              value === 'admin'
                ? 'bg-violet-50 text-violet-700 border border-violet-200'
                : value === 'operator'
                ? 'bg-[#E4F1F2] text-[#0A5A62] border border-[#B9D9DB]'
                : 'bg-slate-100 text-slate-600 border border-slate-200',
            ]"
          >
            <span class="w-1.5 h-1.5 rounded-full"
              :class="value === 'admin' ? 'bg-violet-500' : value === 'operator' ? 'bg-[#E4F1F2]0' : 'bg-slate-400'"
            ></span>
            {{ value.toUpperCase() }}
          </span>
        </template>

        <template #cell-created_at="{ value }">
          {{ formatDate(value, false) }}
        </template>

        <template #cell-sites="{ row }">
          <div class="flex items-center gap-2">
            <span class="text-sm text-slate-600">
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
              class="text-[#0E7C86] hover:text-[#0A5A62]"
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
        class="fixed inset-0 bg-slate-900/60 backdrop-blur-sm flex items-center justify-center z-50 p-4"
        @click.self="closeModal"
      >
        <div class="bg-white rounded-2xl max-w-md w-full shadow-2xl">
          <div class="flex justify-between items-center px-6 py-4 border-b border-slate-100">
            <div class="flex items-center gap-3">
              <div class="w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center">
                <i class="fas fa-user text-primary text-xs"></i>
              </div>
              <h3 class="font-bold text-slate-800">{{ editingUser ? 'Edit Pengguna' : 'Tambah Pengguna' }}</h3>
            </div>
            <button @click="closeModal" class="w-8 h-8 rounded-lg hover:bg-slate-100 flex items-center justify-center transition-colors">
              <i class="fas fa-times text-slate-400 text-sm"></i>
            </button>
          </div>

          <form @submit.prevent="saveUser" class="p-6 space-y-4">
            <div>
              <label class="block text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1.5">Nama</label>
              <input v-model="userForm.name" type="text" required class="form-input text-sm" />
            </div>
            <div>
              <label class="block text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1.5">Email</label>
              <input v-model="userForm.email" type="email" required class="form-input text-sm" />
            </div>
            <div v-if="!editingUser">
              <label class="block text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1.5">Password</label>
              <input v-model="userForm.password" type="password" required minlength="8" class="form-input text-sm" />
            </div>
            <div>
              <label class="block text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1.5">Role</label>
              <select v-model="userForm.role" required class="form-input text-sm">
                <option value="viewer">Viewer</option>
                <option value="operator">Operator</option>
                <option value="admin">Admin</option>
              </select>
            </div>
            <div class="flex gap-3 justify-end pt-4 border-t border-slate-100">
              <button type="button" @click="closeModal" class="btn-secondary text-sm">Batal</button>
              <button type="submit" class="btn-primary text-sm">
                <i class="fas fa-save mr-1.5 text-xs"></i>{{ editingUser ? 'Simpan' : 'Tambah' }}
              </button>
            </div>
          </form>
        </div>
      </div>

      <!-- Manage Sites Modal -->
      <div
        v-if="showSitesModal && managingUser"
        class="fixed inset-0 bg-slate-900/60 backdrop-blur-sm flex items-center justify-center z-50 p-4"
        @click.self="closeSitesModal"
      >
        <div class="bg-white rounded-2xl max-w-2xl w-full shadow-2xl flex flex-col max-h-[80vh]">
          <!-- Modal header -->
          <div class="flex justify-between items-start px-6 py-4 border-b border-slate-100 shrink-0">
            <div class="flex items-center gap-3">
              <div class="w-8 h-8 rounded-lg bg-teal-50 flex items-center justify-center">
                <i class="fas fa-map-marked-alt text-teal-600 text-xs"></i>
              </div>
              <div>
                <h3 class="font-bold text-slate-800 leading-tight">Kelola Akses Site</h3>
                <p class="text-xs text-slate-500 mt-0.5">{{ managingUser.name }} — {{ managingUser.email }}</p>
              </div>
            </div>
            <button @click="closeSitesModal" class="w-8 h-8 rounded-lg hover:bg-slate-100 flex items-center justify-center transition-colors shrink-0">
              <i class="fas fa-times text-slate-400 text-sm"></i>
            </button>
          </div>

          <!-- Site list -->
          <div class="flex-1 overflow-y-auto p-4 space-y-1.5 scrollbar-thin">
            <div v-if="loadingSites" class="text-center py-10">
              <i class="fas fa-spinner fa-spin text-2xl text-slate-300 mb-3"></i>
              <p class="text-sm text-slate-400">Memuat daftar site...</p>
            </div>

            <label
              v-for="site in allSites"
              :key="site.uid"
              class="flex items-center gap-3 px-4 py-3 rounded-xl border cursor-pointer transition-all"
              :class="selectedSites.includes(site.uid)
                ? 'bg-primary/5 border-primary/30'
                : 'border-slate-200 hover:bg-slate-50'"
            >
              <input
                type="checkbox"
                :value="site.uid"
                v-model="selectedSites"
                class="w-4 h-4 text-primary border-slate-300 rounded focus:ring-primary"
              />
              <div class="flex-1 min-w-0">
                <div class="text-sm font-semibold text-slate-800">{{ site.name }}</div>
                <div class="text-xs text-slate-400 font-mono truncate">{{ site.uid }}</div>
              </div>
              <span class="text-[10px] text-slate-400 shrink-0">{{ site.company_name }}</span>
            </label>

            <div v-if="!loadingSites && allSites.length === 0" class="text-center py-10">
              <i class="fas fa-inbox text-3xl text-slate-200 mb-2"></i>
              <p class="text-sm text-slate-400">Tidak ada site tersedia</p>
            </div>
          </div>

          <!-- Footer -->
          <div class="flex gap-3 justify-between items-center px-6 py-4 border-t border-slate-100 shrink-0">
            <span class="text-xs font-mono text-slate-500">{{ selectedSites.length }} dipilih</span>
            <div class="flex gap-3">
              <button type="button" @click="closeSitesModal" class="btn-secondary text-sm">Batal</button>
              <button @click="saveUserSites" :disabled="savingSites" class="btn-primary text-sm disabled:opacity-50 flex items-center gap-2">
                <i :class="savingSites ? 'fas fa-spinner fa-spin' : 'fas fa-save'" class="text-xs"></i>
                {{ savingSites ? 'Menyimpan...' : 'Simpan Akses' }}
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
import { useToast } from '@/Composables/useToast';
import { useConfirm } from '@/Composables/useConfirm';
import { formatDate } from '@/Utils/helpers';
import logger from '@/Utils/logger';

const { getUsers, registerUser, updateUser: apiUpdateUser, deleteUser: apiDeleteUser, getSites, updateUserSites, getViewerSites } = useApi();
const { isAdmin, user: currentUser } = useAuth();
const toast = useToast();
const { confirm } = useConfirm();

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
  const ok = await confirm(`Hapus pengguna "${user.username || user.email}"? Tindakan ini tidak dapat dibatalkan.`);
  if (!ok) return;

  try {
    await apiDeleteUser(user.id);
    await loadUsers();
    toast.success('Pengguna berhasil dihapus');
  } catch (error) {
    logger.error('Failed to delete user:', error);
    toast.error('Gagal menghapus pengguna');
  }
};

const saveUser = async () => {
  try {
    if (editingUser.value) {
      await apiUpdateUser(editingUser.value.id, userForm.value);
      await loadUsers();
      closeModal();
    } else {
      await registerUser(userForm.value);
      await loadUsers();
      closeModal();
    }
  } catch (error) {
    logger.error('Failed to save user:', error);
    toast.error('Gagal menyimpan pengguna');
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
    toast.error('Gagal memuat daftar site');
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
    if (result.added > 0 || result.removed > 0) {
      toast.success(`Akses site diperbarui: +${result.added} / -${result.removed}`);
    } else {
      toast.info('Tidak ada perubahan akses site');
    }
    closeSitesModal();
  } catch (error) {
    logger.error('Failed to save user sites:', error);
    const errorMessage = error.response?.data?.detail || error.message || 'Gagal menyimpan akses site';
    toast.error(errorMessage);
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
