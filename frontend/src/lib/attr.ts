// Ported from TST frontend/src/lib/attr.ts @ 02fba2aa; changed: ranges arrive as {lo, hi};
// the morale band waits for PT-M1b; a strain band (spec 5.6) is added.
// Attribute display rules from docs/wireframes.md. Ranges arrive from the API; this only
// chooses a color and a label for them.

export interface Range {
  lo: number;
  hi: number;
}

export type Tier = 1 | 2 | 3 | 4;

/** Color tier by range midpoint: 1-5, 6-10, 11-15, 16-20. */
export function attributeTier({ lo, hi }: Range): Tier {
  const mid = (lo + hi) / 2;
  if (mid >= 16) return 4;
  if (mid >= 11) return 3;
  if (mid >= 6) return 2;
  return 1;
}

/** "14–17" for a range, "14" for a known value. */
export function rangeText({ lo, hi }: Range): string {
  return lo === hi ? String(lo) : `${lo}–${hi}`;
}

/** Strain bar color band (spec 5.6): 80+ is burnout territory, 60-79 a warning. */
export type StrainBand = 'ok' | 'high' | 'burnout';

export function strainBand(strain: number): StrainBand {
  if (strain >= 80) return 'burnout';
  if (strain >= 60) return 'high';
  return 'ok';
}

/** Sort key for "top skills": highest midpoint first, then narrower range, then label. */
export function byStrength<T extends { label: string } & Range>(a: T, b: T): number {
  const mid = (r: Range) => r.lo + r.hi;
  return mid(b) - mid(a) || a.hi - a.lo - (b.hi - b.lo) || a.label.localeCompare(b.label);
}
