<template>
  <AppLayout>
    <div class="space-y-6">
      <!-- Page Header -->
      <div>
        <h2 class="text-xl font-bold text-slate-800">Pengaturan Sistem</h2>
        <p class="text-slate-500 text-sm mt-0.5">Kelola konfigurasi akun dan sistem</p>
      </div>

      <!-- User Profile Settings -->
      <div class="card p-5 md:p-6">
        <div class="flex items-center gap-3 mb-5">
          <div class="w-8 h-8 rounded-lg bg-[#E4F1F2] flex items-center justify-center shrink-0">
            <i class="fas fa-user text-[#0E7C86] text-xs"></i>
          </div>
          <h3 class="card-title">Profil Pengguna</h3>
        </div>

        <div class="space-y-4 max-w-lg">
          <div>
            <label class="block text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1.5">Email</label>
            <input :value="user?.email" type="email" disabled
              class="form-input text-sm bg-slate-50 text-slate-400 cursor-not-allowed" />
          </div>
          <div>
            <label class="block text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1.5">Nama Lengkap</label>
            <input v-model="profileForm.name" type="text" placeholder="Nama Lengkap" class="form-input text-sm" />
          </div>
          <div>
            <label class="block text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1.5">Role</label>
            <input :value="user?.role || 'viewer'" type="text" disabled
              class="form-input text-sm bg-slate-50 text-slate-400 cursor-not-allowed capitalize" />
          </div>
          <div class="pt-2">
            <button @click="updateProfile" class="btn-primary text-sm">
              <i class="fas fa-save mr-1.5"></i>Simpan Perubahan
            </button>
          </div>
        </div>
      </div>

      <!-- Change Password -->
      <div class="card p-5 md:p-6">
        <div class="flex items-center gap-3 mb-5">
          <div class="w-8 h-8 rounded-lg bg-amber-50 flex items-center justify-center shrink-0">
            <i class="fas fa-lock text-amber-600 text-xs"></i>
          </div>
          <h3 class="card-title">Ubah Password</h3>
        </div>

        <form @submit.prevent="changePassword" class="space-y-4 max-w-lg">
          <div>
            <label class="block text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1.5">Password Saat Ini</label>
            <input v-model="passwordForm.currentPassword" type="password" required class="form-input text-sm" />
          </div>
          <div>
            <label class="block text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1.5">Password Baru</label>
            <input v-model="passwordForm.newPassword" type="password" required minlength="8" class="form-input text-sm" />
          </div>
          <div>
            <label class="block text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1.5">Konfirmasi Password Baru</label>
            <input v-model="passwordForm.confirmPassword" type="password" required class="form-input text-sm" />
          </div>
          <div v-if="passwordError" class="p-3 bg-red-50 border border-red-100 rounded-lg text-xs text-red-700 flex items-center gap-2">
            <i class="fas fa-exclamation-circle shrink-0"></i>{{ passwordError }}
          </div>
          <div class="pt-2">
            <button type="submit" class="btn-primary text-sm">
              <i class="fas fa-key mr-1.5"></i>Ubah Password
            </button>
          </div>
        </form>
      </div>

      <!-- System Settings (Admin Only) -->
      <div v-if="isAdmin" class="card p-5 md:p-6">
        <div class="flex items-center gap-3 mb-5">
          <div class="w-8 h-8 rounded-lg bg-[#E4F1F2] flex items-center justify-center shrink-0">
            <i class="fas fa-server text-[#0E7C86] text-xs"></i>
          </div>
          <h3 class="card-title">Pengaturan Sistem</h3>
        </div>

        <div class="space-y-4 max-w-lg">
          <div>
            <label class="block text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1.5">API Base URL</label>
            <input v-model="systemSettings.apiUrl" type="url" placeholder="http://localhost:8000" class="form-input text-sm font-mono" />
          </div>
          <div>
            <label class="block text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1.5">Interval Refresh Data (detik)</label>
            <input v-model.number="systemSettings.refreshInterval" type="number" min="5" max="300" class="form-input text-sm font-mono" />
          </div>
          <div class="flex items-center gap-3 py-1">
            <input v-model="systemSettings.autoRefresh" type="checkbox" id="auto_refresh"
              class="w-4 h-4 text-primary border-slate-300 rounded focus:ring-primary" />
            <label for="auto_refresh" class="text-sm text-slate-700">Auto Refresh Aktif</label>
          </div>
          <div class="pt-2">
            <button @click="updateSystemSettings" class="btn-primary text-sm">
              <i class="fas fa-save mr-1.5"></i>Simpan Pengaturan
            </button>
          </div>
        </div>
      </div>

      <!-- About -->
      <div class="card p-5 md:p-6">
        <div class="flex items-center gap-3 mb-4">
          <div class="w-8 h-8 rounded-lg bg-slate-100 flex items-center justify-center shrink-0">
            <i class="fas fa-info-circle text-slate-500 text-xs"></i>
          </div>
          <h3 class="card-title">Tentang Sistem</h3>
        </div>
        <div class="divide-y divide-slate-100 max-w-lg">
          <div class="flex justify-between items-center py-2.5">
            <span class="text-xs text-slate-500">Nama Aplikasi</span>
            <span class="text-xs font-bold text-slate-800 font-mono">SPARING</span>
          </div>
          <div class="flex justify-between items-center py-2.5">
            <span class="text-xs text-slate-500">Versi</span>
            <span class="text-xs font-bold text-slate-800 font-mono">1.0.0</span>
          </div>
          <div class="flex justify-between items-center py-2.5">
            <span class="text-xs text-slate-500">Build</span>
            <span class="text-xs font-bold text-slate-800 font-mono">2025.01.01</span>
          </div>
          <div class="flex justify-between items-center py-2.5">
            <span class="text-xs text-slate-500">API Version</span>
            <span class="text-xs font-bold text-slate-800 font-mono">v1</span>
          </div>
        </div>
      </div>
    </div>
  </AppLayout>
</template>

<script setup>
import { ref } from 'vue';
import AppLayout from '@/Layouts/AppLayout.vue';
import { useAuth } from '@/Composables/useAuth';
import { useApi } from '@/Composables/useApi';
import { useToast } from '@/Composables/useToast';
import logger from '@/Utils/logger';

// Composables
const { user, isAdmin } = useAuth();
const { updateProfile: apiUpdateProfile, changePassword: apiChangePassword } = useApi();
const toast = useToast();

// Profile form
const profileForm = ref({
  name: user.value?.name || '',
});

// Password form
const passwordForm = ref({
  currentPassword: '',
  newPassword: '',
  confirmPassword: '',
});

const passwordError = ref(null);

// System settings
const systemSettings = ref({
  apiUrl: import.meta.env.VITE_API_URL || 'http://localhost:8000',
  refreshInterval: 30,
  autoRefresh: true,
});

// Update profile
const updateProfile = async () => {
  try {
    await apiUpdateProfile({ name: profileForm.value.name });
    toast.success('Profil berhasil diperbarui');
  } catch (err) {
    toast.error(err.response?.data?.detail || 'Gagal memperbarui profil');
  }
};

// Change password
const changePassword = async () => {
  passwordError.value = null;

  if (passwordForm.value.newPassword !== passwordForm.value.confirmPassword) {
    passwordError.value = 'Password baru dan konfirmasi tidak cocok';
    return;
  }

  try {
    await apiChangePassword({
      current_password: passwordForm.value.currentPassword,
      new_password: passwordForm.value.newPassword,
    });
    toast.success('Password berhasil diubah');
    passwordForm.value = { currentPassword: '', newPassword: '', confirmPassword: '' };
  } catch (err) {
    passwordError.value = err.response?.data?.detail || 'Gagal mengubah password';
  }
};

// Update system settings
const updateSystemSettings = () => {
  logger.log('Update system settings:', systemSettings.value);
  toast.success('Pengaturan sistem berhasil diperbarui');
};
</script>
