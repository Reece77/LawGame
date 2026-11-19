// Ported from TST frontend/src/components/AttributeRange.tsx @ 02fba2aa; changed: {lo, hi}.
import { attributeTier, rangeText, type Range } from '../lib/attr';

interface Props {
  range: Range;
  label?: string; // accessible name, e.g. "Advocacy"
}

/** A revealed attribute: "14–17" while uncertain, "14" once known, colored by midpoint. */
export function AttributeRange({ range, label }: Props) {
  const text = rangeText(range);
  return (
    <span
      className={`tst-num tst-tier-${attributeTier(range)}`}
      title={label ? `${label}: ${text}` : undefined}
    >
      {text}
    </span>
  );
}
