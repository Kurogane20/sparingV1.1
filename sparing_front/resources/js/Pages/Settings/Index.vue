<template>
  <AppLayout>
    <div class="space-y-6">
      <!-- Page Header -->
      <div>
        <h2 class="text-2xl font-bold text-gray-900">Pengaturan Sistem</h2>
        <p class="text-gray-600 text-sm mt-1">
          Kelola konfigurasi akun dan sistem
        </p>
      </div>

      <!-- User Profile Settings -->
      <div class="bg-white rounded-2xl p-6 shadow-sm">
        <h3 class="text-lg font-semibold text-gray-900 mb-4">Profil Pengguna</h3>

        <div class="space-y-4 max-w-2xl">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-2">
              Email
            </label>
            <input
              :value="user?.email"
              type="email"
              disabled
              class="w-full px-3 py-2 border border-gray-300 rounded-lg bg-gray-50 text-gray-600"
            />
          </div>

          <div>
            <label class="block text-sm font-medium text-gray-700 mb-2">
              Nama
            </label>
            <input
              v-model="profileForm.name"
              type="text"
              class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary"
              placeholder="Nama Lengkap"
            />
          </div>

          <div>
            <label class="block text-sm font-medium text-gray-700 mb-2">
              Role
            </label>
            <input
              :value="user?.role || 'viewer'"
              type="text"
              disabled
              class="w-full px-3 py-2 border border-gray-300 rounded-lg bg-gray-50 text-gray-600 capitalize"
            />
          </div>

          <div class="pt-4">
            <button
              @click="updateProfile"
              class="px-6 py-2 bg-primary text-white rounded-lg hover:bg-opacity-90"
            >
              Simpan Perubahan
            </button>
          </div>
        </div>
      </div>

      <!-- Change Password -->
      <div class="bg-white rounded-2xl p-6 shadow-sm">
        <h3 class="text-lg font-semibold text-gray-900 mb-4">Ubah Password</h3>

        <form @submit.prevent="changePassword" class="space-y-4 max-w-2xl">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-2">
              Password Saat Ini
            </label>
            <input
              v-model="passwordForm.currentPassword"
              type="password"
              required
              class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary"
            />
          </div>

          <div>
            <label class="block text-sm font-medium text-gray-700 mb-2">
              Password Baru
            </label>
            <input
              v-model="passwordForm.newPassword"
              type="password"
              required
              minlength="8"
              class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary"
            />
          </div>

          <div>
            <label class="block text-sm font-medium text-gray-700 mb-2">
              Konfirmasi Password Baru
            </label>
            <input
              v-model="passwordForm.confirmPassword"
              type="password"
              required
              class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary"
            />
          </div>

          <div
            v-if="passwordError"
            class="p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-800"
          >
            {{ passwordError }}
          </div>

          <div class="pt-4">
            <button
              type="submit"
              class="px-6 py-2 bg-primary text-white rounded-lg hover:bg-opacity-90"
            >
              Ubah Password
            </button>
          </div>
        </form>
      </div>

      <!-- System Settings (Admin Only) -->
      <div v-if="isAdmin" class="bg-white rounded-2xl p-6 shadow-sm">
        <h3 class="text-lg font-semibold text-gray-900 mb-4">Pengaturan Sistem</h3>

        <div class="space-y-4 max-w-2xl">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-2">
              API Base URL
            </label>
            <input
              v-model="systemSettings.apiUrl"
              type="url"
              class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary"
              placeholder="http://localhost:8000"
            />
          </div>

          <div>
            <label class="block text-sm font-medium text-gray-700 mb-2">
              Data Refresh Interval (detik)
            </label>
            <input
              v-model.number="systemSettings.refreshInterval"
              type="number"
              min="5"
              max="300"
              class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary"
            />
          </div>

          <div class="flex items-center gap-3">
            <input
              v-model="systemSettings.autoRefresh"
              type="checkbox"
              id="auto_refresh"
              class="w-4 h-4 text-primary border-gray-300 rounded focus:ring-primary"
            />
            <label for="auto_refresh" class="text-sm font-medium text-gray-700">
              Enable Auto Refresh
            </label>
          </div>

          <div class="pt-4">
            <button
              @click="updateSystemSettings"
              class="px-6 py-2 bg-primary text-white rounded-lg hover:bg-opacity-90"
            >
              Simpan Pengaturan
            </button>
          </div>
        </div>
      </div>

      <!-- About -->
      <div class="bg-white rounded-2xl p-6 shadow-sm">
        <h3 class="text-lg font-semibold text-gray-900 mb-4">Tentang Sistem</h3>

        <div class="space-y-2 text-sm text-gray-600">
          <div class="flex justify-between">
            <span>Nama Aplikasi:</span>
            <span class="font-medium text-gray-900">SPARING</span>
          </div>
          <div class="flex justify-between">
            <span>Versi:</span>
            <span class="font-medium text-gray-900">1.0.0</span>
          </div>
          <div class="flex justify-between">
            <span>Build:</span>
            <span class="font-medium text-gray-900">2025.01.01</span>
          </div>
          <div class="flex justify-between">
            <span>API Version:</span>
            <span class="font-medium text-gray-900">v1</span>
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

// Composables
const { user, isAdmin } = useAuth();

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
const updateProfile = () => {
  // TODO: Implement update profile API call
  console.log('Update profile:', profileForm.value);
  alert('Profil berhasil diperbarui');
};

// Change password
const changePassword = () => {
  passwordError.value = null;

  if (passwordForm.value.newPassword !== passwordForm.value.confirmPassword) {
    passwordError.value = 'Password baru dan konfirmasi password tidak cocok';
    return;
  }

  if (passwordForm.value.newPassword.length < 8) {
    passwordError.value = 'Password minimal 8 karakter';
    return;
  }

  // TODO: Implement change password API call
  console.log('Change password');
  alert('Password berhasil diubah');

  // Reset form
  passwordForm.value = {
    currentPassword: '',
    newPassword: '',
    confirmPassword: '',
  };
};

// Update system settings
const updateSystemSettings = () => {
  // TODO: Implement update system settings
  console.log('Update system settings:', systemSettings.value);
  alert('Pengaturan sistem berhasil diperbarui');
};
</script>
