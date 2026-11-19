import { Card, Group, Table, Text, Title } from '@mantine/core';
import { useParams } from 'react-router';
import { useGame, usePayroll } from '../lib/api';
import { formatMoney } from '../lib/format';

export function OverviewScreen() {
  const { slug = '' } = useParams();
  const game = useGame(slug);
  const payroll = usePayroll(slug);
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
      {payroll.data && (
        <Card withBorder mt="md" maw={560} data-testid="payroll">
          <Title order={4}>Payroll and costs this month</Title>
          <Text size="sm" c="dimmed" mb="xs">
            {payroll.data.headcount} people on the books; salaries{' '}
            {formatMoney(payroll.data.annual_salaries_cents)} a year. Year-end bonuses are paid in{' '}
            {payroll.data.bonus_month_label} (about {formatMoney(payroll.data.bonus_estimate_cents)}{' '}
            at today&apos;s staff).
          </Text>
          <Table>
            <Table.Tbody>
              {payroll.data.lines
                .filter((line) => line.amount_cents !== 0)
                .map((line) => (
                  <Table.Tr key={line.label}>
                    <Table.Td>{line.label}</Table.Td>
                    <Table.Td className="tst-num" ta="right">
                      {formatMoney(line.amount_cents)}
                    </Table.Td>
                  </Table.Tr>
                ))}
              <Table.Tr>
                <Table.Td fw={600}>Total</Table.Td>
                <Table.Td className="tst-num" ta="right" fw={600} data-testid="payroll-total">
                  {formatMoney(payroll.data.total_cents)}
                </Table.Td>
              </Table.Tr>
            </Table.Tbody>
          </Table>
        </Card>
      )}
    </>
  );
}
