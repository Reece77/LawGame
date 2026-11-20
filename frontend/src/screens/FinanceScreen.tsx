import {
  Button,
  Card,
  Group,
  SegmentedControl,
  SimpleGrid,
  Stack,
  Table,
  Text,
  Title,
} from '@mantine/core';
import { useState } from 'react';
import { useParams } from 'react-router';
import { useBills, useFinance, useRespondDispute, type Bill, type Finance } from '../lib/api';
import { formatBpPercent, formatMoneyWhole } from '../lib/format';

// The Finance screen (spec 16; PT-M3b): the revenue chain's KPIs, the P&L in its accrual and
// cash views, the balance sheet, WIP and receivables ageing, and open bills with their
// disputes. Every number arrives from the API; this screen only formats it.

function Tile(props: { label: string; value: string; testId?: string; note?: string }) {
  return (
    <Card withBorder>
      <Text c="dimmed" size="sm">
        {props.label}
      </Text>
      <Text size="xl" fw={600} data-testid={props.testId}>
        {props.value}
      </Text>
      {props.note && (
        <Text size="xs" c="dimmed">
          {props.note}
        </Text>
      )}
    </Card>
  );
}

const pct = (bp: number | null) => (bp === null ? '—' : formatBpPercent(bp));

function Kpis({ f }: { f: Finance }) {
  const k = f.kpis;
  return (
    <SimpleGrid cols={{ base: 2, md: 5 }}>
      <Tile
        label="Fees last month"
        value={formatMoneyWhole(k.revenue_cents)}
        testId="kpi-revenue"
      />
      <Tile label="Collected last month" value={formatMoneyWhole(k.collections_cents)} />
      <Tile
        label="Utilisation"
        value={pct(k.utilisation_bp)}
        note="billable ÷ capacity, last month"
      />
      <Tile
        label="Realisation"
        value={pct(k.realisation_bp)}
        testId="kpi-realisation"
        note="billed ÷ standard, 12 months"
      />
      <Tile
        label="Collection"
        value={pct(k.collection_bp)}
        testId="kpi-collection"
        note="collected ÷ billed, 12 months"
      />
      <Tile label="Unbilled WIP" value={formatMoneyWhole(k.wip_cents)} />
      <Tile label="Receivables" value={formatMoneyWhole(k.receivables_cents)} />
      <Tile
        label="Lockup"
        value={k.lockup_days === null ? '—' : `${k.lockup_days} days`}
        testId="kpi-lockup"
        note="(WIP + receivables) ÷ daily fees"
      />
      <Tile
        label="Client money held"
        value={formatMoneyWhole(k.client_money_cents)}
        note="the client account: never firm cash"
      />
      <Tile label="Open disputes" value={String(k.open_disputes)} />
    </SimpleGrid>
  );
}

function Statements({ f }: { f: Finance }) {
  const [basis, setBasis] = useState<'accrual' | 'cash'>('accrual');
  const shown = f.statements.filter((s) => s.basis === basis);
  return (
    <Card withBorder data-testid="statements">
      <Group justify="space-between" mb="xs">
        <Title order={4}>Profit and loss</Title>
        <SegmentedControl
          size="xs"
          value={basis}
          onChange={(v) => setBasis(v as 'accrual' | 'cash')}
          data={[
            { label: 'Accrual', value: 'accrual' },
            { label: 'Cash', value: 'cash' },
          ]}
        />
      </Group>
      <SimpleGrid cols={{ base: 1, md: 2 }}>
        {shown.map((s) => (
          <Table key={s.label} data-testid={`pnl-${s.basis}`}>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>{s.label}</Table.Th>
                <Table.Th ta="right">Amount</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {s.lines.map((line) => (
                <Table.Tr key={line.account}>
                  <Table.Td>{line.label}</Table.Td>
                  <Table.Td className="tst-num" ta="right">
                    {formatMoneyWhole(line.amount_cents)}
                  </Table.Td>
                </Table.Tr>
              ))}
              <Table.Tr>
                <Table.Td fw={600}>Revenue</Table.Td>
                <Table.Td className="tst-num" ta="right" fw={600}>
                  {formatMoneyWhole(s.revenue_cents)}
                </Table.Td>
              </Table.Tr>
              <Table.Tr>
                <Table.Td fw={600}>Costs</Table.Td>
                <Table.Td className="tst-num" ta="right" fw={600}>
                  {formatMoneyWhole(s.costs_cents)}
                </Table.Td>
              </Table.Tr>
              <Table.Tr>
                <Table.Td fw={600}>Profit</Table.Td>
                <Table.Td className="tst-num" ta="right" fw={600}>
                  {formatMoneyWhole(s.profit_cents)}
                </Table.Td>
              </Table.Tr>
            </Table.Tbody>
          </Table>
        ))}
      </SimpleGrid>
    </Card>
  );
}

function BalanceSheet({ f }: { f: Finance }) {
  return (
    <Card withBorder>
      <Title order={4} mb="xs">
        Balance sheet
      </Title>
      <Table>
        <Table.Tbody>
          {f.balance_sheet.map((line) => (
            <Table.Tr key={line.account}>
              <Table.Td>{line.label}</Table.Td>
              <Table.Td c="dimmed">{line.kind}</Table.Td>
              <Table.Td className="tst-num" ta="right">
                {formatMoneyWhole(line.amount_cents)}
              </Table.Td>
            </Table.Tr>
          ))}
        </Table.Tbody>
      </Table>
    </Card>
  );
}

function Ageing({
  title,
  rows,
  testId,
}: {
  title: string;
  rows: Finance['wip_ageing'];
  testId: string;
}) {
  return (
    <Card withBorder data-testid={testId}>
      <Title order={4} mb="xs">
        {title}
      </Title>
      <Table>
        <Table.Tbody>
          {rows.map((b) => (
            <Table.Tr key={b.label}>
              <Table.Td>{b.label}</Table.Td>
              <Table.Td c="dimmed">{b.count}</Table.Td>
              <Table.Td className="tst-num" ta="right">
                {formatMoneyWhole(b.amount_cents)}
              </Table.Td>
            </Table.Tr>
          ))}
        </Table.Tbody>
      </Table>
    </Card>
  );
}

function Bills({ slug, bills }: { slug: string; bills: Bill[] }) {
  const respond = useRespondDispute(slug);
  const disputed = bills.filter((b) => b.dispute !== null);
  return (
    <Card withBorder data-testid="bills">
      <Title order={4} mb="xs">
        Open bills ({bills.length})
      </Title>
      {respond.error && (
        <Text c="red" size="sm">
          {respond.error.message}
        </Text>
      )}
      {disputed.length > 0 && (
        <Stack gap="xs" mb="sm" data-testid="disputes">
          {disputed.map((b) => (
            <Group key={b.id} justify="space-between">
              <Text size="sm">
                {b.client} disputes {formatMoneyWhole(b.dispute?.amount_cents ?? 0)} of{' '}
                {formatMoneyWhole(b.billed_cents)} ({b.matter ?? 'flow work'}); answer by{' '}
                {b.dispute?.expires_label}
              </Text>
              <Group gap={4}>
                {(['concede', 'negotiate', 'hold'] as const).map((choice) => (
                  <Button
                    key={choice}
                    size="xs"
                    variant="light"
                    loading={respond.isPending}
                    onClick={() => respond.mutate({ billId: b.id, choice })}
                  >
                    {choice === 'hold'
                      ? 'Hold firm'
                      : choice === 'concede'
                        ? 'Concede'
                        : 'Negotiate'}
                  </Button>
                ))}
              </Group>
            </Group>
          ))}
        </Stack>
      )}
      <Table>
        <Table.Thead>
          <Table.Tr>
            <Table.Th>Client</Table.Th>
            <Table.Th>Matter</Table.Th>
            <Table.Th>Issued</Table.Th>
            <Table.Th ta="right">Age</Table.Th>
            <Table.Th ta="right">Billed</Table.Th>
            <Table.Th ta="right">Outstanding</Table.Th>
          </Table.Tr>
        </Table.Thead>
        <Table.Tbody>
          {bills.slice(0, 50).map((b) => (
            <Table.Tr key={b.id}>
              <Table.Td>{b.client}</Table.Td>
              <Table.Td>{b.matter ?? 'Flow work'}</Table.Td>
              <Table.Td>{b.issued_label}</Table.Td>
              <Table.Td className="tst-num" ta="right">
                {b.age_days} days
              </Table.Td>
              <Table.Td className="tst-num" ta="right">
                {formatMoneyWhole(b.billed_cents)}
              </Table.Td>
              <Table.Td className="tst-num" ta="right">
                {formatMoneyWhole(b.outstanding_cents)}
              </Table.Td>
            </Table.Tr>
          ))}
        </Table.Tbody>
      </Table>
    </Card>
  );
}

export function FinanceScreen() {
  const { slug = '' } = useParams();
  const finance = useFinance(slug);
  const bills = useBills(slug);
  if (!finance.data) return <Text c="dimmed">Loading…</Text>;
  const f = finance.data;
  return (
    <Stack>
      <Title order={2}>Finance</Title>
      <Kpis f={f} />
      <Statements f={f} />
      <SimpleGrid cols={{ base: 1, md: 3 }}>
        <BalanceSheet f={f} />
        <Ageing title="Unbilled WIP by age" rows={f.wip_ageing} testId="wip-ageing" />
        <Ageing title="Receivables by age" rows={f.receivables_ageing} testId="ar-ageing" />
      </SimpleGrid>
      <Bills slug={slug} bills={bills.data ?? []} />
    </Stack>
  );
}
