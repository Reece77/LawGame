import { Group, Progress, Text } from '@mantine/core';
import { strainBand } from '../lib/attr';
import { formatWhole } from '../lib/format';

const COLORS = { ok: 'accent', high: 'orange', burnout: 'red' } as const;

/** Strain 0-100 (spec 5.6), shown for the player's own firm only. */
export function StrainBar({
  strain,
  burntOut,
  compact = false,
}: {
  strain: number;
  burntOut: boolean;
  compact?: boolean;
}) {
  return (
    <Group gap={6} wrap="nowrap" data-testid="strain">
      <Progress
        value={strain}
        color={COLORS[strainBand(strain)]}
        w={compact ? 60 : 160}
        size={compact ? 'sm' : 'md'}
        aria-label={`Strain ${formatWhole(strain)}`}
      />
      <Text size="sm" className="tst-num">
        {formatWhole(strain)}
      </Text>
      {burntOut && (
        <Text size="xs" c="red" fw={600}>
          Burnt out
        </Text>
      )}
    </Group>
  );
}
