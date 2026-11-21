import {
  Alert,
  Badge,
  Button,
  Card,
  Group,
  NumberInput,
  Select,
  SimpleGrid,
  Stack,
  Switch,
  Table,
  Text,
  TextInput,
  Title,
} from '@mantine/core';
import { createColumnHelper, tableFeatures, useTable } from '@tanstack/react-table';
import { useMemo, useState } from 'react';
import { useParams } from 'react-router';
import {
  usePartnership,
  usePartnershipAction,
  type ApproachRow,
  type CandidateRow,
  type LateralRow,
  type Partnership,
  type PartnerRow,
  type Track,
  type VoteRow,
} from '../lib/api';
import { formatBpPercent, formatMoneyWhole, formatRatio, humanize } from '../lib/format';

// The Partnership screen (spec 16; PT-M4): partners (points, comp, contribution, capital,
// a market band and a confidence label), the agreement and its votes, the December round
// (candidates and the comp round), approaches and departures, lateral partners, the revolver
// and the Explain panel for PEP. Every number arrives from the API; this screen only formats
// it and sends one action per button.

type Act = ReturnType<typeof usePartnershipAction>;
const features = tableFeatures({});
const helper = createColumnHelper<typeof features, PartnerRow>();
const pct = (bp: number | null | undefined) =>
  bp === null || bp === undefined ? '—' : formatBpPercent(bp);
const money = (c: number | null | undefined) =>
  c === null || c === undefined ? '—' : formatMoneyWhole(c);
const dollars = (v: string | number) => Math.round(Number(v) * 100);

function Tile(props: { label: string; value: string; note?: string; testId?: string }) {
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

function Header({ p }: { p: Partnership }) {
  const w = p.whip;
  const band = (r: { lo: number; hi: number }) => (r.lo === r.hi ? `${r.lo}` : `${r.lo}–${r.hi}`);
  return (
    <SimpleGrid cols={{ base: 2, md: 6 }}>
      <Tile label="PEP (last year)" value={money(p.last_pep_cents)} testId="kpi-pep" />
      <Tile label="Profit (last year)" value={money(p.last_profit_cents)} />
      <Tile label="Partners' capital" value={money(p.capital_cents)} />
      <Tile label="True-up owed" value={money(p.true_up_owed_cents)} />
      <Tile
        label="Managing partner"
        value={p.mp_name ?? '—'}
        note={p.term_ends_label ? `term ends ${p.term_ends_label}` : 'founding agreement'}
      />
      <Tile
        label="Whip count"
        value={`${band(w.supportive)} / ${band(w.neutral)} / ${band(w.restless)}`}
        note="supportive / neutral / restless"
        testId="whip"
      />
    </SimpleGrid>
  );
}

function ElectionChoice({ p, act }: { p: Partnership; act: Act }) {
  const [successor, setSuccessor] = useState<string | null>(null);
  if (!p.election_choice_pending) return null;
  const options = p.partners
    .filter((x) => x.klass === 'equity' && !x.is_you)
    .map((x) => ({ value: String(x.person_id), label: x.name }));
  return (
    <Alert color="red" title="You lost the election">
      <Group>
        <Button size="xs" onClick={() => act.mutate({ kind: 'election', choice: 'stay' })}>
          Stay as a partner
        </Button>
        <Select size="xs" placeholder="Successor" data={options} onChange={setSuccessor} />
        <Button
          size="xs"
          disabled={!successor}
          onClick={() =>
            act.mutate({ kind: 'election', choice: 'hand_over', successor_id: Number(successor) })
          }
        >
          Hand over and play them
        </Button>
      </Group>
    </Alert>
  );
}

function partnerColumns(p: Partnership, act: Act) {
  const modified = p.comp_system === 'modified_lockstep';
  const committee = p.comp_system === 'committee';
  return [
    helper.display({
      id: 'name',
      header: 'Partner',
      cell: ({ row }) => (
        <>
          {row.original.name}
          {row.original.is_you && (
            <Badge size="xs" ml={6} variant="light">
              You
            </Badge>
          )}
          {row.original.is_mp && (
            <Badge size="xs" ml={6} color="grape" variant="light">
              MP
            </Badge>
          )}
        </>
      ),
    }),
    helper.display({
      id: 'practice',
      header: 'Practice',
      cell: (c) => humanize(c.row.original.practice),
    }),
    helper.display({ id: 'class', header: 'Class', cell: (c) => c.row.original.klass }),
    helper.display({ id: 'points', header: 'Points', cell: (c) => c.row.original.points }),
    helper.display({
      id: 'comp',
      header: 'Comp (last)',
      cell: (c) => <span className="tst-num">{money(c.row.original.comp_last_cents)}</span>,
    }),
    helper.display({
      id: 'projected',
      header: 'Projected',
      cell: (c) => <span className="tst-num">{money(c.row.original.projected_comp_cents)}</span>,
    }),
    helper.display({
      id: 'drawn',
      header: 'Drawn',
      cell: (c) => <span className="tst-num">{money(c.row.original.drawn_ytd_cents)}</span>,
    }),
    helper.display({
      id: 'contribution',
      header: 'Contribution',
      cell: (c) => pct(c.row.original.contribution_bp),
    }),
    helper.display({
      id: 'capital',
      header: 'Capital',
      cell: (c) =>
        `${money(c.row.original.capital_cents)} / ${money(c.row.original.capital_required_cents)}`,
    }),
    helper.display({
      id: 'market',
      header: 'Market band',
      cell: (c) =>
        `${money(c.row.original.market_band.lo)}–${money(c.row.original.market_band.hi)}`,
    }),
    helper.display({
      id: 'confidence',
      header: 'Confidence',
      cell: (c) => {
        const r = c.row.original;
        return r.is_mp ? (
          '—'
        ) : (
          <span title={`about ${r.confidence_range.lo}–${r.confidence_range.hi}`}>
            {r.confidence_label}
          </span>
        );
      },
    }),
    helper.display({
      id: 'guarantee',
      header: 'Guarantee',
      cell: (c) =>
        c.row.original.guarantee_until_label
          ? `${money(c.row.original.guarantee_cents)} to ${c.row.original.guarantee_until_label}`
          : '—',
    }),
    helper.display({
      id: 'actions',
      header: '',
      cell: ({ row }) => {
        const r = row.original;
        if (r.is_you) return null;
        return (
          <Group gap={4} wrap="nowrap">
            <Button
              size="compact-xs"
              variant="light"
              disabled={r.lobbied || act.isPending}
              onClick={() => act.mutate({ kind: 'lobby', person_id: r.person_id })}
            >
              {r.lobbied ? 'Spoken to' : 'Lobby'}
            </Button>
            {p.december && r.klass === 'equity' && (modified || committee) && (
              <Select
                size="xs"
                w={110}
                aria-label={`Comp round for ${r.name}`}
                value={String(modified ? r.gate_steps : r.adjust_bp)}
                data={
                  modified
                    ? ['-1', '0', '1', '2'].map((v) => ({ value: v, label: `${v} steps` }))
                    : ['-3000', '-1500', '0', '1500', '3000'].map((v) => ({
                        value: v,
                        label: `${Number(v) / 100}%`,
                      }))
                }
                onChange={(v) =>
                  v !== null &&
                  act.mutate({
                    kind: 'comp_round',
                    person_id: r.person_id,
                    gate_steps: modified ? Number(v) : 0,
                    adjust_bp: modified ? 0 : Number(v),
                  })
                }
              />
            )}
          </Group>
        );
      },
    }),
  ];
}

function Partners({ p, act }: { p: Partnership; act: Act }) {
  // eslint-disable-next-line react-hooks/exhaustive-deps
  const columns = useMemo(() => partnerColumns(p, act), [p.comp_system, p.december, act.isPending]);
  const table = useTable({ features, columns, data: p.partners });
  return (
    <Card withBorder>
      <Title order={4} mb="xs">
        Partners
      </Title>
      <div className="tst-table-wrap">
        <Table striped highlightOnHover data-testid="partners-table">
          <Table.Thead>
            {table.getHeaderGroups().map((group) => (
              <Table.Tr key={group.id}>
                {group.headers.map((header) => (
                  <Table.Th key={header.id}>
                    {header.isPlaceholder ? null : <table.FlexRender header={header} />}
                  </Table.Th>
                ))}
              </Table.Tr>
            ))}
          </Table.Thead>
          <Table.Tbody>
            {table.getRowModel().rows.map((row) => (
              <Table.Tr key={row.id}>
                {row.getAllCells().map((cell) => (
                  <Table.Td key={cell.id}>
                    <table.FlexRender cell={cell} />
                  </Table.Td>
                ))}
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
      </div>
    </Card>
  );
}

function Explain({ p }: { p: Partnership }) {
  const e = p.explain;
  return (
    <Card withBorder data-testid="explain">
      <Title order={4} mb="xs">
        Explain: PEP = RPL × margin × leverage
      </Title>
      <Text size="sm">
        PEP {money(e.pep_cents)} = RPL {money(e.rpl_cents)} × margin {pct(e.margin_bp)} × leverage{' '}
        {e.leverage === null ? '—' : formatRatio(e.leverage)}
      </Text>
      <Text size="sm" c="dimmed">
        RPL = {e.hours_per_lawyer === null ? '—' : Math.round(e.hours_per_lawyer)} hours per lawyer
        × {money(e.average_rate_cents)} an hour × realisation {pct(e.realisation_bp)} × collection{' '}
        {pct(e.collection_bp)} (trailing twelve months; {e.lawyers.toFixed(1)} lawyers,{' '}
        {e.equity_partners.toFixed(1)} equity partners)
      </Text>
    </Card>
  );
}

function Votes({ p, act }: { p: Partnership; act: Act }) {
  if (p.votes.length === 0) return null;
  return (
    <Card withBorder>
      <Title order={4} mb="xs">
        Votes
      </Title>
      <Table data-testid="votes">
        <Table.Thead>
          <Table.Tr>
            <Table.Th>Motion</Table.Th>
            <Table.Th>Status</Table.Th>
            <Table.Th>For (predicted or cast)</Table.Th>
            <Table.Th>Needed</Table.Th>
            <Table.Th />
          </Table.Tr>
        </Table.Thead>
        <Table.Tbody>
          {p.votes.map((v: VoteRow) => (
            <Table.Tr key={v.vote_id} data-testid={`vote-${v.kind}`}>
              <Table.Td>{v.title}</Table.Td>
              <Table.Td>{v.status}</Table.Td>
              <Table.Td>
                {v.predicted_yes
                  ? `${v.predicted_yes.lo}–${v.predicted_yes.hi} of ${v.total_weight}`
                  : `${v.yes_weight} for, ${v.no_weight} against`}
              </Table.Td>
              <Table.Td>{v.status === 'open' ? v.needed_weight.toFixed(1) : ''}</Table.Td>
              <Table.Td>
                {v.status === 'open' && (
                  <Button
                    size="compact-xs"
                    variant="subtle"
                    onClick={() => act.mutate({ kind: 'withdraw', vote_id: v.vote_id })}
                  >
                    Withdraw
                  </Button>
                )}
              </Table.Td>
            </Table.Tr>
          ))}
        </Table.Tbody>
      </Table>
      <Text size="xs" c="dimmed">
        Votes are counted when you press Continue.
      </Text>
    </Card>
  );
}

function Agreement({ p, act }: { p: Partnership; act: Act }) {
  const [term, setTerm] = useState<string | null>(null);
  const [value, setValue] = useState('');
  const [call, setCall] = useState<string | number>(100000);
  const parse = (t: string, v: string): string | number | boolean => {
    const current = p.agreement.find((x) => x.term === t)?.value;
    if (typeof current === 'boolean') return v === 'true' || v === 'yes';
    if (typeof current === 'number') return Number(v);
    return v;
  };
  return (
    <Card withBorder data-testid="agreement">
      <Title order={4} mb="xs">
        The partnership agreement
      </Title>
      <Table>
        <Table.Tbody>
          {p.agreement.map((t) => (
            <Table.Tr key={t.term}>
              <Table.Td>{humanize(t.term)}</Table.Td>
              <Table.Td>{String(t.value)}</Table.Td>
            </Table.Tr>
          ))}
        </Table.Tbody>
      </Table>
      <Group mt="sm" align="end">
        <Select
          label="Change a term"
          size="xs"
          data={p.agreement.map((t) => ({ value: t.term, label: humanize(t.term) }))}
          value={term}
          onChange={setTerm}
        />
        <TextInput
          label="New value"
          size="xs"
          value={value}
          onChange={(e) => setValue(e.currentTarget.value)}
        />
        <Button
          size="xs"
          disabled={!term || !value}
          onClick={() => term && act.mutate({ kind: 'terms', term, value: parse(term, value) })}
        >
          Put to a vote
        </Button>
      </Group>
      <Group mt="sm" align="end">
        <NumberInput label="Capital call ($)" size="xs" value={call} onChange={setCall} min={1} />
        <Button
          size="xs"
          onClick={() => act.mutate({ kind: 'capital_call', amount_cents: dollars(call) })}
        >
          Call capital
        </Button>
        <Switch
          label="Draws suspended"
          checked={p.draws_suspended}
          onChange={(e) => act.mutate({ kind: 'draws', suspended: e.currentTarget.checked })}
        />
      </Group>
    </Card>
  );
}

function Candidates({ p, act }: { p: Partnership; act: Act }) {
  if (p.candidates.length === 0) return null;
  return (
    <Card withBorder>
      <Title order={4} mb="xs">
        The December vote {p.december ? '' : '(proposals open in December)'}
      </Title>
      <Table data-testid="candidates">
        <Table.Thead>
          <Table.Tr>
            <Table.Th>Candidate</Table.Th>
            <Table.Th>Level</Table.Th>
            <Table.Th>Sponsor</Table.Th>
            <Table.Th>Rating</Table.Th>
            <Table.Th>Business development</Table.Th>
            <Table.Th>Practice need</Table.Th>
            <Table.Th>Proposal</Table.Th>
          </Table.Tr>
        </Table.Thead>
        <Table.Tbody>
          {p.candidates.map((c: CandidateRow) => (
            <Table.Tr key={c.person_id}>
              <Table.Td>
                {c.name}
                {c.moving_on_label && (
                  <Text size="xs" c="red">
                    told to move on: leaves by {c.moving_on_label}
                  </Text>
                )}
              </Table.Td>
              <Table.Td>{humanize(c.level)}</Table.Td>
              <Table.Td>{c.sponsor_name ?? '—'}</Table.Td>
              <Table.Td>{c.rating}</Table.Td>
              <Table.Td>
                {c.business_development.lo}–{c.business_development.hi}
              </Table.Td>
              <Table.Td>{pct(c.practice_need_bp)}</Table.Td>
              <Table.Td>
                {c.proposed ? (
                  humanize(c.proposed)
                ) : (
                  <Group gap={4}>
                    {c.tracks.map((t) => (
                      <Button
                        key={t}
                        size="compact-xs"
                        variant="light"
                        disabled={!p.december}
                        data-testid={`propose-${c.person_id}-${t}`}
                        onClick={() =>
                          act.mutate({ kind: 'propose', person_id: c.person_id, track: t as Track })
                        }
                      >
                        {humanize(t)}
                      </Button>
                    ))}
                  </Group>
                )}
              </Table.Td>
            </Table.Tr>
          ))}
        </Table.Tbody>
      </Table>
    </Card>
  );
}

function Approaches({ p, act }: { p: Partnership; act: Act }) {
  const [comp, setComp] = useState<Record<number, string | number>>({});
  return (
    <Card withBorder data-testid="approaches">
      <Title order={4} mb="xs">
        Approaches and departures
      </Title>
      {p.approaches.length === 0 && p.departures.length === 0 && (
        <Text c="dimmed" size="sm">
          No approaches or departures.
        </Text>
      )}
      <Stack gap="xs">
        {p.approaches.map((a: ApproachRow) => (
          <Group key={a.approach_id} data-testid={`approach-${a.approach_id}`}>
            <Text size="sm">
              {a.suitor} offers {a.name} {money(a.offer_comp_cents)} a year ({a.guarantee_years}{' '}
              years guaranteed); answer by {a.respond_by_label}. {a.status}, {a.stay_label}.
            </Text>
            {(a.status === 'open' || a.status === 'countered') && (
              <>
                <NumberInput
                  size="xs"
                  w={140}
                  aria-label={`Counter for ${a.name} ($ a year more)`}
                  value={comp[a.approach_id] ?? 100000}
                  onChange={(v) => setComp({ ...comp, [a.approach_id]: v })}
                />
                <Button
                  size="xs"
                  data-testid={`counter-${a.approach_id}`}
                  onClick={() =>
                    act.mutate({
                      kind: 'counter',
                      approach_id: a.approach_id,
                      comp_cents: dollars(comp[a.approach_id] ?? 100000),
                      guarantee_years: 1,
                    })
                  }
                >
                  Counter
                </Button>
              </>
            )}
          </Group>
        ))}
        {p.departures.map((d) => (
          <Text key={`${d.person_id}-${d.label}`} size="sm" data-testid="departure">
            {d.label}: {d.name} ({humanize(d.practice)}) left for {d.destination ?? 'outside'} (
            {humanize(d.reason)}); leaves {d.leave_label}; {d.clients_following} clients following.
          </Text>
        ))}
      </Stack>
    </Card>
  );
}

function Laterals({ p, act }: { p: Partnership; act: Act }) {
  const [practice, setPractice] = useState<string | null>(null);
  return (
    <Card withBorder data-testid="laterals">
      <Title order={4} mb="xs">
        Lateral partners
      </Title>
      <Group align="end" mb="sm">
        <Select
          size="xs"
          label="Practice"
          data={p.practices.map((x) => ({ value: x.key, label: x.label }))}
          value={practice}
          onChange={setPractice}
        />
        <Button
          size="xs"
          disabled={!practice}
          onClick={() => practice && act.mutate({ kind: 'lateral_search', practice })}
        >
          Engage a recruiter
        </Button>
      </Group>
      <Table>
        <Table.Tbody>
          {p.laterals.map((c: LateralRow) => (
            <Table.Tr key={c.person_id}>
              <Table.Td>
                {c.name} ({humanize(c.practice)})
              </Table.Td>
              <Table.Td>
                book {money(c.book.lo)}–{money(c.book.hi)}
                {c.diligence && ` · ${c.clients.length} clients, ${c.conflicts} conflicts`}
              </Table.Td>
              <Table.Td>
                asks {money(c.ask_cents)}, {c.guarantee_ask_years} years guaranteed
              </Table.Td>
              <Table.Td>{c.status}</Table.Td>
              <Table.Td>
                {c.status === 'open' && (
                  <Group gap={4}>
                    {!c.diligence && (
                      <Button
                        size="compact-xs"
                        variant="light"
                        onClick={() => act.mutate({ kind: 'diligence', person_id: c.person_id })}
                      >
                        Diligence
                      </Button>
                    )}
                    <Button
                      size="compact-xs"
                      onClick={() =>
                        act.mutate({
                          kind: 'lateral_offer',
                          person_id: c.person_id,
                          comp_cents: c.ask_cents,
                          guarantee_years: c.guarantee_ask_years,
                          equity: true,
                        })
                      }
                    >
                      Offer the ask
                    </Button>
                  </Group>
                )}
              </Table.Td>
            </Table.Tr>
          ))}
        </Table.Tbody>
      </Table>
    </Card>
  );
}

export function RevolverCard({ p, act }: { p: Partnership; act?: Act }) {
  const r = p.revolver;
  return (
    <Card withBorder data-testid="revolver">
      <Title order={4} mb="xs">
        Revolver {r.called && <Badge color="red">called</Badge>}
      </Title>
      <Text size="sm">
        Drawn {money(r.drawn_cents)} of a {money(r.facility_cents)} facility; headroom{' '}
        {money(r.headroom_cents)}; {pct(r.rate_bp)} a year.
        {r.breach_months > 0 && ` Covenant breached for ${r.breach_months} months.`}
      </Text>
      {r.covenants.map((c) => (
        <Text key={c.name} size="sm" c={c.holds ? (c.near ? 'yellow' : undefined) : 'red'}>
          {humanize(c.name)}: {money(c.value_cents)} {c.floor ? 'at least' : 'at most'}{' '}
          {money(c.limit_cents)}
        </Text>
      ))}
      {r.forecast && (
        <Text size="sm" c="orange" data-testid="cfo-forecast">
          Forecast: on the last months&apos; trend the {r.forecast.covenant} covenant breaks in
          about {r.forecast.months} months ({money(r.forecast.drawn_cents)} drawn by then).
        </Text>
      )}
      {act && r.drawn_cents > 0 && (
        <Button
          mt="xs"
          size="xs"
          variant="light"
          onClick={() =>
            act.mutate({
              kind: 'repay',
              amount_cents: Math.min(r.drawn_cents, Math.max(0, p.cash_cents)),
            })
          }
        >
          Repay from cash
        </Button>
      )}
    </Card>
  );
}

export function PartnershipScreen() {
  const { slug = '' } = useParams();
  const query = usePartnership(slug);
  const act = usePartnershipAction(slug);
  const p = query.data;
  return (
    <Stack>
      <Title order={2}>Partnership</Title>
      {act.error && <Alert color="red">{act.error.message}</Alert>}
      {!p ? (
        <Text c="dimmed">Loading…</Text>
      ) : (
        <>
          <Header p={p} />
          <ElectionChoice p={p} act={act} />
          {!p.you_are_mp && (
            <Alert color="yellow">
              You are not managing partner: your practice and your votes are yours, the firm's
              decisions are not.
            </Alert>
          )}
          <Partners p={p} act={act} />
          <Explain p={p} />
          <Votes p={p} act={act} />
          <Candidates p={p} act={act} />
          <SimpleGrid cols={{ base: 1, md: 2 }}>
            <Approaches p={p} act={act} />
            <RevolverCard p={p} act={act} />
          </SimpleGrid>
          <Laterals p={p} act={act} />
          <Agreement p={p} act={act} />
        </>
      )}
    </Stack>
  );
}
