import {
  Alert,
  Badge,
  Button,
  Card,
  Group,
  NumberInput,
  SegmentedControl,
  Select,
  SimpleGrid,
  Stack,
  Table,
  Text,
  Title,
} from '@mantine/core';
import { createColumnHelper, useTable } from '@tanstack/react-table';
import { useState } from 'react';
import { useParams } from 'react-router';
import { DataTable } from '../components/DataTable';
import { formatMoney, formatMoneyShort, formatWhole, humanize } from '../lib/format';
import {
  useAnswerApproach,
  useApproachFirm,
  useCommissionDiligence,
  useMergers,
  usePutTerms,
  useWalkAway,
  type MergerDeal,
  type MergerIntegration,
  type MergerTarget,
  type Mergers,
} from '../lib/mergersApi';
import { gameTableFeatures, type GameTableFeatures } from '../lib/table';

// Mergers and the verein (spec 8.8; PT-M13): the target list with its fit, talks and due
// diligence, terms and the two partnerships' votes, conflicts clearance, integration's progress,
// the verein and the exit. Every number is the API's; hidden values never reach this screen.

const num = (v: number | string) => <span className="tst-num">{v}</span>;
const range = (lo: number, hi: number, money = false) =>
  money ? `${formatMoneyShort(lo)}–${formatMoneyShort(hi)}` : `${lo}–${hi}`;

const targetHelper = createColumnHelper<GameTableFeatures, MergerTarget>();
const targetColumns = targetHelper.columns([
  targetHelper.accessor('name', { header: 'Firm', sortFn: 'alphanumeric' }),
  targetHelper.accessor('city', { header: 'HQ' }),
  targetHelper.accessor('lawyers', {
    header: 'Lawyers',
    sortFn: 'basic',
    cell: (c) => num(formatWhole(c.getValue())),
  }),
  targetHelper.accessor('revenue_cents', {
    header: 'Revenue',
    sortFn: 'basic',
    cell: (c) => num(formatMoneyShort(c.getValue())),
  }),
  targetHelper.accessor('pep_cents', {
    header: 'PEP',
    sortFn: 'basic',
    cell: (c) => num(formatMoneyShort(c.getValue())),
  }),
  targetHelper.accessor((r) => r.practices.map(humanize).join(', '), {
    id: 'practices',
    header: 'Largest practices',
  }),
  targetHelper.accessor('complement_pct', {
    header: 'Complement',
    sortFn: 'basic',
    cell: (c) => num(`${c.getValue()}%`),
  }),
  targetHelper.accessor('rate_pct', { header: 'Card', cell: (c) => num(`${c.getValue()}%`) }),
  targetHelper.accessor('clash_pct', { header: 'Clash', cell: (c) => num(`${c.getValue()}%`) }),
  targetHelper.accessor('fair_share_pct', {
    header: 'Fair share',
    sortFn: 'basic',
    cell: (c) => num(`${c.getValue()}%`),
  }),
  targetHelper.accessor((r) => (r.integrable ? 'merger or verein' : 'verein'), {
    id: 'form',
    header: 'Possible',
  }),
]);

function TargetsPanel({ m, slug }: { m: Mergers; slug: string }) {
  const approach = useApproachFirm(slug);
  const [key, setKey] = useState<string | null>(null);
  const [form, setForm] = useState<'merger' | 'verein'>('merger');
  const table = useTable({
    features: gameTableFeatures,
    columns: targetColumns,
    data: m.targets,
    getRowId: (r) => r.key,
  });
  const chosen = m.targets.find((t) => t.key === key);
  const blocked = chosen ? (form === 'merger' ? chosen.merger_blocked : chosen.verein_blocked) : '';
  return (
    <div className="tst-panel" data-testid="targets">
      <h3 className="tst-ptitle">Targets</h3>
      <Text size="xs" c="dimmed" mb="xs">
        Public figures. Complement: the share of a firm&apos;s lawyers in practices you lack. Fair
        share: your partners&apos; share of the two profit pools. Firms of more than {m.max_lawyers}{' '}
        lawyers, or outside the modelled cities, can only join a verein.
      </Text>
      <Group align="end" mb="sm" wrap="wrap">
        <Select
          label="Firm"
          searchable
          data={m.targets.map((t) => ({ value: t.key, label: `${t.name} (${t.city})` }))}
          value={key}
          onChange={setKey}
          w={340}
          data-testid="approach-firm"
        />
        <SegmentedControl
          data={[
            { value: 'merger', label: 'Merger' },
            { value: 'verein', label: 'Verein' },
          ]}
          value={form}
          onChange={(v) => setForm(v as 'merger' | 'verein')}
          data-testid="approach-form"
        />
        <Button
          disabled={!key || !m.is_mp || Boolean(blocked)}
          loading={approach.isPending}
          onClick={() => key && approach.mutate({ rival_key: key, form })}
          data-testid="approach"
        >
          Approach ({m.costs.merger_approach} energy)
        </Button>
      </Group>
      {blocked && (
        <Text size="sm" c="orange" mb="xs">
          {chosen?.name}: {blocked}
        </Text>
      )}
      {approach.error && (
        <Alert color="red" mb="xs">
          {String(approach.error.message)}
        </Alert>
      )}
      <DataTable table={table} label="Targets" rowTestId="target-row" />
    </div>
  );
}

function RevealCard({ d, slug, m }: { d: MergerDeal; slug: string; m: Mergers }) {
  const diligence = useCommissionDiligence(slug);
  const r = d.reveal;
  if (!r) return null;
  return (
    <Card withBorder data-testid="diligence">
      <Group justify="space-between">
        <Title order={5}>
          Due diligence: level {r.level} of {r.max_level}
        </Title>
        <Button
          size="xs"
          disabled={d.diligence_running || r.level >= r.max_level || !m.is_mp}
          loading={diligence.isPending}
          onClick={() => diligence.mutate(d.id)}
          data-testid="commission-diligence"
        >
          {d.diligence_running
            ? 'Advisers at work'
            : `Commission a level (${formatMoneyShort(r.next_fee_cents)}, ${m.costs.merger_diligence} energy)`}
        </Button>
      </Group>
      <Table mt="xs">
        <Table.Tbody>
          <Table.Tr>
            <Table.Td>Revenue / profit (a year)</Table.Td>
            <Table.Td className="tst-num">
              {formatMoneyShort(r.revenue_cents)} / {formatMoneyShort(r.profit_cents)}
            </Table.Td>
          </Table.Tr>
          <Table.Tr>
            <Table.Td>Lawyers / equity partners / PEP</Table.Td>
            <Table.Td className="tst-num">
              {r.lawyers} / {r.equity_partners} / {formatMoneyShort(r.pep_cents)}
            </Table.Td>
          </Table.Tr>
          <Table.Tr>
            <Table.Td>WIP / receivables / cash / revolver</Table.Td>
            <Table.Td className="tst-num">
              {r.exact
                ? `${formatMoneyShort(r.wip_cents ?? 0)} / ${formatMoneyShort(r.receivables_cents ?? 0)} / ${formatMoneyShort(r.cash_cents ?? 0)} / ${formatMoneyShort(r.revolver_cents ?? 0)}`
                : 'after a level of diligence'}
            </Table.Td>
          </Table.Tr>
          <Table.Tr>
            <Table.Td>Partners&apos; quality (ability)</Table.Td>
            <Table.Td className="tst-num">
              {range(r.partner_ability.lo, r.partner_ability.hi)}
            </Table.Td>
          </Table.Tr>
          <Table.Tr>
            <Table.Td>Retired partners&apos; annuities</Table.Td>
            <Table.Td className="tst-num">
              {range(r.annuities_cents.lo, r.annuities_cents.hi, true)}
            </Table.Td>
          </Table.Tr>
          <Table.Tr>
            <Table.Td>Lease obligations</Table.Td>
            <Table.Td className="tst-num">
              {range(r.leases_cents.lo, r.leases_cents.hi, true)}
            </Table.Td>
          </Table.Tr>
          <Table.Tr>
            <Table.Td>Conflicts with your clients</Table.Td>
            <Table.Td className="tst-num">
              {range(r.conflicts.lo, r.conflicts.hi)} (book of {r.book_clients} clients)
            </Table.Td>
          </Table.Tr>
        </Table.Tbody>
      </Table>
    </Card>
  );
}

function TermsForm({ d, slug, m }: { d: MergerDeal; slug: string; m: Mergers }) {
  const put = usePutTerms(slug);
  const start = d.counter_share_pct ?? d.terms?.our_share_pct ?? 50;
  const [share, setShare] = useState<number>(start);
  const [name, setName] = useState<string>(d.terms?.name ?? 'combined');
  const [mp, setMp] = useState<string>(d.terms?.mp ?? 'ours');
  const [comp, setComp] = useState<string>(d.terms?.comp_system ?? 'modified_lockstep');
  const [rates, setRates] = useState<string>(d.terms?.rates ?? 'blend');
  const verein = d.form === 'verein';
  return (
    <Card withBorder data-testid="terms-form">
      <Title order={5}>{verein ? 'Join the verein' : 'Terms'}</Title>
      {!verein && (
        <Group align="end" wrap="wrap" mt="xs">
          <NumberInput
            label="Your partners' share of the pool (%)"
            min={5}
            max={95}
            value={share}
            onChange={(v) => setShare(Number(v))}
            w={220}
            data-testid="terms-share"
          />
          <Select
            label="Name"
            data={[
              { value: 'ours', label: 'Ours' },
              { value: 'combined', label: 'Combined' },
              { value: 'theirs', label: 'Theirs' },
            ]}
            value={name}
            onChange={(v) => setName(v ?? 'combined')}
            w={130}
          />
          <Select
            label="Managing partner"
            data={[
              { value: 'ours', label: 'You' },
              { value: 'theirs', label: 'Theirs' },
            ]}
            value={mp}
            onChange={(v) => setMp(v ?? 'ours')}
            w={150}
          />
          <Select
            label="Comp system"
            data={m.comp_systems.map((s) => ({ value: s, label: humanize(s) }))}
            value={comp}
            onChange={(v) => setComp(v ?? comp)}
            w={190}
          />
          <Select
            label="Rate card"
            data={[
              { value: 'ours', label: 'Ours' },
              { value: 'theirs', label: 'Theirs' },
              { value: 'higher', label: 'The higher' },
              { value: 'blend', label: 'A blend' },
            ]}
            value={rates}
            onChange={(v) => setRates(v ?? 'blend')}
            w={130}
          />
        </Group>
      )}
      {!verein && (share < m.absorbed_below_pct || (name === 'theirs' && mp === 'theirs')) && (
        <Text size="sm" c="orange" mt="xs" data-testid="absorption-warning">
          On these terms your firm is absorbed (their name and managing partner, or under{' '}
          {m.absorbed_below_pct}% of the pool): if both partnerships pass it, the campaign ends.
        </Text>
      )}
      <Button
        mt="sm"
        disabled={!m.is_mp || d.diligence_running}
        loading={put.isPending}
        onClick={() =>
          put.mutate({
            deal_id: d.id,
            terms: {
              our_share_bp: share * 100,
              name: name as 'ours' | 'theirs' | 'combined',
              mp: mp as 'ours' | 'theirs',
              comp_system: comp,
              rates: rates as 'ours' | 'theirs' | 'higher' | 'blend',
            },
          })
        }
        data-testid="put-terms"
      >
        Put to both partnerships ({m.costs.merger_terms} energy)
      </Button>
      {put.error && (
        <Alert color="red" mt="xs">
          {String(put.error.message)}
        </Alert>
      )}
    </Card>
  );
}

function DealCard({ d, slug, m }: { d: MergerDeal; slug: string; m: Mergers }) {
  const answer = useAnswerApproach(slug);
  const walk = useWalkAway(slug);
  const open = d.ended === null && d.stage !== 'closed';
  return (
    <div className="tst-panel" data-testid="deal" data-stage={d.stage}>
      <Group justify="space-between">
        <h3 className="tst-ptitle">
          {d.form === 'verein' ? 'Verein' : d.absorbed ? 'Absorption' : 'Merger'} with {d.firm}
        </h3>
        <Group gap="xs">
          <Badge data-testid="deal-stage">{humanize(d.stage)}</Badge>
          {d.leaked && <Badge color="orange">Leaked</Badge>}
          {d.initiator === 'rival' && <Badge variant="light">Their approach</Badge>}
        </Group>
      </Group>
      <Text size="sm" c="dimmed">
        Opened {d.opened}
        {d.diligence_fees_cents > 0 && ` · diligence fees ${formatMoney(d.diligence_fees_cents)}`}
        {d.ended && ` · ended ${d.ended}: ${d.ended_reason}`}
      </Text>
      {d.terms && (
        <Text size="sm" mt="xs" data-testid="deal-terms">
          Terms: your partners {d.terms.our_share_pct}% of the pool · name {d.terms.name} · MP{' '}
          {d.terms.mp === 'ours' ? 'you' : 'theirs'} · {humanize(d.terms.comp_system)} · card{' '}
          {d.terms.rates}
          {d.their_yes_pct !== null && ` · their partners ${d.their_yes_pct}% in favour`}
        </Text>
      )}
      {d.prediction && d.stage === 'terms' && (
        <Text size="sm" c="dimmed">
          Your partners: {d.prediction.yes_lo}–{d.prediction.yes_hi} of {d.prediction.total} votes
          likely yes; {d.prediction.needed.toFixed(1)} needed ({m.vote_pct}%).
        </Text>
      )}
      {d.stage === 'countered' && (
        <Alert color="yellow" mt="xs" data-testid="counter">
          They ask that your partners take {d.counter_share_pct}% of the merged pool.
        </Alert>
      )}
      {open && (
        <SimpleGrid cols={{ base: 1, lg: 2 }} mt="sm">
          {d.stage === 'approached' ? (
            <Card withBorder>
              <Text size="sm">{d.firm} has approached the firm.</Text>
              <Group mt="xs">
                <Button
                  size="xs"
                  onClick={() => answer.mutate({ deal_id: d.id, accept: true })}
                  data-testid="open-talks"
                >
                  Open talks
                </Button>
                <Button
                  size="xs"
                  variant="light"
                  color="red"
                  onClick={() => answer.mutate({ deal_id: d.id, accept: false })}
                >
                  Decline
                </Button>
              </Group>
            </Card>
          ) : (
            <RevealCard d={d} slug={slug} m={m} />
          )}
          {(d.stage === 'talks' || d.stage === 'countered') && (
            <TermsForm key={`${d.id}-${d.stage}`} d={d} slug={slug} m={m} />
          )}
        </SimpleGrid>
      )}
      {d.stage === 'terms' && (
        <Text size="sm" mt="xs">
          Both partnerships vote next month.
        </Text>
      )}
      {d.stage === 'clearance' && (
        <Text size="sm" mt="xs">
          Both partnerships passed it. It closes next month.
        </Text>
      )}
      {d.conflicts.length > 0 && (
        <Table mt="xs" data-testid="conflicts">
          <Table.Thead>
            <Table.Tr>
              <Table.Th>Your client</Table.Th>
              <Table.Th>Their client</Table.Th>
              <Table.Th>Cleared by</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {d.conflicts.map((c, i) => (
              <Table.Tr key={i}>
                <Table.Td>{c.our_client}</Table.Td>
                <Table.Td>{c.their_client}</Table.Td>
                <Table.Td>{humanize(c.outcome)}</Table.Td>
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
      )}
      {open && d.stage !== 'voting' && d.stage !== 'clearance' && d.stage !== 'approached' && (
        <Button
          mt="sm"
          size="xs"
          variant="subtle"
          color="red"
          onClick={() => walk.mutate(d.id)}
          data-testid="walk-away"
        >
          Walk away
        </Button>
      )}
    </div>
  );
}

function IntegrationCard({ i }: { i: MergerIntegration }) {
  return (
    <Card withBorder data-testid="integration">
      <Title order={5}>Integration of {i.firm}</Title>
      <Text size="sm" c="dimmed">
        Closed {i.closed} · runs to {i.until} ({i.months_left} months left)
      </Text>
      <Table mt="xs">
        <Table.Tbody>
          <Table.Tr>
            <Table.Td>Lawyers at closing</Table.Td>
            <Table.Td className="tst-num">{i.lawyers_at_closing}</Table.Td>
          </Table.Tr>
          <Table.Tr>
            <Table.Td>Equity partners gone</Table.Td>
            <Table.Td className="tst-num" data-testid="partners-lost">
              {i.partners_lost} of {i.partners_at_closing} ({i.partners_lost_pct}%)
            </Table.Td>
          </Table.Tr>
          <Table.Tr>
            <Table.Td>Clients balked at the merged card</Table.Td>
            <Table.Td className="tst-num">
              {i.clients_lost} (their card +{i.card_rise_pct}%)
            </Table.Td>
          </Table.Tr>
          <Table.Tr>
            <Table.Td>Culture clash</Table.Td>
            <Table.Td className="tst-num">{i.clash_pct}%</Table.Td>
          </Table.Tr>
          {i.surrender_cents > 0 && (
            <Table.Tr>
              <Table.Td>Lease surrendered</Table.Td>
              <Table.Td className="tst-num">{formatMoney(i.surrender_cents)}</Table.Td>
            </Table.Tr>
          )}
        </Table.Tbody>
      </Table>
    </Card>
  );
}

export function VereinCard({ m }: { m: Mergers }) {
  const v = m.verein;
  if (!v) return null;
  return (
    <Card withBorder data-testid="verein">
      <Title order={5}>{v.name} (a verein)</Title>
      <Text size="sm" c="dimmed">
        Formed {v.formed}. Each member keeps its own books and profit pool; shared costs are split
        by revenue (your share to date {formatMoney(v.costs_cents)}).
      </Text>
      <Table mt="xs">
        <Table.Thead>
          <Table.Tr>
            <Table.Th>Member</Table.Th>
            <Table.Th>City</Table.Th>
            <Table.Th>Joined</Table.Th>
            <Table.Th>Lawyers</Table.Th>
            <Table.Th>Revenue</Table.Th>
          </Table.Tr>
        </Table.Thead>
        <Table.Tbody>
          {v.members.map((x) => (
            <Table.Tr key={x.key} data-testid="verein-member">
              <Table.Td>{x.name}</Table.Td>
              <Table.Td>{x.city}</Table.Td>
              <Table.Td>{x.joined}</Table.Td>
              <Table.Td className="tst-num">{x.lawyers}</Table.Td>
              <Table.Td className="tst-num">{formatMoneyShort(x.revenue_cents)}</Table.Td>
            </Table.Tr>
          ))}
        </Table.Tbody>
      </Table>
    </Card>
  );
}

export function ExitCard({ m }: { m: Mergers }) {
  const e = m.exit;
  if (!e) return null;
  return (
    <Card withBorder data-testid="exit">
      <Title order={4}>The exit</Title>
      <Text size="sm">
        In {e.turn} the firm joined {e.firm}, number {e.rank} by revenue (
        {formatMoneyShort(e.revenue_cents)} a year). The campaign ends here.
      </Text>
      <Text size="sm" mt="xs">
        Your capital account: {formatMoney(e.capital_cents)} · your draws and true-ups to date:{' '}
        {formatMoney(e.earnings_cents)}
      </Text>
    </Card>
  );
}

export function MergersScreen() {
  const { slug = '' } = useParams();
  const q = useMergers(slug);
  if (!q.data) return <Text c="dimmed">Loading…</Text>;
  const m = q.data;
  const open = m.deals.filter((d) => d.ended === null && d.stage !== 'closed');
  const past = m.deals.filter((d) => !(d.ended === null && d.stage !== 'closed'));
  return (
    <Stack>
      <Title order={2}>Mergers</Title>
      <ExitCard m={m} />
      {!m.is_mp && !m.exit && (
        <Alert color="gray">Only the managing partner can make merger moves.</Alert>
      )}
      <Text size="sm" c="dimmed">
        Energy {m.energy}. A merger needs {m.vote_pct}% of each partnership.
      </Text>
      {open.map((d) => (
        <DealCard key={d.id} d={d} slug={slug} m={m} />
      ))}
      {m.integrations.length > 0 && (
        <SimpleGrid cols={{ base: 1, lg: 2 }}>
          {m.integrations.map((i) => (
            <IntegrationCard key={i.deal_id} i={i} />
          ))}
        </SimpleGrid>
      )}
      <VereinCard m={m} />
      {!m.exit && <TargetsPanel m={m} slug={slug} />}
      {past.length > 0 && (
        <div className="tst-panel" data-testid="past-deals">
          <h3 className="tst-ptitle">Past talks</h3>
          {past.map((d) => (
            <Text size="sm" key={d.id}>
              {d.firm} ({d.form}): {humanize(d.stage)}
              {d.ended_reason ? ` (${d.ended_reason})` : ''}
              {d.ended ? `, ${d.ended}` : ''}
            </Text>
          ))}
        </div>
      )}
    </Stack>
  );
}
