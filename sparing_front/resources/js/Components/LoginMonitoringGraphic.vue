<template>
  <div class="monitoring-flow" aria-hidden="true">
    <svg
      class="monitoring-flow__canvas"
      viewBox="0 0 900 300"
      preserveAspectRatio="none"
      focusable="false"
      xmlns="http://www.w3.org/2000/svg"
    >
      <defs>
        <linearGradient id="loginFlowSignal" x1="0" y1="0" x2="1" y2="0">
          <stop offset="0" stop-color="#70BFC6" stop-opacity="0.12" />
          <stop offset="0.48" stop-color="#8ED8DE" stop-opacity="0.62" />
          <stop offset="1" stop-color="#70BFC6" stop-opacity="0.12" />
        </linearGradient>
        <pattern id="loginTelemetryGrid" width="60" height="48" patternUnits="userSpaceOnUse">
          <path d="M 60 0 L 0 0 0 48" fill="none" stroke="#B9DADD" stroke-opacity="0.09" stroke-width="1" />
        </pattern>
      </defs>

      <rect x="20" y="16" width="860" height="250" rx="20" fill="url(#loginTelemetryGrid)" />

      <path
        class="monitoring-flow__route monitoring-flow__route--base"
        d="M144 172 C174 172 186 96 243 96 S343 164 450 164 S549 80 639 80 S700 176 756 176"
      />
      <path
        class="monitoring-flow__route monitoring-flow__route--signal"
        pathLength="1"
        d="M144 172 C174 172 186 96 243 96 S343 164 450 164 S549 80 639 80 S700 176 756 176"
      />

      <g class="monitoring-flow__telemetry">
        <path d="M72 238 H846" />
        <polyline points="72,238 118,238 142,226 167,249 198,238 252,238 278,218 306,253 338,238 406,238 432,229 457,245 485,238 544,238 574,222 603,248 632,238 701,238 728,228 755,246 782,238 846,238" />
        <circle cx="198" cy="238" r="3" />
        <circle cx="338" cy="238" r="3" />
        <circle cx="485" cy="238" r="3" />
        <circle cx="632" cy="238" r="3" />
        <circle cx="782" cy="238" r="3" />
      </g>

      <g class="monitoring-flow__parameters">
        <text x="72" y="278">pH</text>
        <text x="252" y="278">TSS</text>
        <text x="432" y="278">COD</text>
        <text x="603" y="278">NH3-N</text>
        <text x="782" y="278">DEBIT</text>
      </g>
    </svg>

    <div
      v-for="node in flowNodes"
      :key="node.label"
      class="monitoring-flow__node"
      :class="`monitoring-flow__node--${node.key}`"
      :style="{ '--flow-x': `${node.x}%`, '--flow-y': `${node.y}%` }"
    >
      <span class="monitoring-flow__icon">
        <i :class="node.icon"></i>
      </span>
      <span class="monitoring-flow__copy">
        <span class="monitoring-flow__label">{{ node.label }}</span>
        <span class="monitoring-flow__meta">{{ node.meta }}</span>
      </span>
    </div>
  </div>
</template>

<script setup>
const flowNodes = [
  { key: 'sensor', label: 'Sensor', meta: 'Akuisisi data', icon: 'fas fa-water', x: 16, y: 57.3 },
  { key: 'logger', label: 'Data Logger', meta: 'Interval 2 menit', icon: 'fas fa-hard-drive', x: 27, y: 32 },
  { key: 'server', label: 'Server', meta: 'Validasi terpusat', icon: 'fas fa-server', x: 50, y: 54.7 },
  { key: 'dashboard', label: 'Dashboard', meta: 'Monitoring', icon: 'fas fa-chart-line', x: 71, y: 26.7 },
  { key: 'klhk', label: 'KLHK', meta: 'Pelaporan', icon: 'fas fa-file-alt', x: 84, y: 58.7 },
];
</script>

<style scoped>
.monitoring-flow {
  position: relative;
  width: 100%;
  min-height: 220px;
  max-width: 940px;
  margin-inline: auto;
}

/* Grow the illustration on taller/large desktops so it fills the column
   instead of floating small in a lot of empty space (the main complaint on
   1440–1920px screens). The % node positions stay proportional. */
@media (min-width: 1280px) {
  .monitoring-flow { min-height: 300px; }
}

@media (min-width: 1536px) and (min-height: 900px) {
  .monitoring-flow { min-height: 360px; }
}

.monitoring-flow__canvas {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  overflow: visible;
}

.monitoring-flow__route {
  fill: none;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.monitoring-flow__route--base {
  stroke: rgba(153, 211, 216, 0.18);
  stroke-width: 1.5;
}

.monitoring-flow__route--signal {
  stroke: url(#loginFlowSignal);
  stroke-width: 2;
  stroke-dasharray: 0.025 0.055;
  animation: telemetry-travel 16s linear infinite;
}

.monitoring-flow__telemetry {
  fill: rgba(154, 214, 219, 0.24);
  stroke: rgba(154, 214, 219, 0.15);
  stroke-width: 1.25;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.monitoring-flow__parameters {
  fill: rgba(190, 222, 225, 0.28);
  font-family: 'IBM Plex Mono', ui-monospace, monospace;
  font-size: 9px;
  font-weight: 500;
  letter-spacing: 0.12em;
}

.monitoring-flow__node {
  position: absolute;
  left: var(--flow-x);
  top: var(--flow-y);
  display: flex;
  align-items: center;
  gap: 0.55rem;
  min-width: max-content;
  padding: 0.45rem 0.6rem;
  color: rgba(220, 236, 238, 0.76);
  background: rgba(9, 39, 47, 0.58);
  border: 1px solid rgba(156, 214, 219, 0.17);
  border-radius: 0.5rem;
  box-shadow: 0 8px 24px rgba(3, 22, 27, 0.08);
  transform: translate(-50%, -50%);
}

.monitoring-flow__icon {
  display: grid;
  width: 1.75rem;
  height: 1.75rem;
  flex: none;
  place-items: center;
  color: rgba(167, 220, 224, 0.72);
  background: rgba(93, 176, 184, 0.1);
  border: 1px solid rgba(149, 211, 217, 0.13);
  border-radius: 50%;
  font-size: 0.66rem;
}

.monitoring-flow__copy {
  display: flex;
  flex-direction: column;
  line-height: 1.15;
}

.monitoring-flow__label {
  font-size: 0.68rem;
  font-weight: 600;
  letter-spacing: 0.015em;
}

.monitoring-flow__meta {
  margin-top: 0.2rem;
  color: rgba(161, 199, 203, 0.46);
  font-family: 'IBM Plex Mono', ui-monospace, monospace;
  font-size: 0.5rem;
  letter-spacing: 0.04em;
  text-transform: uppercase;
}

@keyframes telemetry-travel {
  to { stroke-dashoffset: -1; }
}

@media (max-width: 1279px) {
  .monitoring-flow {
    min-height: 190px;
  }

  .monitoring-flow__node {
    gap: 0.4rem;
    padding: 0.38rem 0.46rem;
  }

  .monitoring-flow__icon {
    width: 1.5rem;
    height: 1.5rem;
    font-size: 0.58rem;
  }

  .monitoring-flow__label {
    font-size: 0.61rem;
  }

  .monitoring-flow__meta {
    display: none;
  }
}

@media (prefers-reduced-motion: reduce) {
  .monitoring-flow__route--signal {
    animation: none;
  }
}
</style>
