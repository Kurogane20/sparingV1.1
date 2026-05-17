<template>
  <div class="min-h-screen bg-slate-100 flex">

    <!-- ══════════════════════════════════════
         Left Panel — Branding + Visual Data
         ══════════════════════════════════════ -->
    <div class="hidden lg:flex lg:w-5/12 relative flex-col justify-between overflow-hidden" style="background: linear-gradient(160deg, #1e3a8a 0%, #1e2e6a 60%, #172554 100%);">

      <!-- Dot grid pattern overlay -->
      <svg class="absolute inset-0 w-full h-full opacity-10 pointer-events-none" xmlns="http://www.w3.org/2000/svg">
        <defs>
          <pattern id="dots" x="0" y="0" width="24" height="24" patternUnits="userSpaceOnUse">
            <circle cx="2" cy="2" r="1.5" fill="white"/>
          </pattern>
        </defs>
        <rect width="100%" height="100%" fill="url(#dots)"/>
      </svg>

      <!-- Glowing orb top-right -->
      <div class="absolute -top-20 -right-20 w-64 h-64 rounded-full opacity-10 pointer-events-none"
        style="background: radial-gradient(circle, #60a5fa 0%, transparent 70%);">
      </div>

      <!-- Content -->
      <div class="relative z-10 p-12">
        <!-- Logo -->
        <div class="flex items-center gap-3 mb-12">
          <div class="w-11 h-11 rounded-xl bg-white/15 flex items-center justify-center ring-1 ring-white/20">
            <i class="fas fa-water text-white text-lg"></i>
          </div>
          <div>
            <span class="text-white font-bold text-xl tracking-widest">SPARING</span>
            <div class="text-blue-300 text-[10px] tracking-widest uppercase">Monitoring System</div>
          </div>
        </div>

        <h2 class="text-3xl font-bold text-white leading-snug mb-3">
          Pantau Kualitas<br>Lingkungan Industri
        </h2>
        <p class="text-blue-200 text-sm leading-relaxed mb-10 max-w-xs">
          Real-time monitoring air limbah, emisi udara, dan parameter lingkungan — sesuai regulasi KLHK.
        </p>

        <!-- ── Animated Data Chart ── -->
        <div class="mb-10 rounded-2xl overflow-hidden" style="background: rgba(255,255,255,0.07); border: 1px solid rgba(255,255,255,0.12);">
          <div class="px-4 pt-3 pb-1 flex items-center justify-between">
            <span class="text-blue-200 text-xs font-semibold">Live Sensor Data</span>
            <div class="flex items-center gap-1.5">
              <span class="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
              <span class="text-emerald-300 text-[10px] font-medium">LIVE</span>
            </div>
          </div>

          <svg viewBox="0 0 320 120" class="w-full" xmlns="http://www.w3.org/2000/svg">
            <!-- Grid lines -->
            <line x1="0" y1="30"  x2="320" y2="30"  stroke="rgba(255,255,255,0.06)" stroke-width="1"/>
            <line x1="0" y1="60"  x2="320" y2="60"  stroke="rgba(255,255,255,0.06)" stroke-width="1"/>
            <line x1="0" y1="90"  x2="320" y2="90"  stroke="rgba(255,255,255,0.06)" stroke-width="1"/>
            <line x1="64"  y1="10" x2="64"  y2="110" stroke="rgba(255,255,255,0.04)" stroke-width="1"/>
            <line x1="128" y1="10" x2="128" y2="110" stroke="rgba(255,255,255,0.04)" stroke-width="1"/>
            <line x1="192" y1="10" x2="192" y2="110" stroke="rgba(255,255,255,0.04)" stroke-width="1"/>
            <line x1="256" y1="10" x2="256" y2="110" stroke="rgba(255,255,255,0.04)" stroke-width="1"/>

            <!-- pH line (blue) — fill area -->
            <defs>
              <linearGradient id="phGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stop-color="#60a5fa" stop-opacity="0.3"/>
                <stop offset="100%" stop-color="#60a5fa" stop-opacity="0"/>
              </linearGradient>
              <linearGradient id="tssGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stop-color="#34d399" stop-opacity="0.2"/>
                <stop offset="100%" stop-color="#34d399" stop-opacity="0"/>
              </linearGradient>
            </defs>

            <path class="chart-fill-ph"
              d="M0,70 C20,65 40,55 64,58 C88,61 108,75 128,68 C148,61 168,45 192,50 C216,55 236,62 256,55 C276,48 296,40 320,44 L320,110 L0,110 Z"
              fill="url(#phGrad)"/>
            <path class="chart-line-ph"
              d="M0,70 C20,65 40,55 64,58 C88,61 108,75 128,68 C148,61 168,45 192,50 C216,55 236,62 256,55 C276,48 296,40 320,44"
              fill="none" stroke="#60a5fa" stroke-width="2" stroke-linecap="round"/>

            <!-- TSS line (green) -->
            <path class="chart-fill-tss"
              d="M0,85 C20,82 40,90 64,80 C88,70 108,88 128,82 C148,76 168,72 192,78 C216,84 236,76 256,70 C276,64 296,72 320,65 L320,110 L0,110 Z"
              fill="url(#tssGrad)"/>
            <path class="chart-line-tss"
              d="M0,85 C20,82 40,90 64,80 C88,70 108,88 128,82 C148,76 168,72 192,78 C216,84 236,76 256,70 C276,64 296,72 320,65"
              fill="none" stroke="#34d399" stroke-width="1.5" stroke-linecap="round" stroke-dasharray="4 2"/>

            <!-- Animated data point (latest) -->
            <circle cx="320" cy="44" r="4" fill="#60a5fa" class="dot-pulse-blue"/>
            <circle cx="320" cy="65" r="3" fill="#34d399" class="dot-pulse-green"/>
          </svg>

          <!-- Legend -->
          <div class="px-4 pb-3 flex gap-4">
            <div class="flex items-center gap-1.5">
              <span class="w-3 h-0.5 bg-blue-400 rounded-full inline-block"></span>
              <span class="text-blue-300 text-[10px]">pH</span>
            </div>
            <div class="flex items-center gap-1.5">
              <span class="w-3 h-0.5 bg-emerald-400 rounded-full inline-block" style="border-bottom: 2px dashed #34d399; background: none;"></span>
              <span class="text-blue-300 text-[10px]">TSS</span>
            </div>
            <div class="ml-auto text-blue-300/60 text-[10px]">7 hari terakhir</div>
          </div>
        </div>
      </div>

      <!-- ── Feature list ── -->
      <div class="relative z-10 px-12 pb-6 space-y-3">
        <div v-for="f in features" :key="f.label" class="flex items-center gap-3">
          <div class="w-7 h-7 rounded-lg bg-white/10 flex items-center justify-center shrink-0 ring-1 ring-white/10">
            <i :class="[f.icon, 'text-white text-xs']"></i>
          </div>
          <span class="text-blue-100 text-xs">{{ f.label }}</span>
        </div>
      </div>

      <!-- ── Animated SVG Water Wave ── -->
      <div class="relative z-10 h-20 overflow-hidden">
        <svg viewBox="0 0 1440 80" preserveAspectRatio="none" class="absolute bottom-0 w-full h-full" xmlns="http://www.w3.org/2000/svg">
          <path class="wave1" d="M0,40 C180,10 360,70 540,40 C720,10 900,70 1080,40 C1260,10 1380,60 1440,40 L1440,80 L0,80 Z"
            fill="rgba(255,255,255,0.06)"/>
          <path class="wave2" d="M0,55 C200,25 400,75 600,50 C800,25 1000,75 1200,50 C1300,37 1380,52 1440,45 L1440,80 L0,80 Z"
            fill="rgba(255,255,255,0.05)"/>
        </svg>
        <div class="absolute bottom-3 left-12 text-blue-300/50 text-[10px]">SPARING v1.1 &copy; 2025</div>
      </div>
    </div>

    <!-- ══════════════════════════════════════
         Right Panel — Login Form
         ══════════════════════════════════════ -->
    <div class="flex-1 flex items-center justify-center p-6 lg:p-12 bg-slate-50">
      <div class="w-full max-w-sm animate-slide-up">

        <!-- Mobile Logo -->
        <div class="flex items-center gap-2 mb-8 lg:hidden">
          <div class="w-9 h-9 rounded-xl bg-primary flex items-center justify-center">
            <i class="fas fa-water text-white text-sm"></i>
          </div>
          <div>
            <div class="font-bold text-primary text-base tracking-widest">SPARING</div>
            <div class="text-slate-400 text-[10px] tracking-wider uppercase">Monitoring System</div>
          </div>
        </div>

        <!-- Form Card -->
        <div class="bg-white rounded-2xl shadow-xl shadow-slate-200/80 border border-slate-100 p-8">
          <div class="mb-7">
            <h1 class="text-xl font-bold text-slate-800 mb-1">Masuk ke Sistem</h1>
            <p class="text-xs text-slate-400">Gunakan akun yang diberikan administrator</p>
          </div>

          <!-- Error -->
          <Transition name="slide-fade">
            <div
              v-if="errorMessage"
              class="mb-5 flex items-start gap-3 px-4 py-3 bg-red-50 border border-red-200 rounded-xl"
            >
              <i class="fas fa-exclamation-circle text-red-500 mt-0.5 text-sm shrink-0"></i>
              <p class="text-sm text-red-700 flex-1">{{ errorMessage }}</p>
              <button @click="errorMessage = null" class="text-red-400 hover:text-red-600 transition-colors shrink-0">
                <i class="fas fa-times text-xs"></i>
              </button>
            </div>
          </Transition>

          <!-- Form -->
          <form @submit.prevent="handleLogin" class="space-y-4">
            <!-- Email -->
            <div>
              <label for="email" class="block text-xs font-semibold text-slate-600 mb-1.5 uppercase tracking-wide">Email</label>
              <div class="relative">
                <span class="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none">
                  <i class="fas fa-envelope text-slate-400 text-sm"></i>
                </span>
                <input
                  id="email"
                  v-model="form.email"
                  type="email"
                  required
                  class="form-input pl-10"
                  placeholder="user@example.com"
                />
              </div>
            </div>

            <!-- Password -->
            <div>
              <label for="password" class="block text-xs font-semibold text-slate-600 mb-1.5 uppercase tracking-wide">Password</label>
              <div class="relative">
                <span class="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none">
                  <i class="fas fa-lock text-slate-400 text-sm"></i>
                </span>
                <input
                  id="password"
                  v-model="form.password"
                  :type="showPassword ? 'text' : 'password'"
                  required
                  class="form-input pl-10 pr-10"
                  placeholder="••••••••"
                />
                <button
                  type="button"
                  @click="showPassword = !showPassword"
                  class="absolute inset-y-0 right-0 pr-3.5 flex items-center text-slate-400 hover:text-slate-600 transition-colors"
                >
                  <i :class="showPassword ? 'fas fa-eye-slash' : 'fas fa-eye'" class="text-sm"></i>
                </button>
              </div>
            </div>

            <!-- Submit -->
            <button
              type="submit"
              :disabled="isLoading"
              class="btn-primary w-full py-3 flex items-center justify-center gap-2 mt-2 rounded-xl shadow-md shadow-primary/20"
            >
              <i v-if="isLoading" class="fas fa-spinner fa-spin text-sm"></i>
              <span>{{ isLoading ? 'Memproses...' : 'Masuk' }}</span>
              <i v-if="!isLoading" class="fas fa-arrow-right text-sm"></i>
            </button>
          </form>
        </div>

        <p class="mt-5 text-center text-xs text-slate-400">
          Lupa akses? Hubungi <span class="text-primary font-medium">administrator sistem</span>.
        </p>
      </div>
    </div>

  </div>
</template>

<script setup>
import { ref } from 'vue';
import { useRouter } from 'vue-router';
import { useAuth } from '@/Composables/useAuth';

const router = useRouter();
const { login } = useAuth();

const form         = ref({ email: '', password: '' });
const showPassword = ref(false);
const isLoading    = ref(false);
const errorMessage = ref(null);

const features = [
  { icon: 'fas fa-tint',        label: 'Monitoring kualitas air real-time' },
  { icon: 'fas fa-chart-line',  label: 'Analisis tren & laporan otomatis' },
  { icon: 'fas fa-bell',        label: 'Notifikasi peringatan baku mutu' },
  { icon: 'fas fa-shield-alt',  label: 'Keamanan data terenkripsi' },
];

const handleLogin = async () => {
  isLoading.value    = true;
  errorMessage.value = null;
  try {
    await login(form.value);
    router.push('/dashboard');
  } catch (error) {
    errorMessage.value = error.response?.data?.detail || 'Email atau password salah. Silakan coba lagi.';
  } finally {
    isLoading.value = false;
  }
};
</script>

<style scoped>
/* Form transition */
.slide-fade-enter-active,
.slide-fade-leave-active { transition: all 0.25s ease; }
.slide-fade-enter-from,
.slide-fade-leave-to     { opacity: 0; transform: translateY(-8px); }

/* Chart line draw-in animation */
.chart-line-ph {
  stroke-dasharray: 700;
  stroke-dashoffset: 700;
  animation: drawLine 2s ease-out 0.3s forwards;
}
.chart-line-tss {
  stroke-dasharray: 700;
  stroke-dashoffset: 700;
  animation: drawLine 2.2s ease-out 0.6s forwards;
}
.chart-fill-ph {
  opacity: 0;
  animation: fadeInArea 1s ease-out 2s forwards;
}
.chart-fill-tss {
  opacity: 0;
  animation: fadeInArea 1s ease-out 2.2s forwards;
}
@keyframes drawLine {
  to { stroke-dashoffset: 0; }
}
@keyframes fadeInArea {
  to { opacity: 1; }
}

/* Live data dot pulse */
.dot-pulse-blue {
  transform-origin: 320px 44px;
  animation: pulseDot 2s ease-in-out infinite;
}
.dot-pulse-green {
  transform-origin: 320px 65px;
  animation: pulseDot 2s ease-in-out 0.5s infinite;
}
@keyframes pulseDot {
  0%, 100% { r: 4; opacity: 1; }
  50%       { r: 6; opacity: 0.6; }
}

/* Wave animation */
.wave1 {
  animation: waveMove 6s ease-in-out infinite alternate;
}
.wave2 {
  animation: waveMove 8s ease-in-out 1s infinite alternate-reverse;
}
@keyframes waveMove {
  0%   { transform: translateX(0); }
  100% { transform: translateX(-40px); }
}
</style>
