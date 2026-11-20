import { Badge, Tooltip } from '@mantine/core';

const COLOR = { low: 'gray', medium: 'orange', high: 'red' } as const;

/** A matter's risk level as the API judged it, with its reasons on hover. */
export function RiskBadge({ risk, notes }: { risk: 'low' | 'medium' | 'high'; notes: string[] }) {
  const badge = (
    <Badge size="sm" variant="light" color={COLOR[risk]} data-testid="risk">
      {risk}
    </Badge>
  );
  return notes.length ? <Tooltip label={notes.join('; ')}>{badge}</Tooltip> : badge;
}
