<template>
  <div>
    <div class="grid gap-[3px]" style="grid-template-columns: repeat(31, 1fr)">
      <i v-for="d in days" :key="d.date"
         :title="`${d.date} — ${label(d.status)}`"
         class="aspect-square rounded-[2px]"
         :class="cls(d.status)"
         :style="d.status === 'none' ? 'background:#DCE4E5' : ''"></i>
    </div>
    <div class="flex gap-3.5 text-[11.5px] text-[#617377] mt-2.5 flex-wrap">
      <span><i class="inline-block w-2.5 h-2.5 rounded-[2px] bg-success mr-1.5 align-[-1px]"></i>Patuh penuh</span>
      <span><i class="inline-block w-2.5 h-2.5 rounded-[2px] bg-warning mr-1.5 align-[-1px]"></i>Ada peringatan</span>
      <span><i class="inline-block w-2.5 h-2.5 rounded-[2px] bg-danger mr-1.5 align-[-1px]"></i>Ada pelampauan</span>
      <span><i class="inline-block w-2.5 h-2.5 rounded-[2px] mr-1.5 align-[-1px]" style="background:#DCE4E5"></i>Belum berjalan</span>
    </div>
  </div>
</template>
<script setup>
defineProps({ days: { type: Array, default: () => [] } });
const cls = (s) => ({ ok: 'bg-success', warning: 'bg-warning', violation: 'bg-danger' }[s] || '');
const label = (s) => ({ ok: 'patuh', warning: 'peringatan', violation: 'pelampauan', none: 'belum berjalan' }[s] || s);
</script>
