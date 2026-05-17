import { ref } from 'vue';

const toasts = ref([]);
let _id = 0;

function show(message, type = 'info', duration = 3500) {
  const id = ++_id;
  toasts.value.push({ id, message, type });
  setTimeout(() => {
    toasts.value = toasts.value.filter(t => t.id !== id);
  }, duration);
}

export function useToast() {
  return {
    toasts,
    success: (msg) => show(msg, 'success'),
    error:   (msg) => show(msg, 'error', 5000),
    warn:    (msg) => show(msg, 'warn'),
    info:    (msg) => show(msg, 'info'),
  };
}
