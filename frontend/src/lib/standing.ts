// PT-M16: display helpers for the Rankings and Press screens. No game values are computed
// here: bands, scores and progress are the API's; these only format and gate the forms.

/** A directory band as shown: "Band 2", or "Not ranked" when the firm has none. */
export function bandText(band: number | null | undefined): string {
  return band === null || band === undefined ? 'Not ranked' : `Band ${band}`;
}

/** A firm's band history for a practice: "2005 B3 · 2006 B2", or a dash when empty. */
export function bandHistoryText(history: { year: number; band: number }[]): string {
  return history.length === 0 ? '—' : history.map((h) => `${h.year} B${h.band}`).join(' · ');
}

/** A reputation or credibility change with its sign, to one decimal. */
export function signedDelta(delta: number): string {
  const v = Math.round(delta * 10) / 10;
  return `${v > 0 ? '+' : v < 0 ? '−' : ''}${Math.abs(v).toFixed(1)}`;
}

/** Toggle an id in a capped selection (checkbox lists): adding past `max` changes nothing. */
export function toggleId(ids: number[], id: number, max: number): number[] {
  if (ids.includes(id)) return ids.filter((x) => x !== id);
  return ids.length >= max ? ids : [...ids, id];
}

export interface ClaimDraft {
  kind: string | null;
  practice: string | null;
  target: number | null;
  months: number | null;
}

/**
 * Why a public claim's form cannot be sent yet (null when it can). The rules are the API's
 * input rules (PT-M16 AnswerIn), checked here only so the buttons say what is missing; the
 * engine validates again and has the last word.
 */
export function claimProblem(
  d: ClaimDraft,
  tone: string,
  ctx: { lawyers: number; claimMonths: [number, number]; claimsOpen: number; claimsMax: number },
): string | null {
  if (d.kind === null) return null;
  if (tone === 'deflect') return 'A claim needs a bold or measured answer';
  if (ctx.claimsOpen >= ctx.claimsMax) return `At most ${ctx.claimsMax} claims open at once`;
  const [lo, hi] = ctx.claimMonths;
  const timed = d.kind === 'headcount' || d.kind === 'band';
  if (timed && (d.months === null || d.months < lo || d.months > hi))
    return `Months must be ${lo}-${hi}`;
  if (d.kind === 'headcount' && (d.target === null || d.target <= ctx.lawyers))
    return `Target must be above today's ${ctx.lawyers} lawyers`;
  if (d.kind === 'band') {
    if (d.practice === null) return 'Choose a practice';
    if (d.target === null || d.target < 1 || d.target > 6) return 'Target band must be 1-6';
  }
  return null;
}
