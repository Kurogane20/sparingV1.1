<template>
  <div class="relative w-full rounded-xl overflow-hidden border border-slate-200" :style="{ height: height }">
    <!-- Map container -->
    <div ref="mapEl" class="w-full h-full z-0"></div>

    <!-- Loading overlay -->
    <div v-if="loading" class="absolute inset-0 bg-white/80 flex items-center justify-center z-10">
      <div class="flex items-center gap-2 text-slate-500 text-sm">
        <i class="fas fa-spinner fa-spin"></i>
        <span>Memuat peta...</span>
      </div>
    </div>

    <!-- No sites overlay -->
    <div v-if="!loading && (!sites || sites.length === 0)"
      class="absolute inset-0 bg-slate-50 flex flex-col items-center justify-center z-10 gap-2">
      <i class="fas fa-map-marked-alt text-3xl text-slate-300"></i>
      <p class="text-sm text-slate-400">Tidak ada lokasi untuk ditampilkan</p>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch, nextTick } from 'vue';

const props = defineProps({
  sites: {
    type: Array,
    default: () => [],
  },
  activeSiteUid: {
    type: String,
    default: null,
  },
  height: {
    type: String,
    default: '400px',
  },
  zoom: {
    type: Number,
    default: 10,
  },
});

const emit = defineEmits(['site-click']);

const mapEl  = ref(null);
const loading = ref(true);

let map      = null;
let markers  = {};
let L        = null;

// Fix Leaflet default icon URLs broken by Vite bundling
const fixLeafletIcons = (leaflet) => {
  delete leaflet.Icon.Default.prototype._getIconUrl;
  leaflet.Icon.Default.mergeOptions({
    iconUrl:       new URL('leaflet/dist/images/marker-icon.png',    import.meta.url).href,
    iconRetinaUrl: new URL('leaflet/dist/images/marker-icon-2x.png', import.meta.url).href,
    shadowUrl:     new URL('leaflet/dist/images/marker-shadow.png',  import.meta.url).href,
  });
};

const createIcon = (active = false) => L.divIcon({
  className: '',
  html: `
    <div style="
      width: ${active ? 36 : 28}px;
      height: ${active ? 36 : 28}px;
      border-radius: 50% 50% 50% 0;
      transform: rotate(-45deg);
      background: ${active ? '#12333B' : '#0E7C86'};
      border: 3px solid white;
      box-shadow: 0 2px 8px rgba(0,0,0,0.25);
      transition: all 0.2s ease;
    "></div>`,
  iconSize:   [active ? 36 : 28, active ? 36 : 28],
  iconAnchor: [active ? 18 : 14, active ? 36 : 28],
  popupAnchor:[0, -(active ? 40 : 32)],
});

const buildPopup = (site) => `
  <div style="font-family: Inter, sans-serif; min-width: 180px;">
    <div style="font-weight: 700; font-size: 14px; color: #1e293b; margin-bottom: 4px;">${site.name}</div>
    <div style="font-size: 12px; color: #64748b; margin-bottom: 6px;">${site.company_name}</div>
    <div style="font-size: 11px; color: #94a3b8;">
      <i class="fas fa-map-pin" style="margin-right: 4px;"></i>
      ${site.lat?.toFixed(5)}, ${site.lon?.toFixed(5)}
    </div>
    <div style="margin-top: 8px; padding: 4px 10px; background: #12333B; color: white; border-radius: 6px; font-size: 12px; font-weight: 600; text-align: center; cursor: pointer;"
      onclick="document.dispatchEvent(new CustomEvent('map-site-click', {detail: '${site.uid}'}))">
      Lihat Dashboard
    </div>
  </div>
`;

const clearMarkers = () => {
  Object.values(markers).forEach(m => map.removeLayer(m));
  markers = {};
};

const addMarkers = () => {
  if (!map || !L) return;
  clearMarkers();

  const validSites = props.sites.filter(s => s.lat != null && s.lon != null);
  if (!validSites.length) return;

  const bounds = [];

  validSites.forEach(site => {
    const isActive = site.uid === props.activeSiteUid;
    const marker = L.marker([site.lat, site.lon], { icon: createIcon(isActive), zIndexOffset: isActive ? 1000 : 0 })
      .addTo(map)
      .bindPopup(buildPopup(site), { maxWidth: 220 });

    if (isActive) marker.openPopup();

    marker.on('click', () => emit('site-click', site));
    markers[site.uid] = marker;
    bounds.push([site.lat, site.lon]);
  });

  if (bounds.length === 1) {
    map.setView(bounds[0], props.zoom);
  } else if (bounds.length > 1) {
    map.fitBounds(bounds, { padding: [40, 40], maxZoom: 14 });
  }
};

const updateActiveMarker = () => {
  if (!map || !L) return;
  Object.entries(markers).forEach(([uid, marker]) => {
    marker.setIcon(createIcon(uid === props.activeSiteUid));
    marker.setZIndexOffset(uid === props.activeSiteUid ? 1000 : 0);
  });
  if (props.activeSiteUid && markers[props.activeSiteUid]) {
    markers[props.activeSiteUid].openPopup();
  }
};

const initMap = async () => {
  await nextTick();
  if (!mapEl.value) return;

  // Dynamically import Leaflet (browser only)
  const leafletModule = await import('leaflet');
  await import('leaflet/dist/leaflet.css');
  L = leafletModule.default || leafletModule;

  fixLeafletIcons(L);

  // Default center: Indonesia
  const center = props.sites.find(s => s.lat && s.lon)
    ? [props.sites[0].lat, props.sites[0].lon]
    : [-2.5, 118.0];

  map = L.map(mapEl.value, {
    center,
    zoom: props.zoom,
    zoomControl: true,
    attributionControl: true,
  });

  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '&copy; <a href="https://openstreetmap.org">OpenStreetMap</a>',
    maxZoom: 19,
  }).addTo(map);

  addMarkers();
  loading.value = false;
};

// Listen for popup button click events
const handleMapSiteClick = (e) => {
  const site = props.sites.find(s => s.uid === e.detail);
  if (site) emit('site-click', site);
};

onMounted(() => {
  initMap();
  document.addEventListener('map-site-click', handleMapSiteClick);
});

onUnmounted(() => {
  document.removeEventListener('map-site-click', handleMapSiteClick);
  if (map) { map.remove(); map = null; }
});

watch(() => props.sites, () => { if (map) addMarkers(); }, { deep: true });
watch(() => props.activeSiteUid, () => { if (map) updateActiveMarker(); });
</script>
