<template>
  <div class="min-h-screen relative overflow-hidden">
    <!-- Animated Background -->
    <div class="fixed inset-0 -z-10">
      <div class="absolute inset-0 bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900"></div>
      
      <!-- Animated gradient orbs -->
      <div class="absolute top-0 left-1/4 w-96 h-96 bg-primary/20 rounded-full blur-3xl animate-float"></div>
      <div class="absolute bottom-1/4 right-1/4 w-80 h-80 bg-secondary/20 rounded-full blur-3xl animate-float" style="animation-delay: -3s;"></div>
      <div class="absolute top-1/2 left-1/2 w-64 h-64 bg-purple-500/10 rounded-full blur-3xl animate-float" style="animation-delay: -1.5s;"></div>
      
      <!-- Grid pattern overlay -->
      <div class="absolute inset-0 bg-[url('data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNDAiIGhlaWdodD0iNDAiIHZpZXdCb3g9IjAgMCA0MCA0MCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48ZyBmaWxsPSJub25lIiBmaWxsLXJ1bGU9ImV2ZW5vZGQiPjxwYXRoIGQ9Ik0wIDBoNDB2NDBIMHoiLz48cGF0aCBkPSJNNDAgMEgwdjQwaDQwVjB6TTEgMWgzOHYzOEgxVjF6IiBmaWxsPSJyZ2JhKDI1NSwyNTUsMjU1LDAuMDMpIi8+PC9nPjwvc3ZnPg==')] opacity-50"></div>
    </div>

    <div class="min-h-screen flex items-center justify-center p-4">
      <div class="max-w-md w-full animate-slide-up">
        <!-- Logo & Title -->
        <div class="text-center mb-8">
          <div class="inline-flex items-center justify-center w-20 h-20 bg-gradient-to-br from-primary to-emerald-400 rounded-2xl shadow-2xl shadow-primary/30 mb-6 animate-float">
            <i class="fas fa-leaf text-white text-3xl"></i>
          </div>
          <h1 class="text-4xl font-bold text-white mb-2">SPARING</h1>
          <p class="text-gray-400">
            Environmental Monitoring System
          </p>
        </div>

        <!-- Login Card -->
        <div class="glass-dark rounded-3xl p-8 shadow-2xl">
          <h2 class="text-2xl font-bold text-white mb-2">Selamat Datang</h2>
          <p class="text-gray-400 mb-6">Masuk ke dashboard monitoring Anda</p>

          <!-- Error Message -->
          <transition name="slide-fade">
            <div
              v-if="errorMessage"
              class="mb-6 p-4 bg-rose-500/20 border border-rose-500/30 rounded-xl flex items-start gap-3 backdrop-blur-sm"
            >
              <i class="fas fa-exclamation-circle text-rose-400 mt-0.5"></i>
              <div class="flex-1">
                <p class="text-sm text-rose-200">{{ errorMessage }}</p>
              </div>
              <button @click="errorMessage = null" class="text-rose-400 hover:text-rose-300 transition-colors">
                <i class="fas fa-times"></i>
              </button>
            </div>
          </transition>

          <!-- Login Form -->
          <form @submit.prevent="handleLogin" class="space-y-5">
            <!-- Email Field -->
            <div>
              <label for="email" class="block text-sm font-medium text-gray-300 mb-2">
                Email
              </label>
              <div class="relative group">
                <div class="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
                  <i class="fas fa-envelope text-gray-500 group-focus-within:text-primary transition-colors"></i>
                </div>
                <input
                  id="email"
                  v-model="form.email"
                  type="email"
                  required
                  class="w-full pl-12 pr-4 py-3.5 bg-white/5 border border-white/10 rounded-xl text-white placeholder-gray-500 focus:bg-white/10 focus:border-primary/50 focus:ring-2 focus:ring-primary/20 transition-all duration-300"
                  placeholder="user@example.com"
                />
              </div>
            </div>

            <!-- Password Field -->
            <div>
              <label for="password" class="block text-sm font-medium text-gray-300 mb-2">
                Password
              </label>
              <div class="relative group">
                <div class="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
                  <i class="fas fa-lock text-gray-500 group-focus-within:text-primary transition-colors"></i>
                </div>
                <input
                  id="password"
                  v-model="form.password"
                  :type="showPassword ? 'text' : 'password'"
                  required
                  class="w-full pl-12 pr-12 py-3.5 bg-white/5 border border-white/10 rounded-xl text-white placeholder-gray-500 focus:bg-white/10 focus:border-primary/50 focus:ring-2 focus:ring-primary/20 transition-all duration-300"
                  placeholder="••••••••"
                />
                <button
                  type="button"
                  @click="showPassword = !showPassword"
                  class="absolute inset-y-0 right-0 pr-4 flex items-center text-gray-500 hover:text-gray-300 transition-colors"
                >
                  <i :class="showPassword ? 'fas fa-eye-slash' : 'fas fa-eye'"></i>
                </button>
              </div>
            </div>

            <!-- Submit Button -->
            <button
              type="submit"
              :disabled="isLoading"
              class="w-full py-4 rounded-xl font-semibold text-white transition-all duration-300 disabled:opacity-50 disabled:cursor-not-allowed disabled:transform-none relative overflow-hidden group"
              :class="isLoading ? 'bg-gray-600' : 'bg-gradient-to-r from-primary to-emerald-400 hover:shadow-lg hover:shadow-primary/30 hover:-translate-y-0.5'"
            >
              <span class="relative z-10 flex items-center justify-center gap-2">
                <i v-if="isLoading" class="fas fa-spinner fa-spin"></i>
                <span>{{ isLoading ? 'Memproses...' : 'Masuk' }}</span>
                <i v-if="!isLoading" class="fas fa-arrow-right transition-transform group-hover:translate-x-1"></i>
              </span>
              
              <!-- Button shine effect -->
              <div class="absolute inset-0 -translate-x-full group-hover:translate-x-full transition-transform duration-700 bg-gradient-to-r from-transparent via-white/20 to-transparent"></div>
            </button>
          </form>

          <!-- Footer -->
          <div class="mt-8 text-center">
            <p class="text-sm text-gray-500">
              Hubungi administrator untuk akses sistem
            </p>
          </div>
        </div>

        <!-- Version Info -->
        <div class="mt-8 text-center text-gray-500 text-sm">
          SPARING v1.0.0 &copy; 2025
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue';
import { useRouter } from 'vue-router';
import { useAuth } from '@/Composables/useAuth';

// Router
const router = useRouter();

// State
const form = ref({
  email: '',
  password: '',
});

const showPassword = ref(false);
const isLoading = ref(false);
const errorMessage = ref(null);

// Composables
const { login } = useAuth();

// Handle login submission
const handleLogin = async () => {
  isLoading.value = true;
  errorMessage.value = null;

  try {
    await login(form.value);
    router.push('/dashboard');
  } catch (error) {
    errorMessage.value =
      error.response?.data?.detail || 'Email atau password salah. Silakan coba lagi.';
  } finally {
    isLoading.value = false;
  }
};
</script>

<style scoped>
.glass-dark {
  background: rgba(15, 23, 42, 0.8);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border: 1px solid rgba(255, 255, 255, 0.1);
}

.slide-fade-enter-active,
.slide-fade-leave-active {
  transition: all 0.3s ease;
}

.slide-fade-enter-from,
.slide-fade-leave-to {
  opacity: 0;
  transform: translateY(-10px);
}
</style>
