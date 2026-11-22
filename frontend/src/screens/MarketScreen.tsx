import { RunBy } from '../components/RunBy';
import {
  Alert,
  Badge,
  Button,
  Checkbox,
  Group,
  MultiSelect,
  Stack,
  Table,
  Text,
  Title,
} from '@mantine/core';
import { createColumnHelper, useTable } from '@tanstack/react-table';
import { useMemo, useState } from 'react';
import { Link, useParams } from 'react-router';
import { DataTable } from '../components/DataTable';
import { useTableViews } from '../hooks/useTableViews';
import {
  useApproachFreeAgents,
  useCounterApproach,
  useMarket,
  usePeople,
  usePitchRfp,
  usePracticeLabels,
  type MarketNews,
  type Rfp,
  type RivalRow,
} from '../lib/api';
import { formatMoneyShort, formatMoneyWhole, formatWhole, humanize } from '../lib/format';
import { gameTableFeatures, type GameTableFeatures } from '../lib/table';

// Market (spec 10, 16): rival firms with their personality, money and stance labels and the
// press's figures; the firm's RFPs with the pitch form; rivals' approaches to the firm's
// people with Counter; the market's news. Every number is the API's.
const helper = createColumnHelper<GameTableFeatures, RivalRow>();
const EMPTY: RivalRow[] = [];
const MONEY_COLOR = { strong: 'teal', steady: 'gray', strained: 'red' } as const;
const STANCE_COLOR = { neutral: 'gray', wary: 'yellow', hostile: 'red' } as const;

export function MarketScreen() {
  const { slug = '' } = useParams();
  const market = useMarket(slug);
  const columns = useMemo(
    () =>
      helper.columns([
        helper.accessor('name', {
          header: 'Firm',
          sortFn: 'alphanumeric',
          cell: ({ row }) => (
            <Link to={`/game/${slug}/market/rivals/${row.original.id}`} data-testid="rival-link">
              {row.original.name}
            </Link>
          ),
        }),
        helper.accessor('personality', { header: 'Personality', sortFn: 'alphanumeric' }),
        helper.accessor('revenue_cents', {
          header: 'Revenue',
          sortFn: 'basic',
          cell: ({ getValue }) => <span className="tst-num">{formatMoneyShort(getValue())}</span>,
        }),
        helper.accessor('lawyers', {
          header: 'Lawyers',
          sortFn: 'basic',
          cell: ({ getValue }) => <span className="tst-num">{formatWhole(getValue())}</span>,
        }),
        helper.accessor('pep_cents', {
          header: 'PEP',
          sortFn: 'basic',
          cell: ({ getValue }) => <span className="tst-num">{formatMoneyShort(getValue())}</span>,
        }),
        helper.accessor('money', {
          header: 'Money',
          sortFn: 'alphanumeric',
          cell: ({ getValue }) => (
            <Badge
              size="sm"
              variant="light"
              color={MONEY_COLOR[getValue() as keyof typeof MONEY_COLOR] ?? 'gray'}
            >
              {getValue()}
            </Badge>
          ),
        }),
        helper.accessor('stance', {
          header: 'Stance',
          sortFn: 'alphanumeric',
          cell: ({ getValue }) => (
            <Badge
              size="sm"
              variant="light"
              color={STANCE_COLOR[getValue() as keyof typeof STANCE_COLOR] ?? 'gray'}
            >
              {getValue()}
            </Badge>
          ),
        }),
        helper.accessor('offices', {
          header: 'Offices',
          sortFn: 'basic',
          cell: ({ getValue }) => <span className="tst-num">{getValue()}</span>,
        }),
        helper.accessor('on_panels', {
          header: 'Panels',
          sortFn: 'basic',
          cell: ({ getValue }) => <span className="tst-num">{getValue()}</span>,
        }),
        helper.accessor('kind', {
          header: 'Kind',
          sortFn: 'alphanumeric',
          cell: ({ getValue }) => humanize(getValue()),
        }),
      ]),
    [slug],
  );
  const views = useTableViews('market', {
    sorting: [{ id: 'revenue_cents', desc: true }],
    columnVisibility: {},
    columnOrder: [],
  });
  const table = useTable({
    features: gameTableFeatures,
    columns,
    data: market.data?.rivals ?? EMPTY,
    getRowId: (r) => String(r.id),
    ...views.tableProps,
  });
  if (market.error)
    return <Alert color="red">Could not load the market: {market.error.message}</Alert>;
  const m = market.data;
  return (
    <Stack gap="lg">
      <Title order={2}>Market</Title>
      <RunBy slug={slug} areas={['bd']} />
      {m && <Approaches slug={slug} approaches={m.approaches} />}
      {m && <Rfps slug={slug} rfps={m.rfps} claims={m.claims} />}
      <div>
        <Title order={4} mb="xs">
          Rival firms
        </Title>
        {market.isLoading ? (
          <Text c="dimmed">Loading…</Text>
        ) : (
          <DataTable
            views={views}
            table={table}
            label="Rival firms"
            rowTestId="rival-row"
            empty="No rivals."
          />
        )}
      </div>
      {m && <FreeAgents slug={slug} count={m.free_agents} />}
      {m && <News news={m.news} slug={slug} />}
    </Stack>
  );
}

function Approaches({ slug, approaches }: { slug: string; approaches: MarketView['approaches'] }) {
  const counter = useCounterApproach(slug);
  if (approaches.length === 0) return null;
  return (
    <div className="tst-panel" data-testid="approaches">
      <Title order={4} mb="xs">
        Approaches to our people
      </Title>
      {counter.error && <Alert color="red">{counter.error.message}</Alert>}
      <Table>
        <Table.Tbody>
          {approaches.map((a) => (
            <Table.Tr key={a.id} data-testid="approach-row">
              <Table.Td>
                <Link to={`/game/${slug}/people/${a.person.id}`}>{a.person.name}</Link>
              </Table.Td>
              <Table.Td>
                <Link to={`/game/${slug}/market/rivals/${a.firm.id}`}>{a.firm.name}</Link>
              </Table.Td>
              <Table.Td className="tst-num">{formatMoneyWhole(a.offer_cents)} a year</Table.Td>
              <Table.Td>{a.odds}</Table.Td>
              <Table.Td>
                <Button size="xs" loading={counter.isPending} onClick={() => counter.mutate(a.id)}>
                  Counter
                </Button>
              </Table.Td>
            </Table.Tr>
          ))}
        </Table.Tbody>
      </Table>
    </div>
  );
}

type MarketView = NonNullable<ReturnType<typeof useMarket>['data']>;

function Rfps({ slug, rfps, claims }: { slug: string; rfps: Rfp[]; claims: string[] }) {
  const practice = usePracticeLabels(slug);
  if (rfps.length === 0) {
    return (
      <Text c="dimmed" size="sm" data-testid="no-rfps">
        No RFPs the firm is invited to.
      </Text>
    );
  }
  return (
    <div className="tst-panel">
      <Title order={4} mb="xs">
        RFPs and panel reviews
      </Title>
      <Stack gap="sm">
        {rfps.map((r) => (
          <div key={r.id} data-testid="rfp-row">
            <Group gap="xs">
              <Link to={`/game/${slug}/clients/${r.client.id}`}>{r.client.name}</Link>
              <Badge size="sm" variant="light">
                {r.kind === 'panel' ? 'Panel review' : 'Matter RFP'}
              </Badge>
              {r.incumbent && (
                <Badge size="sm" variant="light" color="teal">
                  Incumbent
                </Badge>
              )}
              {r.won === true && <Badge color="teal">Won</Badge>}
              {r.won === false && <Badge color="red">Lost</Badge>}
              <Text size="sm" c="dimmed">
                {r.practices.map(practice).join(', ')} · award {r.award_label} · {r.seats} seat
                {r.seats === 1 ? '' : 's'}
              </Text>
            </Group>
            <Text size="xs" c="dimmed">
              Contenders: {r.contenders.join(' · ')}
            </Text>
            {r.status === 'open' && !r.pitched && <PitchForm slug={slug} rfp={r} claims={claims} />}
            {r.pitched && (
              <Text size="sm">
                Pitched with {r.team.map((t) => t.name).join(', ')}
                {r.claims.length > 0 ? `; claims: ${r.claims.map(humanize).join(', ')}` : ''}
              </Text>
            )}
          </div>
        ))}
      </Stack>
    </div>
  );
}

function PitchForm({ slug, rfp, claims }: { slug: string; rfp: Rfp; claims: string[] }) {
  const people = usePeople(slug);
  const pitch = usePitchRfp(slug);
  const [team, setTeam] = useState<string[]>([]);
  const [chosen, setChosen] = useState<string[]>([]);
  const options = (people.data ?? [])
    .filter((p) => p.own_firm && p.kind === 'lawyer')
    .map((p) => ({ value: String(p.id), label: `${p.name} (${p.role_label})` }));
  return (
    <Group gap="xs" align="end" mt={4}>
      <MultiSelect
        size="xs"
        label="Pitch team (lead first)"
        data={options}
        value={team}
        onChange={setTeam}
        maxValues={6}
        w={320}
        data-testid="pitch-team"
      />
      <Checkbox.Group value={chosen} onChange={setChosen} label="Claims" size="xs">
        <Group gap="xs">
          {claims.map((c) => (
            <Checkbox key={c} value={c} label={humanize(c)} />
          ))}
        </Group>
      </Checkbox.Group>
      <Button
        size="xs"
        disabled={team.length === 0}
        loading={pitch.isPending}
        onClick={() => pitch.mutate({ rfp_id: rfp.id, team: team.map(Number), claims: chosen })}
        data-testid="pitch-button"
      >
        Pitch
      </Button>
      {pitch.error && (
        <Text c="red" size="xs">
          {pitch.error.message}
        </Text>
      )}
    </Group>
  );
}

function FreeAgents({ slug, count }: { slug: string; count: number }) {
  const approach = useApproachFreeAgents(slug);
  if (count === 0) return null;
  return (
    <Group>
      <Text size="sm">{count} people from firms that have closed are looking for work.</Text>
      <Button
        size="xs"
        variant="light"
        loading={approach.isPending}
        onClick={() => approach.mutate(undefined)}
      >
        Approach them
      </Button>
      {approach.error && (
        <Text c="red" size="xs">
          {approach.error.message}
        </Text>
      )}
    </Group>
  );
}

export function News({ news, slug }: { news: MarketNews[]; slug: string }) {
  return (
    <div>
      <Title order={4} mb="xs">
        Market news
      </Title>
      {news.length === 0 ? (
        <Text c="dimmed" size="sm">
          Nothing yet.
        </Text>
      ) : (
        <Stack gap={2} data-testid="market-news">
          {news.slice(0, 60).map((n, i) => (
            <Text size="sm" key={`${n.turn}-${i}`}>
              <span className="tst-muted">{n.date_label}</span>{' '}
              <Link to={`/game/${slug}/market/rivals/${n.firm.id}`}>{n.text}</Link>
            </Text>
          ))}
        </Stack>
      )}
    </div>
  );
}
