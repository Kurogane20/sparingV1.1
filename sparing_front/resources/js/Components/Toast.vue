<template>
  <Teleport to="body">
    <!-- Toast container -->
    <div class="fixed top-4 right-4 z-[9999] flex flex-col gap-2 pointer-events-none">
      <TransitionGroup name="toast">
        <div
          v-for="t in toasts"
          :key="t.id"
          class="pointer-events-auto flex items-start gap-3 px-4 py-3 rounded-xl shadow-lg text-sm font-medium max-w-sm"
          :class="styles[t.type]"
        >
          <i class="mt-0.5 text-base" :class="icons[t.type]"></i>
          <span class="flex-1">{{ t.message }}</span>
        </div>
      </TransitionGroup>
    </div>

    <!-- Confirm modal -->
    <Transition name="fade">
      <div
        v-if="confirmState.visible"
        class="fixed inset-0 bg-black/50 flex items-center justify-center z-[9998]"
      >
        <div class="bg-white rounded-2xl shadow-xl p-6 max-w-sm w-full mx-4">
          <div class="flex items-center gap-3 mb-4">
            <div class="w-10 h-10 rounded-full bg-red-100 flex items-center justify-center flex-shrink-0">
              <i class="fas fa-exclamation-triangle text-red-600"></i>
            </div>
            <p class="text-sm text-gray-700 leading-relaxed">{{ confirmState.message }}</p>
          </div>
          <div class="flex gap-3 justify-end">
            <button
              @click="answer(false)"
              class="px-4 py-2 text-sm bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors"
            >
              Batal
            </button>
            <button
              @click="answer(true)"
              class="px-4 py-2 text-sm bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors"
            >
              Ya, Lanjutkan
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { useToast } from '@/Composables/useToast';
import { useConfirm } from '@/Composables/useConfirm';

const { toasts } = useToast();
const { state: confirmState, answer } = useConfirm();

const styles = {
  success: 'bg-emerald-600 text-white',
  error:   'bg-red-600 text-white',
  warn:    'bg-amber-500 text-white',
  info:    'bg-primary text-white',
};

const icons = {
  success: 'fas fa-check-circle',
  error:   'fas fa-times-circle',
  warn:    'fas fa-exclamation-triangle',
  info:    'fas fa-info-circle',
};
</script>

<style scoped>
.toast-enter-active,
.toast-leave-active { transition: all 0.25s ease; }
.toast-enter-from  { opacity: 0; transform: translateX(100%); }
.toast-leave-to    { opacity: 0; transform: translateX(100%); }

.fade-enter-active,
.fade-leave-active { transition: opacity 0.2s ease; }
.fade-enter-from,
.fade-leave-to     { opacity: 0; }
</style>
