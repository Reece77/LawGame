import { sparkPoints } from '../lib/spark';

/** A small trend line, e.g. a practice's monthly demand. */
export function Sparkline({ values, label }: { values: readonly number[]; label: string }) {
  if (values.length < 2) return <span className="tst-muted">—</span>;
  return (
    <svg viewBox="0 0 100 24" role="img" aria-label={label} style={{ width: 100, height: 24 }}>
      <polyline
        points={sparkPoints(values)}
        fill="none"
        stroke="var(--ptk-accent)"
        strokeWidth={2}
      />
    </svg>
  );
}
