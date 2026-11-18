import { Card, Group, Text, Title } from '@mantine/core';
import { useParams } from 'react-router';
import { useGame } from '../lib/api';
import { formatMoney } from '../lib/format';

export function OverviewScreen() {
  const { slug = '' } = useParams();
  const game = useGame(slug);
  if (!game.data) return <Text c="dimmed">Loading…</Text>;
  const g = game.data;
  return (
    <>
      <Title order={2} mb="md">
        Overview
      </Title>
      <Group align="stretch">
        <Card withBorder miw={200}>
          <Text c="dimmed" size="sm">
            Cash
          </Text>
          <Text size="xl" fw={600} data-testid="cash">
            {formatMoney(g.cash_cents)}
          </Text>
        </Card>
        <Card withBorder miw={200}>
          <Text c="dimmed" size="sm">
            Month
          </Text>
          <Text size="xl" fw={600}>
            {g.turn + 1 > g.turns_in_campaign ? g.turns_in_campaign : g.turn + 1} of{' '}
            {g.turns_in_campaign}
          </Text>
        </Card>
      </Group>
    </>
  );
}
