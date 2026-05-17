<template>
  <div class="min-h-screen bg-slate-50 flex items-center justify-center p-6">
    <div class="text-center max-w-sm">

      <!-- Illustration -->
      <div class="relative mx-auto w-40 h-40 mb-8">
        <!-- Background circle -->
        <div class="absolute inset-0 rounded-full bg-primary/5"></div>
        <!-- Number -->
        <div class="absolute inset-0 flex items-center justify-center">
          <span class="text-7xl font-black text-primary/10 select-none leading-none">404</span>
        </div>
        <!-- Icon -->
        <div class="absolute inset-0 flex items-center justify-center">
          <div class="w-16 h-16 rounded-2xl bg-white shadow-md border border-slate-100 flex items-center justify-center">
            <i class="fas fa-map-marked-alt text-2xl text-primary/60"></i>
          </div>
        </div>
      </div>

      <h1 class="text-2xl font-bold text-slate-800 mb-2">Halaman Tidak Ditemukan</h1>
      <p class="text-sm text-slate-400 leading-relaxed mb-8">
        Halaman yang Anda cari tidak ada atau sudah dipindahkan.<br>
        Kembali ke dashboard untuk melanjutkan.
      </p>

      <div class="flex gap-3 justify-center">
        <button
          @click="$router.back()"
          class="px-5 py-2.5 text-sm font-medium text-slate-600 bg-white border border-slate-200 rounded-xl hover:bg-slate-50 transition-colors"
        >
          <i class="fas fa-arrow-left mr-2 text-xs"></i>Kembali
        </button>
        <router-link
          to="/dashboard"
          class="px-5 py-2.5 text-sm font-semibold text-white bg-primary rounded-xl hover:bg-opacity-90 transition-colors shadow-sm shadow-primary/20"
        >
          <i class="fas fa-th-large mr-2 text-xs"></i>Dashboard
        </router-link>
      </div>

      <p class="mt-10 text-xs text-slate-300">SPARING Monitoring System</p>
    </div>
  </div>
</template>

<script setup>
// No logic needed
</script>
