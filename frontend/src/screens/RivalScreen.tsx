import {
  Alert,
  Badge,
  Button,
  Group,
  Select,
  SimpleGrid,
  Stack,
  Table,
  Text,
  Title,
} from '@mantine/core';
import { useState } from 'react';
import { Link, useParams } from 'react-router';
import { useApproachRival, usePracticeLabels, useRival } from '../lib/api';
import { formatMoneyShort, formatWhole, humanize } from '../lib/format';
import { News } from './MarketScreen';

// A rival firm (spec 10, 16): the press's figures by year, lawyers by practice, its key
// people (names, levels, practices; a met person links to their revealed profile), the
// approach action and its news. Every number is the API's.
export function RivalScreen() {
  const { slug = '', firmId = '0' } = useParams();
  const rival = useRival(slug, Number(firmId));
  const practice = usePracticeLabels(slug);
  const approach = useApproachRival(slug);
  const [target, setTarget] = useState<string | null>(null);
  if (rival.isLoading) return <Text c="dimmed">Loading…</Text>;
  if (rival.error || !rival.data) {
    return <Alert color="red">Could not load the firm: {rival.error?.message}</Alert>;
  }
  const r = rival.data;
  const practices = Array.from(new Set(r.people.map((p) => p.practice)));
  return (
    <Stack gap="lg">
      <div>
        <Group gap="xs">
          <Title order={2} data-testid="rival-name">
            {r.name}
          </Title>
          <Badge variant="light">{r.personality}</Badge>
          {r.status !== 'active' && (
            <Badge color="red" variant="light">
              {humanize(r.status)}
              {r.ended_label ? ` ${r.ended_label}` : ''}
            </Badge>
          )}
        </Group>
        <Text c="dimmed" size="sm">
          {r.hq} · {r.offices} offices · {r.comp} · founded {r.founded_label}
          {r.successor ? ` · now part of ${r.successor}` : ''}
        </Text>
      </div>
      <div className="tst-panel">
        <SimpleGrid cols={{ base: 2, sm: 5 }}>
          <Field label="Revenue">{formatMoneyShort(r.revenue_cents)}</Field>
          <Field label="Lawyers">{formatWhole(r.lawyers)}</Field>
          <Field label="PEP">{formatMoneyShort(r.pep_cents)}</Field>
          <Field label="Money">{r.money}</Field>
          <Field label="Stance">{r.stance}</Field>
        </SimpleGrid>
      </div>
      {r.history.length > 0 && (
        <div>
          <Title order={4} mb="xs">
            By year
          </Title>
          <Table data-testid="rival-history">
            <Table.Thead>
              <Table.Tr>
                <Table.Th>Year</Table.Th>
                <Table.Th>Revenue</Table.Th>
                <Table.Th>Lawyers</Table.Th>
                <Table.Th>Equity partners</Table.Th>
                <Table.Th>PEP</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {r.history.map((h) => (
                <Table.Tr key={h.year}>
                  <Table.Td>{h.year}</Table.Td>
                  <Table.Td className="tst-num">{formatMoneyShort(h.revenue_cents)}</Table.Td>
                  <Table.Td className="tst-num">{formatWhole(h.lawyers)}</Table.Td>
                  <Table.Td className="tst-num">{formatWhole(h.equity_partners)}</Table.Td>
                  <Table.Td className="tst-num">{formatMoneyShort(h.pep_cents)}</Table.Td>
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
        </div>
      )}
      <div>
        <Title order={4} mb="xs">
          Lawyers by practice
        </Title>
        <Text size="sm">
          {r.practices.map((p) => `${p.label} ${formatWhole(p.lawyers)}`).join(' · ')}
        </Text>
      </div>
      <div>
        <Group justify="space-between" mb="xs">
          <Title order={4}>Key people</Title>
          {r.status === 'active' && (
            <Group gap="xs">
              <Select
                size="xs"
                placeholder="Any practice"
                clearable
                data={practices.map((p) => ({ value: p, label: practice(p) }))}
                value={target}
                onChange={setTarget}
              />
              <Button
                size="xs"
                loading={approach.isPending}
                onClick={() => approach.mutate({ firm_id: r.id, practice: target })}
                data-testid="approach-rival"
              >
                Approach
              </Button>
            </Group>
          )}
        </Group>
        {approach.error && <Alert color="red">{approach.error.message}</Alert>}
        {approach.isSuccess && (
          <Alert color="teal" data-testid="approach-done">
            They are now candidates on the{' '}
            <Link to={`/game/${slug}/recruitment`}>Recruitment screen</Link>.
          </Alert>
        )}
        <Table>
          <Table.Tbody>
            {r.people.map((p) => (
              <Table.Tr key={p.id} data-testid="key-person">
                <Table.Td>
                  {p.met ? <Link to={`/game/${slug}/people/${p.id}`}>{p.name}</Link> : p.name}
                  {p.real && (
                    <Badge size="xs" ml="xs" variant="outline">
                      real
                    </Badge>
                  )}
                </Table.Td>
                <Table.Td>{humanize(p.level)}</Table.Td>
                <Table.Td>{practice(p.practice)}</Table.Td>
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
      </div>
      <News news={r.news} slug={slug} />
    </Stack>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <Text size="xs" c="dimmed">
        {label}
      </Text>
      <Text>{children}</Text>
    </div>
  );
}
