<script setup>
import { formatDashboardTimestamp } from '@/Utils/dashboardTimeseries.js';
import { parseUTC } from '@/Utils/helpers';

// Admin only: refused requests from uids that belong to no site, e.g. a new Pi
// still on the default uid (admin-LOG).
defineProps({
  rejections: { type: Array, default: () => [] }, // /logger/rejections rows with site_uid === null
});
const REASONS = {
  unknown_uid: 'uid belum terdaftar',
  bad_signature: 'kunci tidak cocok',
  expired: 'token kedaluwarsa',
  malformed: 'format tidak dikenali',
  no_uid: 'tanpa uid',
  missing_token: 'tanpa token',
  bad_data: 'data tidak valid',
};
const when = (ts) => formatDashboardTimestamp(parseUTC(ts), 'Asia/Jakarta');
</script>

<template>
  <section class="mt-6 overflow-hidden rounded-xl border border-line bg-white" aria-labelledby="unknown-loggers-title">
    <h2 id="unknown-loggers-title" class="border-b border-line px-4 py-3 text-[15px] font-bold text-ink md:px-6">Logger tak dikenal</h2>
    <p v-if="!rejections.length" class="px-4 py-4 text-[13px] text-muted md:px-6">
      Tidak ada kiriman dari logger tak dikenal dalam 7 hari terakhir.
    </p>
    <ul v-else class="divide-y divide-line">
      <li v-for="r in rejections" :key="`${r.uid}|${r.source}|${r.reason}`" class="px-4 py-3 text-[13px] md:px-6">
        <span class="font-mono font-semibold text-ink">{{ r.uid || '(token tak terbaca)' }}</span>
        <span class="text-muted"> · {{ r.source }} · {{ REASONS[r.reason] ?? r.reason }} · {{ r.count }}× · terakhir {{ when(r.last_at) }}</span>
        <span v-if="r.last_detail" class="block font-mono text-xs text-muted">{{ r.last_detail }}</span>
      </li>
    </ul>
  </section>
</template>
