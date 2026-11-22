// Ported from TST frontend/src/components/OwnerRecord.tsx @ 80a38079; changed: one panel for
// every owner on the Automation screen (the view carries the records), Partner Track's counts
// (decisions, proposals approved and declined, workload against the month's energy) and the
// owner's own note. Outcomes only: never a score, a draw or which decision was a mistake.
import { Stack, Text } from '@mantine/core';
import { Link } from 'react-router';
import type { OwnerRecord } from '../lib/automation';

export function OwnerRecordPanel({ slug, owners }: { slug: string; owners: OwnerRecord[] }) {
  if (owners.length === 0) return null;
  return (
    <div className="tst-panel" data-testid="owner-records">
      <h3 className="tst-ptitle">Owners' records</h3>
      <Stack gap="xs">
        {owners.map((o) => (
          <div key={o.person_id} data-testid="owner-record">
            <Text size="sm" fw={600}>
              <Link to={`/game/${slug}/people/${o.person_id}`}>{o.name}</Link>: {o.areas.join(', ')}
            </Text>
            <Text size="xs" c={o.workload > o.capacity ? 'orange' : 'dimmed'}>
              Workload {o.workload} of {o.capacity} a month · {o.decisions} decision
              {o.decisions === 1 ? '' : 's'} · {o.proposals} proposal
              {o.proposals === 1 ? '' : 's'}: {o.approved} approved, {o.declined} declined or
              expired
            </Text>
            <Text size="xs" fs="italic">
              “{o.note}”
            </Text>
          </div>
        ))}
      </Stack>
    </div>
  );
}
