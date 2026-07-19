<template>
  <AppLayout>
    <PageHeader :crumb="['Beranda', 'Administrasi', 'Pengaturan']" title="Pengaturan" subtitle="Kelola konfigurasi akun dan sistem" />

    <div class="space-y-6">
      <!-- User Profile Settings -->
      <div class="bg-white border border-[#D7E0E1] rounded-lg p-5 md:p-6">
        <div class="flex items-center gap-3 mb-5">
          <div class="w-8 h-8 rounded-lg bg-primary-soft flex items-center justify-center shrink-0">
            <i class="fas fa-user text-primary-dark text-xs"></i>
          </div>
          <h3 class="text-sm font-bold text-ink">Profil Pengguna</h3>
        </div>

        <div class="divide-y divide-[#EEF2F3]">
          <div class="setrow">
            <div class="setrow-label">
              <p class="text-sm font-semibold text-ink">Email</p>
              <p class="text-[12px] text-[#617377]">Alamat email akun, tidak dapat diubah</p>
            </div>
            <div class="setrow-control">
              <input :value="user?.email" type="email" disabled
                class="w-full border border-[#D7E0E1] rounded-md p-2 text-sm bg-[#EEF2F3] text-[#8FA0A3] cursor-not-allowed" />
            </div>
          </div>
          <div class="setrow">
            <div class="setrow-label">
              <p class="text-sm font-semibold text-ink">Nama Lengkap</p>
              <p class="text-[12px] text-[#617377]">Ditampilkan pada catatan tindak lanjut & laporan</p>
            </div>
            <div class="setrow-control">
              <input v-model="profileForm.name" type="text" placeholder="Nama Lengkap" class="w-full border border-[#C4D1D3] rounded-md p-2 text-sm" />
            </div>
          </div>
          <div class="setrow">
            <div class="setrow-label">
              <p class="text-sm font-semibold text-ink">Role</p>
              <p class="text-[12px] text-[#617377]">Peran akses ditentukan oleh administrator</p>
            </div>
            <div class="setrow-control">
              <input :value="user?.role || 'viewer'" type="text" disabled
                class="w-full border border-[#D7E0E1] rounded-md p-2 text-sm bg-[#EEF2F3] text-[#8FA0A3] cursor-not-allowed capitalize" />
            </div>
          </div>
        </div>
        <div class="pt-4">
          <button @click="updateProfile" class="px-3 py-2 rounded-md bg-primary hover:bg-primary-dark text-white text-sm transition-colors">
            <i class="fas fa-save mr-1.5"></i>Simpan Perubahan
          </button>
        </div>
      </div>

      <!-- Change Password -->
      <div class="bg-white border border-[#D7E0E1] rounded-lg p-5 md:p-6">
        <div class="flex items-center gap-3 mb-5">
          <div class="w-8 h-8 rounded-lg bg-[#F7EFD9] flex items-center justify-center shrink-0">
            <i class="fas fa-lock text-warning text-xs"></i>
          </div>
          <h3 class="text-sm font-bold text-ink">Ubah Password</h3>
        </div>

        <form @submit.prevent="changePassword" class="space-y-4 max-w-lg">
          <div>
            <label class="block text-[11.5px] font-semibold text-ink mb-1.5 uppercase tracking-wide">Password Saat Ini</label>
            <input v-model="passwordForm.currentPassword" type="password" required class="w-full border border-[#C4D1D3] rounded-md p-2 text-sm" />
          </div>
          <div>
            <label class="block text-[11.5px] font-semibold text-ink mb-1.5 uppercase tracking-wide">Password Baru</label>
            <input v-model="passwordForm.newPassword" type="password" required minlength="8" class="w-full border border-[#C4D1D3] rounded-md p-2 text-sm" />
          </div>
          <div>
            <label class="block text-[11.5px] font-semibold text-ink mb-1.5 uppercase tracking-wide">Konfirmasi Password Baru</label>
            <input v-model="passwordForm.confirmPassword" type="password" required class="w-full border border-[#C4D1D3] rounded-md p-2 text-sm" />
          </div>
          <div v-if="passwordError" class="p-3 bg-[#FBEAEA] border border-[#F0C6C6] rounded-md text-xs text-danger flex items-center gap-2">
            <i class="fas fa-exclamation-circle shrink-0"></i>{{ passwordError }}
          </div>
          <div class="pt-2">
            <button type="submit" class="px-3 py-2 rounded-md bg-primary hover:bg-primary-dark text-white text-sm transition-colors">
              <i class="fas fa-key mr-1.5"></i>Ubah Password
            </button>
          </div>
        </form>
      </div>

      <!-- Ambang peringatan dini -->
      <div class="bg-white border border-[#D7E0E1] rounded-lg p-5 md:p-6">
        <div class="flex items-center gap-3 mb-5">
          <div class="w-8 h-8 rounded-lg bg-primary-soft flex items-center justify-center shrink-0">
            <i class="fas fa-bell text-primary-dark text-xs"></i>
          </div>
          <div>
            <h3 class="text-sm font-bold text-ink">Ambang Peringatan Dini</h3>
            <p class="text-[12px] text-[#617377]">Batas waspada & bahaya per parameter untuk setiap lokasi</p>
          </div>
        </div>

        <div class="mb-4 max-w-xs">
          <label class="block text-[11.5px] font-semibold text-ink mb-1.5 uppercase tracking-wide">Lokasi</label>
          <select v-model="thresholdSiteUid" @change="loadRules" class="w-full border border-[#C4D1D3] rounded-md p-2 text-sm">
            <option value="">Pilih lokasi</option>
            <option v-for="s in sites" :key="s.uid" :value="s.uid">{{ s.name }}</option>
          </select>
        </div>

        <div v-if="loadingRules" class="text-center py-6 text-sm text-[#617377]">
          <i class="fas fa-spinner fa-spin mr-2"></i>Memuat ambang...
        </div>

        <div v-else-if="thresholdSiteUid && !alertRules.length" class="text-center py-6 text-sm text-[#617377]">
          Belum ada ambang yang diatur untuk lokasi ini.
        </div>

        <div v-else-if="alertRules.length" class="border border-[#D7E0E1] rounded-lg overflow-hidden">
          <table class="w-full text-sm">
            <thead>
              <tr class="bg-[#EEF2F3] text-left text-[11.5px] text-[#617377] uppercase tracking-wide">
                <th class="px-4 py-2.5 font-semibold">Parameter</th>
                <th class="px-4 py-2.5 font-semibold text-right">Waspada (Maks)</th>
                <th class="px-4 py-2.5 font-semibold text-right">Bahaya (Maks)</th>
                <th class="px-4 py-2.5 font-semibold text-right">Aksi</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-[#EEF2F3]">
              <template v-for="rule in alertRules" :key="rule.id">
                <tr class="hover:bg-[#F7FAFA] transition-colors">
                  <td class="px-4 py-2.5 text-ink font-semibold">{{ PARAM_LABELS[rule.field] || rule.field }}</td>
                  <td class="px-4 py-2.5 text-right font-mono text-warning">{{ rule.warning_max ?? '—' }}</td>
                  <td class="px-4 py-2.5 text-right font-mono text-danger">{{ rule.danger_max ?? '—' }}</td>
                  <td class="px-4 py-2.5 text-right">
                    <button
                      type="button"
                      class="px-2.5 py-1 rounded-md border border-[#C4D1D3] text-[11.5px] text-ink hover:bg-[#EEF2F3] transition-colors"
                      @click="toggleEdit(rule)"
                    >
                      {{ editingRuleId === rule.id ? 'Batal' : 'Ubah' }}
                    </button>
                  </td>
                </tr>
                <tr v-if="editingRuleId === rule.id" class="bg-[#EEF2F3]">
                  <td colspan="4" class="px-4 py-3">
                    <div class="flex flex-wrap items-end gap-3">
                      <div>
                        <label class="block text-[11px] font-semibold text-ink mb-1">Waspada (Maks)</label>
                        <input v-model.number="editForm.warning_max" type="number" step="0.01" class="w-32 border border-[#C4D1D3] rounded-md p-1.5 text-sm font-mono" />
                      </div>
                      <div>
                        <label class="block text-[11px] font-semibold text-ink mb-1">Bahaya (Maks)</label>
                        <input v-model.number="editForm.danger_max" type="number" step="0.01" class="w-32 border border-[#C4D1D3] rounded-md p-1.5 text-sm font-mono" />
                      </div>
                      <button
                        type="button"
                        :disabled="savingRule"
                        class="px-3 py-1.5 rounded-md bg-primary hover:bg-primary-dark text-white text-[12.5px] disabled:opacity-50 flex items-center gap-1.5 transition-colors"
                        @click="saveRule(rule)"
                      >
                        <i :class="savingRule ? 'fas fa-spinner fa-spin' : 'fas fa-save'" class="text-xs"></i>
                        Simpan
                      </button>
                    </div>
                  </td>
                </tr>
              </template>
            </tbody>
          </table>
        </div>
      </div>

      <!-- Kanal notifikasi -->
      <div class="bg-white border border-[#D7E0E1] rounded-lg p-5 md:p-6">
        <div class="flex items-center gap-3 mb-5">
          <div class="w-8 h-8 rounded-lg bg-primary-soft flex items-center justify-center shrink-0">
            <i class="fas fa-paper-plane text-primary-dark text-xs"></i>
          </div>
          <div>
            <h3 class="text-sm font-bold text-ink">Kanal Notifikasi</h3>
            <p class="text-[12px] text-[#617377]">Saluran pengiriman peringatan alarm</p>
          </div>
        </div>

        <div class="divide-y divide-[#EEF2F3]">
          <div class="flex items-center justify-between py-3">
            <div class="flex items-center gap-3">
              <i class="fas fa-envelope text-[#617377] w-5 text-center"></i>
              <span class="text-sm text-ink">Email</span>
            </div>
            <span class="text-[10px] font-bold px-2 py-0.5 rounded bg-primary-soft text-primary-dark uppercase tracking-wide">Aktif</span>
          </div>
          <div class="flex items-center justify-between py-3 opacity-60">
            <div class="flex items-center gap-3">
              <i class="fab fa-whatsapp text-[#617377] w-5 text-center"></i>
              <span class="text-sm text-ink">WhatsApp</span>
            </div>
            <span class="text-[10px] font-bold px-2 py-0.5 rounded bg-[#EAEEEF] text-[#6E7E82] uppercase tracking-wide">Segera</span>
          </div>
          <div class="flex items-center justify-between py-3 opacity-60">
            <div class="flex items-center gap-3">
              <i class="fab fa-telegram text-[#617377] w-5 text-center"></i>
              <span class="text-sm text-ink">Telegram</span>
            </div>
            <span class="text-[10px] font-bold px-2 py-0.5 rounded bg-[#EAEEEF] text-[#6E7E82] uppercase tracking-wide">Segera</span>
          </div>
          <div class="flex items-center justify-between py-3 opacity-60">
            <div class="flex items-center gap-3">
              <i class="fas fa-sms text-[#617377] w-5 text-center"></i>
              <span class="text-sm text-ink">SMS</span>
            </div>
            <span class="text-[10px] font-bold px-2 py-0.5 rounded bg-[#EAEEEF] text-[#6E7E82] uppercase tracking-wide">Segera</span>
          </div>
        </div>
        <p class="text-[11.5px] text-[#617377] mt-4">
          Kanal WhatsApp, Telegram, dan SMS belum terhubung ke backend — dalam backlog pengembangan.
        </p>
      </div>

      <!-- System Settings (Admin Only) -->
      <div v-if="isAdmin" class="bg-white border border-[#D7E0E1] rounded-lg p-5 md:p-6">
        <div class="flex items-center gap-3 mb-5">
          <div class="w-8 h-8 rounded-lg bg-primary-soft flex items-center justify-center shrink-0">
            <i class="fas fa-server text-primary-dark text-xs"></i>
          </div>
          <h3 class="text-sm font-bold text-ink">Pengaturan Sistem</h3>
        </div>

        <div class="space-y-4 max-w-lg">
          <div>
            <label class="block text-[11.5px] font-semibold text-ink mb-1.5 uppercase tracking-wide">API Base URL</label>
            <input v-model="systemSettings.apiUrl" type="url" placeholder="http://localhost:8000" class="w-full border border-[#C4D1D3] rounded-md p-2 text-sm font-mono" />
          </div>
          <div>
            <label class="block text-[11.5px] font-semibold text-ink mb-1.5 uppercase tracking-wide">Interval Refresh Data (detik)</label>
            <input v-model.number="systemSettings.refreshInterval" type="number" min="5" max="300" class="w-full border border-[#C4D1D3] rounded-md p-2 text-sm font-mono" />
          </div>
          <div class="flex items-center gap-3 py-1">
            <input v-model="systemSettings.autoRefresh" type="checkbox" id="auto_refresh"
              class="w-4 h-4 text-primary border-[#C4D1D3] rounded focus:ring-primary" />
            <label for="auto_refresh" class="text-sm text-ink">Auto Refresh Aktif</label>
          </div>
          <div class="pt-2">
            <button @click="updateSystemSettings" class="px-3 py-2 rounded-md bg-primary hover:bg-primary-dark text-white text-sm transition-colors">
              <i class="fas fa-save mr-1.5"></i>Simpan Pengaturan
            </button>
          </div>
        </div>
      </div>

      <!-- About -->
      <div class="bg-white border border-[#D7E0E1] rounded-lg p-5 md:p-6">
        <div class="flex items-center gap-3 mb-4">
          <div class="w-8 h-8 rounded-lg bg-[#EEF2F3] flex items-center justify-center shrink-0">
            <i class="fas fa-info-circle text-[#617377] text-xs"></i>
          </div>
          <h3 class="text-sm font-bold text-ink">Tentang Sistem</h3>
        </div>
        <div class="divide-y divide-[#EEF2F3] max-w-lg">
          <div class="flex justify-between items-center py-2.5">
            <span class="text-xs text-[#617377]">Nama Aplikasi</span>
            <span class="text-xs font-bold text-ink font-mono">SPARING</span>
          </div>
          <div class="flex justify-between items-center py-2.5">
            <span class="text-xs text-[#617377]">Versi</span>
            <span class="text-xs font-bold text-ink font-mono">2.0.0</span>
          </div>
          <div class="flex justify-between items-center py-2.5">
            <span class="text-xs text-[#617377]">Build</span>
            <span class="text-xs font-bold text-ink font-mono">2026.07.20</span>
          </div>
          <div class="flex justify-between items-center py-2.5">
            <span class="text-xs text-[#617377]">API Version</span>
            <span class="text-xs font-bold text-ink font-mono">v1</span>
          </div>
        </div>
      </div>
    </div>
  </AppLayout>
</template>

<script setup>
import { ref } from 'vue';
import AppLayout from '@/Layouts/AppLayout.vue';
import PageHeader from '@/Components/PageHeader.vue';
import { useAuth } from '@/Composables/useAuth';
import { useApi } from '@/Composables/useApi';
import { useToast } from '@/Composables/useToast';
import logger from '@/Utils/logger';

// Composables
const { user, isAdmin } = useAuth();
const { updateProfile: apiUpdateProfile, changePassword: apiChangePassword, getSites, getAlertRules, updateAlertRule } = useApi();
const toast = useToast();

const PARAM_LABELS = { ph: 'pH', tss: 'TSS', cod: 'COD', nh3n: 'NH3-N', debit: 'Debit', temp: 'Temperatur' };

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

// Ambang peringatan dini
const sites = ref([]);
const thresholdSiteUid = ref('');
const alertRules = ref([]);
const loadingRules = ref(false);
const editingRuleId = ref(null);
const editForm = ref({ warning_max: null, danger_max: null });
const savingRule = ref(false);

const loadSites = async () => {
  try {
    const res = await getSites({ per_page: 100 });
    sites.value = Array.isArray(res) ? res : (res?.items || res?.data || []);
  } catch (err) {
    logger.error('Failed to load sites:', err);
    sites.value = [];
  }
};

const loadRules = async () => {
  editingRuleId.value = null;
  if (!thresholdSiteUid.value) {
    alertRules.value = [];
    return;
  }
  loadingRules.value = true;
  try {
    const res = await getAlertRules(thresholdSiteUid.value);
    alertRules.value = Array.isArray(res) ? res : (res?.items || res?.data || []);
  } catch (err) {
    logger.error('Failed to load alert rules:', err);
    alertRules.value = [];
    toast.error('Gagal memuat ambang peringatan');
  } finally {
    loadingRules.value = false;
  }
};

const toggleEdit = (rule) => {
  if (editingRuleId.value === rule.id) {
    editingRuleId.value = null;
    return;
  }
  editingRuleId.value = rule.id;
  editForm.value = { warning_max: rule.warning_max, danger_max: rule.danger_max };
};

const saveRule = async (rule) => {
  savingRule.value = true;
  try {
    await updateAlertRule(rule.id, {
      warning_max: editForm.value.warning_max,
      danger_max: editForm.value.danger_max,
    });
    rule.warning_max = editForm.value.warning_max;
    rule.danger_max = editForm.value.danger_max;
    editingRuleId.value = null;
    toast.success('Ambang peringatan diperbarui');
  } catch (err) {
    logger.error('Failed to update alert rule:', err);
    toast.error(err.response?.data?.detail || 'Gagal memperbarui ambang peringatan');
  } finally {
    savingRule.value = false;
  }
};

loadSites();

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

<style scoped>
.setrow {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  padding: 0.875rem 0;
}
@media (min-width: 640px) {
  .setrow {
    flex-direction: row;
    align-items: center;
    justify-content: space-between;
    gap: 1.5rem;
  }
  .setrow-label {
    flex: 1;
  }
  .setrow-control {
    flex: 1;
    max-width: 20rem;
  }
}
</style>
