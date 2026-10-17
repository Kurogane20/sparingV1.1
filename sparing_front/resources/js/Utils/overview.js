// Command Center presentation helpers.

export function loggerLabel(state) {
  if (!state) return 'Logger belum terpantau';
  return { alive: 'Logger hidup', down: 'Logger mati' }[state] ?? `Logger ${state}`;
}

const percent = (value) => `${Number(value).toLocaleString('id-ID', { maximumFractionDigits: 1 })}%`;

// Per-site compliance vs today's completeness. Horizontal bars keep long site
// names readable (vertical bars rotated them 45°); a site without compliance
// data gets no bar instead of a misleading 0%.
export function comparisonChart(sites) {
  const list = Array.isArray(sites) ? sites : [];
  return {
    height: Math.max(160, 70 + list.length * 44),
    series: [
      { name: 'Kepatuhan 24 jam', data: list.map((site) => site.compliance_pct ?? null) },
      { name: 'Kelengkapan hari ini', data: list.map((site) => site.completeness_pct ?? null) },
    ],
    options: {
      chart: { type: 'bar', toolbar: { show: false }, fontFamily: 'Inter, sans-serif', animations: { enabled: false } },
      colors: ['#0E7C86', '#9A6B00'],
      plotOptions: { bar: { horizontal: true, barHeight: '70%', borderRadius: 3 } },
      dataLabels: { enabled: false },
      stroke: { width: 0 },
      grid: { borderColor: '#EEF2F3', strokeDashArray: 4 },
      xaxis: {
        categories: list.map((site) => site.name),
        min: 0,
        max: 100,
        tickAmount: 5,
        labels: { style: { colors: '#617377', fontSize: '10px' }, formatter: (value) => `${Math.round(value)}%` },
      },
      yaxis: { labels: { style: { colors: '#12333B', fontSize: '11px' }, maxWidth: 220 } },
      legend: { position: 'top', horizontalAlign: 'right', fontSize: '11px', labels: { colors: '#617377' } },
      tooltip: { y: { formatter: (value) => (value == null ? 'Tidak ada data' : percent(value)) } },
    },
  };
}
