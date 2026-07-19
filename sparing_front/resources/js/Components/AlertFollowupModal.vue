<template>
  <div v-if="open" class="fixed inset-0 z-50 flex items-center justify-center bg-ink/40 p-4" @click.self="$emit('close')">
    <div class="bg-white rounded-lg border border-[#D7E0E1] w-full max-w-md p-5">
      <h3 class="text-[15px] font-bold text-ink mb-1">{{ mode === 'resolve' ? 'Selesaikan alarm' : 'Tindak lanjut alarm' }}</h3>
      <p v-if="alert" class="text-[12.5px] text-[#617377] mb-3">{{ alert.site_name }} · {{ alert.field }} = {{ alert.value }}</p>
      <label class="block text-[12.5px] font-semibold text-ink mb-1">
        Catatan tindak lanjut <span v-if="mode==='resolve'" class="text-danger">*</span>
      </label>
      <textarea v-model="note" rows="4" class="w-full border border-[#C4D1D3] rounded-md p-2 text-sm" :placeholder="mode==='resolve' ? 'Wajib diisi…' : 'Opsional…'"></textarea>
      <p v-if="mode==='resolve'" class="text-[11.5px] text-[#617377] mt-1">Catatan wajib diisi sebelum alarm dapat ditutup (SOP-ENV).</p>
      <div class="flex justify-end gap-2 mt-4">
        <button class="px-3 py-2 rounded-md border border-[#C4D1D3] text-sm" @click="$emit('close')">Batal</button>
        <button class="px-3 py-2 rounded-md text-sm text-white bg-primary hover:bg-primary-dark disabled:opacity-50"
                :disabled="mode==='resolve' && !note.trim()"
                @click="$emit('submit', { note: note.trim() })">
          {{ mode === 'resolve' ? 'Tutup alarm' : 'Simpan' }}
        </button>
      </div>
    </div>
  </div>
</template>
<script setup>
import { ref, watch } from 'vue';
const props = defineProps({ open: Boolean, mode: { type: String, default: 'followup' }, alert: Object });
defineEmits(['close', 'submit']);
const note = ref('');
watch(() => props.open, (v) => { if (v) note.value = ''; });
</script>
