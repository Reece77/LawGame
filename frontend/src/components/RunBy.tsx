// Ported from TST frontend/src/components/RunBy.tsx @ 80a38079; changed: the screen names its
// areas (TST matched the route), "Take over" and "Hand back" (to the last owner, or the
// Automation screen to choose one), the run-by endpoint per area. No game logic here.
import { Button, Group, Text } from '@mantine/core';
import { Link } from 'react-router';
import { useAutomation, useAutomationAction, useRunBy } from '../lib/automation';

function One({ slug, area, slot }: { slug: string; area: string; slot: number }) {
  const runBy = useRunBy(slug, area, slot);
  const action = useAutomationAction(slug);
  const r = runBy.data;
  if (!r) return null;
  if (!r.owner) {
    return (
      <Text size="xs" c="dimmed" data-testid={`run-by-${area}`}>
        {r.label}: you run it
        {r.can_automate && (
          <>
            {' '}
            · <Link to={`/game/${slug}/automation`}>Hand back</Link>
          </>
        )}
      </Text>
    );
  }
  return (
    <Group gap={4} data-testid={`run-by-${area}`}>
      <Text size="xs">
        {r.label}: run by{' '}
        <Link to={`/game/${slug}/people/${r.owner.person_id}`}>{r.owner.name}</Link> ·
      </Text>
      <Button
        size="compact-xs"
        variant="subtle"
        disabled={action.isPending}
        onClick={() => action.mutate({ kind: 'take_over', area, slot })}
        data-testid={`take-over-${area}`}
      >
        Take over
      </Button>
    </Group>
  );
}

/** "Run by <name> · Take over" for each area a screen drives (spec 9.4; TST 40.8). */
export function RunBy({ slug, areas }: { slug: string; areas: string[] }) {
  return (
    <Group gap="md" mb={4}>
      {areas.map((a) => (
        <One key={a} slug={slug} area={a} slot={0} />
      ))}
    </Group>
  );
}

/** The Org screen: each practice group whose staffing is automated, with its owner. */
export function StaffingRunBy({ slug }: { slug: string }) {
  const auto = useAutomation(slug);
  const action = useAutomationAction(slug);
  const rows = (auto.data?.areas ?? []).filter(
    (a) => a.area === 'staffing' && a.status === 'automated' && a.owner,
  );
  if (rows.length === 0) return null;
  return (
    <Group gap="md" mb={4} data-testid="run-by-staffing">
      {rows.map((a) => (
        <Group key={a.slot} gap={4}>
          <Text size="xs">
            {a.label}: run by{' '}
            <Link to={`/game/${slug}/people/${a.owner?.person_id ?? 0}`}>{a.owner?.name}</Link> ·
          </Text>
          <Button
            size="compact-xs"
            variant="subtle"
            disabled={action.isPending}
            onClick={() => action.mutate({ kind: 'take_over', area: a.area, slot: a.slot })}
          >
            Take over
          </Button>
        </Group>
      ))}
    </Group>
  );
}
