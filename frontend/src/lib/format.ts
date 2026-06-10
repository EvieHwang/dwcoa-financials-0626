// Money is integer cents at the API boundary. `centsToUsd` is the ONLY money
// formatter in the app (cents/100 → toLocaleString USD); no new client-side
// money math is introduced by the redesign (visual-redesign-009).
export function centsToUsd(cents: number | null | undefined): string {
  if (cents === null || cents === undefined) return "";
  return (cents / 100).toLocaleString("en-US", {
    style: "currency",
    currency: "USD",
  });
}

// A deterministic recent range that always includes the migrated history's
// years; not clock-fragile (clamped so the lower bound stays well below today).
export function yearOptions(): number[] {
  const startYear = Math.max(new Date().getFullYear(), 2026);
  return Array.from({ length: startYear - 2018 }, (_, i) => startYear - i);
}

export function todayIso(): string {
  return new Date().toISOString().slice(0, 10);
}
