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
    <aside
      class="login-hero hidden md:flex min-h-screen flex-col overflow-hidden px-8 py-8 text-[#C6D9DC] lg:px-10 lg:py-9 xl:px-12 xl:py-11 2xl:px-16"
      aria-labelledby="login-hero-title"
    >
      <svg
        class="absolute inset-0 h-full w-full opacity-[0.055] pointer-events-none"
        aria-hidden="true"
        focusable="false"
        xmlns="http://www.w3.org/2000/svg"
      >
        <defs>
          <pattern id="loginDots" x="0" y="0" width="24" height="24" patternUnits="userSpaceOnUse">
            <circle cx="2" cy="2" r="1.5" fill="white"/>
          </pattern>
        </defs>
        <rect width="100%" height="100%" fill="url(#loginDots)"/>
      </svg>

      <div class="relative z-10 flex min-h-0 flex-1 flex-col">
        <header class="shrink-0 max-w-xl">
          <h2 id="login-hero-title" class="max-w-xl text-[28px] font-bold leading-[1.22] text-white lg:text-3xl 2xl:text-[36px]">
            Pemantauan air limbah yang berkelanjutan, akurat, dan siap audit.
          </h2>
          <p class="mt-4 max-w-lg text-sm leading-relaxed text-[#A9C4C8]">
            SPARING mengumpulkan data sensor secara berkala dari setiap titik pemantauan, memeriksa kepatuhan
            terhadap baku mutu, dan menyiapkan laporan untuk kebutuhan pelaporan KLHK — dalam satu sistem terpadu.
          </p>
        </header>

        <div class="login-hero__visual flex min-h-[190px] flex-1 items-center py-3 lg:min-h-[210px] lg:py-4 xl:min-h-[240px]">
          <LoginMonitoringGraphic />
        </div>

        <dl class="grid shrink-0 grid-cols-1 gap-3 border-t border-white/10 pt-4 lg:grid-cols-3 lg:gap-0 lg:pt-5">
          <div class="login-fact">
            <dt class="flex items-center gap-2 text-[11px] font-semibold uppercase tracking-[0.12em] text-[#B6CED1]">
              <span class="login-fact__icon"><i class="fas fa-sliders" aria-hidden="true"></i></span>
              5 Parameter
            </dt>
            <dd class="mt-1 pl-8 text-[11px] leading-relaxed text-[#82A7AC] xl:text-[12px]">
              pH · TSS · COD · NH3-N · Debit
            </dd>
          </div>

          <div class="login-fact">
            <dt class="flex items-center gap-2 text-[11px] font-semibold uppercase tracking-[0.12em] text-[#B6CED1]">
              <span class="login-fact__icon"><i class="fas fa-clock" aria-hidden="true"></i></span>
              Monitoring
            </dt>
            <dd class="mt-1 pl-8 text-[11px] leading-relaxed text-[#82A7AC] xl:text-[12px]">Setiap 2 menit</dd>
          </div>

          <div class="login-fact">
            <dt class="flex items-center gap-2 text-[11px] font-semibold uppercase tracking-[0.12em] text-[#B6CED1]">
              <span class="login-fact__icon"><i class="fas fa-arrow-right-arrow-left" aria-hidden="true"></i></span>
              Integrasi
            </dt>
            <dd class="mt-1 pl-8 text-[11px] leading-relaxed text-[#82A7AC] xl:text-[12px]">Pelaporan KLHK</dd>
          </div>
        </dl>
      </div>
    </aside>

  </div>
</template>

<script setup>
import { ref } from 'vue';
import LoginMonitoringGraphic from '@/Components/LoginMonitoringGraphic.vue';
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

<style scoped>
.login-hero {
  position: relative;
  background:
    radial-gradient(circle at 82% 48%, rgba(21, 154, 165, 0.14) 0, rgba(21, 154, 165, 0) 38%),
    linear-gradient(145deg, #12333b 0%, #102f38 58%, #163e47 100%);
}

.login-fact__icon {
  display: grid;
  width: 1.5rem;
  height: 1.5rem;
  flex: none;
  place-items: center;
  color: rgba(174, 221, 225, 0.78);
  background: rgba(117, 193, 200, 0.09);
  border: 1px solid rgba(154, 214, 219, 0.13);
  border-radius: 50%;
  font-size: 0.58rem;
}

@media (min-width: 1024px) {
  .login-fact + .login-fact {
    margin-left: 1.25rem;
    padding-left: 1.25rem;
    border-left: 1px solid rgba(255, 255, 255, 0.09);
  }
}

@media (min-width: 768px) and (max-height: 720px) {
  .login-hero {
    padding-top: 1.75rem;
    padding-bottom: 1.75rem;
  }

  .login-hero__visual {
    min-height: 170px;
    padding-top: 0;
    padding-bottom: 0;
  }
}
</style>
