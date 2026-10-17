// "Kelengkapan data hari ini" as one bar over the whole day: readings received,
// readings due by now that are missing, and the part of the day not yet due.
// The headline percentage (received ÷ due) says how complete the data is so
// far; the bar shows how far through the day that is, so 96% at 17:00 no
// longer reads as "the day is 96% done".

const round1 = (value) => Math.round(value * 10) / 10;

export function completenessSegments(kpi) {
  if (!kpi || !Number.isFinite(kpi.actual) || !Number.isFinite(kpi.expected)) return null;
  const received = Math.max(0, kpi.actual);
  const due = Math.max(0, kpi.expected);
  // Older API versions sent no whole-day target: the bar then ends at "due".
  const total = Math.max(Number.isFinite(kpi.expected_total) ? kpi.expected_total : due, received, due);
  const missing = Math.max(0, due - received);
  const notYet = Math.max(0, total - Math.max(due, received));
  const pct = (count) => (total > 0 ? round1((count / total) * 100) : 0);
  const receivedPct = pct(received);
  const missingPct = pct(missing);
  return {
    received,
    missing,
    notYet,
    total,
    receivedPct,
    missingPct,
    // The remainder, so the three widths always add up to exactly 100%.
    notYetPct: notYet > 0 ? round1(100 - receivedPct - missingPct) : 0,
  };
}
