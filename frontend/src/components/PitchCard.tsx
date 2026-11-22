import { Badge, Button, Card, Group, NumberInput, Stack, Text } from '@mantine/core';
import { useState } from 'react';
import { Link } from 'react-router';
import { formatMoney } from '../lib/format';
import { formatCase, useLeadershipAction, type SeatPitch } from '../lib/leadership';

// A seat holder's pitch in the inbox (PT-M8; TST formulas.md 27.1): what, why, the cost, a
// low, central and high case, and Approve, Modify (a class size or a rate rise) or Decline.
export function PitchCard({ slug, pitch }: { slug: string; pitch: SeatPitch }) {
  const action = useLeadershipAction(slug);
  const [value, setValue] = useState<number | null>(null);
  const pending = pitch.status === 'pending';
  const unit = pitch.case_unit;
  return (
    <Card withBorder data-testid="pitch-card">
      <Group justify="space-between">
        <Text fw={pending ? 600 : 400}>
          <Link to={`/game/${slug}/people/${pitch.holder_id}`}>{pitch.holder_name}</Link> (
          {pitch.seat_label}) pitches {pitch.title}
        </Text>
        <Group gap={6}>
          <Badge size="xs" variant={pending ? 'filled' : 'light'} data-testid="pitch-status">
            {pitch.status}
          </Badge>
          {pitch.follow_through && (
            <Badge size="xs" color={pitch.follow_through === 'hit' ? 'teal' : 'red'}>
              {pitch.follow_through}
            </Badge>
          )}
          <Text size="sm" c="dimmed">
            {pitch.made_label}
          </Text>
        </Group>
      </Group>
      <Stack gap={2} mt={4}>
        <Text size="sm">{pitch.why}.</Text>
        <Text size="sm">
          {pitch.cost_cents > 0 && `Cost now ${formatMoney(pitch.cost_cents)}. `}
          Low {formatCase(unit, pitch.low)} · central {formatCase(unit, pitch.central)} · high{' '}
          {formatCase(unit, pitch.high)} after 24 months.
        </Text>
        {action.error && (
          <Text size="sm" c="red">
            {action.error.message}
          </Text>
        )}
        {pending && (
          <Group mt={4} align="flex-end">
            <Button
              size="xs"
              data-testid="pitch-approve"
              loading={action.isPending}
              onClick={() =>
                action.mutate({ kind: 'answer', pitchId: pitch.id, answer: 'approve' })
              }
            >
              Approve
            </Button>
            {pitch.modifiable && (
              <>
                <NumberInput
                  size="xs"
                  w={130}
                  label={unit === 'bp' ? 'Rise (bp)' : 'Size (people)'}
                  value={value ?? ''}
                  onChange={(v) => setValue(v === '' ? null : Number(v))}
                />
                <Button
                  size="xs"
                  variant="light"
                  disabled={value === null}
                  onClick={() =>
                    value !== null &&
                    action.mutate({ kind: 'answer', pitchId: pitch.id, answer: 'modify', value })
                  }
                >
                  Modify and approve
                </Button>
              </>
            )}
            <Button
              size="xs"
              variant="subtle"
              color="red"
              data-testid="pitch-decline"
              onClick={() =>
                action.mutate({ kind: 'answer', pitchId: pitch.id, answer: 'decline' })
              }
            >
              Decline
            </Button>
          </Group>
        )}
      </Stack>
    </Card>
  );
}
