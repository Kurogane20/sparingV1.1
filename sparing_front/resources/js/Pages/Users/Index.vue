<template>
  <AppLayout>
    <PageHeader :crumb="['Beranda', 'Administrasi', 'Manajemen User']" title="Manajemen User" subtitle="Kelola akun pengguna dan hak akses sistem">
      <template #actions>
        <button
          v-if="isAdmin"
          @click="showAddModal = true"
          class="px-3 py-2 rounded-md bg-primary hover:bg-primary-dark text-white text-sm flex items-center gap-2 transition-colors"
        >
          <i class="fas fa-plus text-xs"></i>Tambah Pengguna
        </button>
      </template>
    </PageHeader>

    <div class="space-y-6">
      <!-- Filter bar -->
      <div class="bg-white border border-[#D7E0E1] rounded-lg p-4">
        <div class="grid grid-cols-1 sm:grid-cols-3 gap-3 items-end">
          <div>
            <label class="block text-[11.5px] font-semibold text-ink mb-1">Cari</label>
            <div class="relative">
              <i class="fas fa-search absolute left-3 top-1/2 -translate-y-1/2 text-[#8FA0A3] text-xs"></i>
              <input v-model="searchQuery" type="text" placeholder="Nama atau email..." class="w-full border border-[#C4D1D3] rounded-md p-2 pl-8 text-sm" />
            </div>
          </div>
          <div>
            <label class="block text-[11.5px] font-semibold text-ink mb-1">Role</label>
            <select v-model="roleFilter" class="w-full border border-[#C4D1D3] rounded-md p-2 text-sm">
              <option value="">Semua</option>
              <option value="admin">Admin</option>
              <option value="operator">Operator</option>
              <option value="viewer">Viewer</option>
            </select>
          </div>
          <div>
            <label class="block text-[11.5px] font-semibold text-ink mb-1">Status Akses Site</label>
            <select v-model="siteFilter" class="w-full border border-[#C4D1D3] rounded-md p-2 text-sm">
              <option value="">Semua</option>
              <option value="assigned">Memiliki akses site</option>
              <option value="none">Belum ada akses site</option>
            </select>
          </div>
        </div>
      </div>

      <!-- Users Table -->
      <DataTable
        title="Daftar Pengguna"
        :data="filteredUsers"
        :columns="userColumns"
        :loading="loading"
        empty-message="Belum ada pengguna terdaftar"
      >
        <template #cell-role="{ value }">
          <span
            :class="[
              'inline-flex items-center gap-1 text-[10px] font-bold px-2 py-0.5 rounded tracking-wide',
              roleChipClass(value),
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
            <span class="text-sm text-ink">
              {{ row.sites?.length || 0 }} site(s)
            </span>
            <button
              v-if="row.role !== 'admin'"
              @click="manageSites(row)"
              class="text-primary hover:text-primary-dark"
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
              class="text-primary hover:text-primary-dark"
              title="Edit"
            >
              <i class="fas fa-edit"></i>
            </button>
            <button
              v-if="row.id !== currentUser?.id"
              @click="deleteUser(row)"
              class="text-danger hover:opacity-80"
              title="Hapus"
            >
              <i class="fas fa-trash"></i>
            </button>
          </div>
        </template>
      </DataTable>

      <!-- Matriks hak akses -->
      <div class="bg-white border border-[#D7E0E1] rounded-lg overflow-hidden">
        <div class="px-5 py-4 border-b border-[#D7E0E1]">
          <h3 class="text-sm font-bold text-ink">Matriks Hak Akses</h3>
          <p class="text-[12px] text-[#617377] mt-0.5">Ringkasan kapabilitas per peran pengguna</p>
        </div>
        <div class="overflow-x-auto">
          <table class="w-full text-sm">
            <thead>
              <tr class="bg-[#EEF2F3] text-left text-[11.5px] text-[#617377] uppercase tracking-wide">
                <th class="px-4 py-2.5 font-semibold">Kapabilitas</th>
                <th class="px-4 py-2.5 font-semibold text-center">Admin</th>
                <th class="px-4 py-2.5 font-semibold text-center">Operator</th>
                <th class="px-4 py-2.5 font-semibold text-center">Viewer</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-[#EEF2F3]">
              <tr v-for="row in accessMatrix" :key="row.label">
                <td class="px-4 py-2.5 text-ink">{{ row.label }}</td>
                <td class="px-4 py-2.5 text-center">
                  <i :class="row.admin ? 'fas fa-check text-success' : 'fas fa-times text-[#C6D2D3]'"></i>
                </td>
                <td class="px-4 py-2.5 text-center">
                  <i :class="row.operator ? 'fas fa-check text-success' : 'fas fa-times text-[#C6D2D3]'"></i>
                </td>
                <td class="px-4 py-2.5 text-center">
                  <i :class="row.viewer ? 'fas fa-check text-success' : 'fas fa-times text-[#C6D2D3]'"></i>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- Add/Edit Modal -->
      <div
        v-if="showAddModal || editingUser"
        class="fixed inset-0 bg-ink/40 backdrop-blur-sm flex items-center justify-center z-50 p-4"
        @click.self="closeModal"
      >
        <div class="bg-white rounded-2xl max-w-md w-full shadow-2xl">
          <div class="flex justify-between items-center px-6 py-4 border-b border-[#D7E0E1]">
            <div class="flex items-center gap-3">
              <div class="w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center">
                <i class="fas fa-user text-primary text-xs"></i>
              </div>
              <h3 class="font-bold text-ink">{{ editingUser ? 'Edit Pengguna' : 'Tambah Pengguna' }}</h3>
            </div>
            <button @click="closeModal" class="w-8 h-8 rounded-lg hover:bg-[#EEF2F3] flex items-center justify-center transition-colors">
              <i class="fas fa-times text-[#8FA0A3] text-sm"></i>
            </button>
          </div>

          <form @submit.prevent="saveUser" class="p-6 space-y-4">
            <div>
              <label class="block text-xs font-semibold text-[#617377] uppercase tracking-wide mb-1.5">Nama</label>
              <input v-model="userForm.name" type="text" required class="w-full border border-[#C4D1D3] rounded-md p-2 text-sm" />
            </div>
            <div>
              <label class="block text-xs font-semibold text-[#617377] uppercase tracking-wide mb-1.5">Email</label>
              <input v-model="userForm.email" type="email" required class="w-full border border-[#C4D1D3] rounded-md p-2 text-sm" />
            </div>
            <div v-if="!editingUser">
              <label class="block text-xs font-semibold text-[#617377] uppercase tracking-wide mb-1.5">Password</label>
              <input v-model="userForm.password" type="password" required minlength="8" class="w-full border border-[#C4D1D3] rounded-md p-2 text-sm" />
              <p class="mt-1 text-[11px] text-[#617377]">Minimal 8 karakter, mengandung huruf kapital dan angka.</p>
            </div>
            <div>
              <label class="block text-xs font-semibold text-[#617377] uppercase tracking-wide mb-1.5">Role</label>
              <select v-model="userForm.role" required class="w-full border border-[#C4D1D3] rounded-md p-2 text-sm">
                <option value="viewer">Viewer</option>
                <option value="operator">Operator</option>
                <option value="admin">Admin</option>
              </select>
            </div>
            <div class="flex gap-3 justify-end pt-4 border-t border-[#D7E0E1]">
              <button type="button" @click="closeModal" class="px-3 py-2 rounded-md border border-[#C4D1D3] text-sm text-ink hover:bg-[#EEF2F3] transition-colors">Batal</button>
              <button type="submit" class="px-3 py-2 rounded-md bg-primary hover:bg-primary-dark text-white text-sm transition-colors">
                <i class="fas fa-save mr-1.5 text-xs"></i>{{ editingUser ? 'Simpan' : 'Tambah' }}
              </button>
            </div>
          </form>
        </div>
      </div>

      <!-- Manage Sites Modal -->
      <div
        v-if="showSitesModal && managingUser"
        class="fixed inset-0 bg-ink/40 backdrop-blur-sm flex items-center justify-center z-50 p-4"
        @click.self="closeSitesModal"
      >
        <div class="bg-white rounded-2xl max-w-2xl w-full shadow-2xl flex flex-col max-h-[80vh]">
          <!-- Modal header -->
          <div class="flex justify-between items-start px-6 py-4 border-b border-[#D7E0E1] shrink-0">
            <div class="flex items-center gap-3">
              <div class="w-8 h-8 rounded-lg bg-primary-soft flex items-center justify-center">
                <i class="fas fa-map-marked-alt text-primary-dark text-xs"></i>
              </div>
              <div>
                <h3 class="font-bold text-ink leading-tight">Kelola Akses Site</h3>
                <p class="text-xs text-[#617377] mt-0.5">{{ managingUser.name }} — {{ managingUser.email }}</p>
              </div>
            </div>
            <button @click="closeSitesModal" class="w-8 h-8 rounded-lg hover:bg-[#EEF2F3] flex items-center justify-center transition-colors shrink-0">
              <i class="fas fa-times text-[#8FA0A3] text-sm"></i>
            </button>
          </div>

          <!-- Site list -->
          <div class="flex-1 overflow-y-auto p-4 space-y-1.5 scrollbar-thin">
            <div v-if="loadingSites" class="text-center py-10">
              <i class="fas fa-spinner fa-spin text-2xl text-[#C4D1D3] mb-3"></i>
              <p class="text-sm text-[#8FA0A3]">Memuat daftar site...</p>
            </div>

            <label
              v-for="site in allSites"
              :key="site.uid"
              class="flex items-center gap-3 px-4 py-3 rounded-xl border cursor-pointer transition-all"
              :class="selectedSites.includes(site.uid)
                ? 'bg-primary/5 border-primary/30'
                : 'border-[#D7E0E1] hover:bg-[#EEF2F3]'"
            >
              <input
                type="checkbox"
                :value="site.uid"
                v-model="selectedSites"
                class="w-4 h-4 text-primary border-[#C4D1D3] rounded focus:ring-primary"
              />
              <div class="flex-1 min-w-0">
                <div class="text-sm font-semibold text-ink">{{ site.name }}</div>
                <div class="text-xs text-[#8FA0A3] font-mono truncate">{{ site.uid }}</div>
              </div>
              <span class="text-[10px] text-[#8FA0A3] shrink-0">{{ site.company_name }}</span>
            </label>

            <div v-if="!loadingSites && allSites.length === 0" class="text-center py-10">
              <i class="fas fa-inbox text-3xl text-[#D7E0E1] mb-2"></i>
              <p class="text-sm text-[#8FA0A3]">Tidak ada site tersedia</p>
            </div>
          </div>

          <!-- Footer -->
          <div class="flex gap-3 justify-between items-center px-6 py-4 border-t border-[#D7E0E1] shrink-0">
            <span class="text-xs font-mono text-[#617377]">{{ selectedSites.length }} dipilih</span>
            <div class="flex gap-3">
              <button type="button" @click="closeSitesModal" class="px-3 py-2 rounded-md border border-[#C4D1D3] text-sm text-ink hover:bg-[#EEF2F3] transition-colors">Batal</button>
              <button @click="saveUserSites" :disabled="savingSites" class="px-3 py-2 rounded-md bg-primary hover:bg-primary-dark text-white text-sm disabled:opacity-50 flex items-center gap-2 transition-colors">
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
import { ref, computed, onMounted } from 'vue';
import AppLayout from '@/Layouts/AppLayout.vue';
import PageHeader from '@/Components/PageHeader.vue';
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

// Filters
const searchQuery = ref('');
const roleFilter = ref('');
const siteFilter = ref('');

const filteredUsers = computed(() => {
  return users.value.filter(u => {
    if (roleFilter.value && u.role !== roleFilter.value) return false;
    if (siteFilter.value === 'assigned' && !(u.sites?.length > 0)) return false;
    if (siteFilter.value === 'none' && (u.sites?.length > 0)) return false;
    if (searchQuery.value) {
      const q = searchQuery.value.toLowerCase();
      const name = (u.name || '').toLowerCase();
      const email = (u.email || '').toLowerCase();
      if (!name.includes(q) && !email.includes(q)) return false;
    }
    return true;
  });
});

const roleChipClass = (role) => ({
  admin: 'bg-primary-soft text-primary-dark',
  operator: 'bg-[#F7EFD9] text-[#9A6B00]',
  viewer: 'bg-[#EAEEEF] text-[#6E7E82]',
}[role] || 'bg-[#EAEEEF] text-[#6E7E82]');

// Static access matrix
const accessMatrix = [
  { label: 'Melihat dashboard & data', admin: true, operator: true, viewer: true },
  { label: 'Ekspor riwayat data', admin: true, operator: true, viewer: false },
  { label: 'Tindak lanjut & tutup alarm', admin: true, operator: true, viewer: false },
  { label: 'Konfigurasi site & kalibrasi', admin: true, operator: false, viewer: false },
  { label: 'Susun & kirim laporan', admin: true, operator: false, viewer: false },
  { label: 'Kelola user & peran', admin: true, operator: false, viewer: false },
];

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

// Turn an axios error into a readable message. FastAPI/Pydantic 422 returns
// `detail` as an array of {loc, msg}; a plain string otherwise.
const apiErrorMessage = (error, fallback) => {
  const d = error?.response?.data?.detail;
  if (Array.isArray(d)) {
    return d.map((e) => (e?.msg || '').replace(/^Value error,\s*/, '')).filter(Boolean).join('; ') || fallback;
  }
  if (typeof d === 'string') return d;
  return fallback;
};

const saveUser = async () => {
  const isEdit = !!editingUser.value;
  // Match the backend password rules up front so the user gets a clear message
  // instead of a raw 422 (only new users send a password).
  if (!isEdit) {
    const pw = userForm.value.password || '';
    if (pw.length < 8 || !/[A-Z]/.test(pw) || !/[0-9]/.test(pw)) {
      toast.error('Password minimal 8 karakter, mengandung huruf kapital dan angka.');
      return;
    }
  }
  try {
    if (isEdit) {
      await apiUpdateUser(editingUser.value.id, userForm.value);
    } else {
      await registerUser(userForm.value);
    }
    await loadUsers();
    closeModal();
    toast.success(isEdit ? 'Pengguna diperbarui' : 'Pengguna ditambahkan');
  } catch (error) {
    logger.error('Failed to save user:', error);
    toast.error(apiErrorMessage(error, 'Gagal menyimpan pengguna'));
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
