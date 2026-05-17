import { ref } from 'vue';

const state = ref({ visible: false, message: '', resolve: null });

export function useConfirm() {
  const confirm = (message) =>
    new Promise((resolve) => {
      state.value = { visible: true, message, resolve };
    });

  const answer = (val) => {
    if (state.value.resolve) state.value.resolve(val);
    state.value = { visible: false, message: '', resolve: null };
  };

  return { state, confirm, answer };
}
