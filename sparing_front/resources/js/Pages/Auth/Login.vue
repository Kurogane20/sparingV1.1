<template>
  <div class="min-h-screen grid md:grid-cols-[minmax(340px,460px)_1fr] bg-white">

    <!-- ══════════════════════════════════════
         Left Panel — Login Form
         ══════════════════════════════════════ -->
    <div class="flex flex-col justify-center px-6 sm:px-10 py-10 bg-white">
      <div class="w-full max-w-sm mx-auto">

        <!-- Logo -->
        <div class="flex items-center gap-3 mb-10">
          <div class="w-10 h-10 rounded-lg bg-primary flex items-center justify-center shrink-0">
            <i class="fas fa-water text-white text-sm"></i>
          </div>
          <div>
            <div class="font-bold text-ink text-base leading-tight">SPARING Web Monitoring</div>
            <div class="text-[#617377] text-[11px] tracking-wide">Mitra Mutiara</div>
          </div>
        </div>

        <h1 class="text-xl font-bold text-ink mb-1">Masuk ke akun Anda</h1>
        <p class="text-[12.5px] text-[#617377] mb-6">Gunakan email dan password yang diberikan administrator.</p>

        <!-- Error -->
        <div
          v-if="errorMessage"
          class="mb-4 flex items-start gap-2.5 px-3.5 py-2.5 bg-[#FBEAEA] border border-[#F0C6C6] rounded-md"
        >
          <i class="fas fa-exclamation-circle text-danger mt-0.5 text-xs shrink-0"></i>
          <p class="text-[12.5px] text-danger flex-1">{{ errorMessage }}</p>
          <button type="button" @click="errorMessage = null" class="text-danger/60 hover:text-danger shrink-0">
            <i class="fas fa-times text-xs"></i>
          </button>
        </div>

        <!-- Form -->
        <form @submit.prevent="handleLogin" class="space-y-4">
          <div>
            <label for="email" class="block text-[11.5px] font-semibold text-ink mb-1.5 uppercase tracking-wide">Email</label>
            <div class="relative">
              <span class="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                <i class="fas fa-envelope text-[#8FA0A3] text-sm"></i>
              </span>
              <input
                id="email"
                v-model="form.email"
                type="email"
                required
                class="w-full border border-[#C4D1D3] rounded-md py-2.5 pl-9 pr-3 text-sm text-ink focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary"
                placeholder="user@example.com"
              />
            </div>
          </div>

          <div>
            <label for="password" class="block text-[11.5px] font-semibold text-ink mb-1.5 uppercase tracking-wide">Password</label>
            <div class="relative">
              <span class="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                <i class="fas fa-lock text-[#8FA0A3] text-sm"></i>
              </span>
              <input
                id="password"
                v-model="form.password"
                :type="showPassword ? 'text' : 'password'"
                required
                class="w-full border border-[#C4D1D3] rounded-md py-2.5 pl-9 pr-9 text-sm text-ink focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary"
                placeholder="••••••••"
              />
              <button
                type="button"
                @click="showPassword = !showPassword"
                class="absolute inset-y-0 right-0 pr-3 flex items-center text-[#8FA0A3] hover:text-ink transition-colors"
                :aria-label="showPassword ? 'Sembunyikan password' : 'Tampilkan password'"
              >
                <i :class="showPassword ? 'fas fa-eye-slash' : 'fas fa-eye'" class="text-sm"></i>
              </button>
            </div>
          </div>

          <button
            type="submit"
            :disabled="isLoading"
            class="w-full py-2.5 rounded-md bg-primary hover:bg-primary-dark text-white text-sm font-semibold flex items-center justify-center gap-2 transition-colors disabled:opacity-60"
          >
            <i v-if="isLoading" class="fas fa-spinner fa-spin text-sm"></i>
            <span>{{ isLoading ? 'Memproses...' : 'Masuk' }}</span>
            <i v-if="!isLoading" class="fas fa-arrow-right text-sm"></i>
          </button>
        </form>

        <!-- Note box -->
        <div class="mt-5 flex items-start gap-2.5 px-3.5 py-3 bg-[#EEF2F3] border border-[#D7E0E1] rounded-md">
          <i class="fas fa-circle-info text-[#617377] mt-0.5 text-xs shrink-0"></i>
          <p class="text-[12px] text-[#617377]">
            Belum punya akun atau lupa akses? Hubungi administrator untuk akun.
          </p>
        </div>

        <!-- Footer -->
        <div class="mt-8 pt-4 border-t border-[#EEF2F3] text-[11px] text-[#8FA0A3] space-y-1">
          <p>SPARING Web v2</p>
          <p>Didukung oleh Chrome, Edge, dan Firefox versi terbaru.</p>
        </div>
      </div>
    </div>

    <!-- ══════════════════════════════════════
         Right Panel — Brand / Info
         ══════════════════════════════════════ -->
    <div class="hidden md:flex flex-col justify-between bg-[#12333B] text-[#C6D9DC] p-12 relative overflow-hidden">
      <svg class="absolute inset-0 w-full h-full opacity-[0.06] pointer-events-none" xmlns="http://www.w3.org/2000/svg">
        <defs>
          <pattern id="loginDots" x="0" y="0" width="24" height="24" patternUnits="userSpaceOnUse">
            <circle cx="2" cy="2" r="1.5" fill="white"/>
          </pattern>
        </defs>
        <rect width="100%" height="100%" fill="url(#loginDots)"/>
      </svg>

      <div class="relative z-10">
        <h2 class="text-3xl font-bold text-white leading-snug mb-4 max-w-md">
          Pemantauan air limbah yang berkelanjutan, akurat, dan siap audit.
        </h2>
        <p class="text-[#A9C4C8] text-sm leading-relaxed max-w-sm">
          SPARING mengumpulkan data sensor secara berkala dari setiap titik pemantauan, memeriksa kepatuhan
          terhadap baku mutu, dan menyiapkan laporan untuk kebutuhan pelaporan KLHK — dalam satu sistem terpadu.
        </p>
      </div>

      <div class="relative z-10 flex flex-wrap items-center gap-x-4 gap-y-2 text-[12px] text-[#8FB0B5]">
        <span>Parameter: pH, TSS, COD, NH3-N, Debit</span>
        <span class="text-[#3E5A61]">·</span>
        <span>Interval 2 menit</span>
        <span class="text-[#3E5A61]">·</span>
        <span>Terhubung dengan pelaporan KLHK</span>
      </div>
    </div>

  </div>
</template>

<script setup>
import { ref } from 'vue';
import { useAuth } from '@/Composables/useAuth';

const { login } = useAuth();

const form         = ref({ email: '', password: '' });
const showPassword = ref(false);
const isLoading    = ref(false);
const errorMessage = ref(null);

const handleLogin = async () => {
  isLoading.value    = true;
  errorMessage.value = null;
  try {
    await login(form.value);
    window.location.href = '/dashboard';
  } catch (error) {
    errorMessage.value = error.response?.data?.detail || 'Email atau password salah. Silakan coba lagi.';
  } finally {
    isLoading.value = false;
  }
};
</script>
