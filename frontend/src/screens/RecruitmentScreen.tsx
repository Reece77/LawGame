import { RunBy } from '../components/RunBy';
import {
  Alert,
  Badge,
  Button,
  Card,
  Group,
  Modal,
  MultiSelect,
  NumberInput,
  SegmentedControl,
  Select,
  SimpleGrid,
  Stack,
  Table,
  Text,
  Title,
} from '@mantine/core';
import { useState } from 'react';
import { useParams } from 'react-router';
import { rangeText } from '../lib/attr';
import {
  useOffices,
  useOfferPreview,
  useRecruitment,
  useRecruitmentAction,
  type Candidate,
  type OpenSearchBody,
  type Recruitment,
  type RecruitmentAction,
} from '../lib/api';
import { formatMoney, formatMoneyWhole, humanize } from '../lib/format';

// Recruitment (spec 16, 5.7): the campus season, searches, candidates as the firm sees them
// (revealed ranges and the potential phrase; asks exactly), offers and the pay policy. Every
// button is an immediate action (ADR-0014); the server enforces the rules and says why.

const HINT_COLOR = { likely: 'teal', uncertain: 'yellow', unlikely: 'red' } as const;

export function RecruitmentScreen() {
  const { slug = '' } = useParams();
  const view = useRecruitment(slug);
  const act = useRecruitmentAction(slug);
  const [offerFor, setOfferFor] = useState<Candidate | null>(null);
  if (!view.data) return <Text c="dimmed">Loading…</Text>;
  const r = view.data;
  const run = (a: RecruitmentAction) => act.mutate(a);
  return (
    <Stack>
      <Group justify="space-between">
        <Title order={2}>Recruitment</Title>
        <RunBy slug={slug} areas={['hiring']} />
        <Badge size="lg" variant="light" data-testid="energy">
          Energy {r.energy} / {r.energy_per_month}
        </Badge>
      </Group>
      {act.error && (
        <Alert color="red" title="Not done" data-testid="action-error">
          {act.error.message}
        </Alert>
      )}
      <SimpleGrid cols={{ base: 1, md: 2 }}>
        <CampusPanel r={r} />
        <OpenSearchForm r={r} onOpen={(body) => run({ kind: 'open', body })} busy={act.isPending} />
      </SimpleGrid>
      <SearchesTable r={r} run={run} />
      <CandidatesTable r={r} run={run} onOffer={setOfferFor} busy={act.isPending} />
      <OffersTable r={r} run={run} />
      <PayPanel r={r} onSave={(body) => run({ kind: 'pay', body })} />
      <OfferDialog
        slug={slug}
        candidate={offerFor}
        onClose={() => setOfferFor(null)}
        onSend={(candidateId, salaryCents) => {
          run({ kind: 'offer', candidateId, salaryCents });
          setOfferFor(null);
        }}
      />
    </Stack>
  );
}

function CampusPanel({ r }: { r: Recruitment }) {
  const c = r.campus;
  let status = 'Registration has closed for this year.';
  if (c.registration_open) status = 'Registration is open: open a campus search for each practice.';
  if (c.in_summer)
    status = `The summer programme is running: ${c.summer_associates} summer associates.`;
  if (c.offers_open) status = 'Offer month: interview summer associates and make your offers.';
  return (
    <Card withBorder data-testid="campus-panel">
      <Title order={4}>Campus season</Title>
      <Text size="sm" c="dimmed" mb="xs">
        Register {c.registration_label} · summer programme {c.summer_label} · offers {c.offer_label}{' '}
        · the class starts in {c.start_label} of the next year
      </Text>
      <Text data-testid="campus-status">{status}</Text>
      {c.registered_roles.length > 0 && (
        <Text size="sm">Registered: {c.registered_roles.join(', ')}</Text>
      )}
      {c.signed.length > 0 && (
        <>
          <Text fw={600} mt="sm">
            Signed ({c.signed.length})
          </Text>
          {c.signed.map((s) => (
            <Text size="sm" key={s.person_id} data-testid="signed">
              {s.name}, {s.role_label}: starts {s.start_label}
            </Text>
          ))}
        </>
      )}
    </Card>
  );
}

function OpenSearchForm({
  r,
  onOpen,
  busy,
}: {
  r: Recruitment;
  onOpen: (body: OpenSearchBody) => void;
  busy: boolean;
}) {
  const [role, setRole] = useState<string | null>(r.roles[0]?.key ?? null);
  const [channel, setChannel] = useState<string | null>('campus');
  const [level, setLevel] = useState<string | null>(null);
  const [tiers, setTiers] = useState<string[]>([]);
  const [city, setCity] = useState<string | null>(null);
  const { slug = '' } = useParams();
  const offices = useOffices(slug).data?.offices ?? []; // PT-M11: a local hiring pool
  const kind = r.roles.find((x) => x.key === role)?.kind ?? 'lawyer';
  const levels = (r.levels[kind] ?? []).filter((l) => l !== 'associate_1' || channel !== 'campus');
  const chosen = r.channels.find((c) => c.key === channel);
  return (
    <Card withBorder>
      <Title order={4}>Open a search</Title>
      <Stack gap="xs">
        <Select
          label="Role"
          data={r.roles.map((x) => ({ value: x.key, label: x.label }))}
          value={role}
          onChange={setRole}
          allowDeselect={false}
        />
        <Select
          label="Channel"
          data={r.channels.map((x) => ({ value: x.key, label: x.label }))}
          value={channel}
          onChange={setChannel}
          allowDeselect={false}
          description={chosen ? `${chosen.energy} energy; ${chosen.fee_note}` : undefined}
        />
        {channel !== 'campus' && (
          <Select
            label="Level"
            placeholder="Any level"
            data={levels.map((l) => ({ value: l, label: humanize(l) }))}
            value={level}
            onChange={setLevel}
            clearable
          />
        )}
        {kind === 'lawyer' && (
          <MultiSelect
            label="Law schools"
            placeholder="Any tier"
            data={r.school_tiers.map((t) => ({ value: t.key, label: t.label }))}
            value={tiers}
            onChange={setTiers}
          />
        )}
        {offices.length > 1 && channel !== 'campus' && (
          <Select
            label="Office"
            placeholder="Home office"
            data={offices.map((o) => ({ value: o.city, label: o.label }))}
            value={city}
            onChange={setCity}
            clearable
            data-testid="search-office"
          />
        )}
        <Button
          loading={busy}
          disabled={!role || !channel}
          onClick={() =>
            role && channel && onOpen(buildBody({ role, channel, level, tiers, city }))
          }
        >
          Open search
        </Button>
      </Stack>
    </Card>
  );
}

function buildBody(v: {
  role: string;
  channel: string;
  level: string | null;
  tiers: string[];
  city?: string | null;
}): OpenSearchBody {
  return {
    role: v.role,
    channel: v.channel as 'campus' | 'recruiter' | 'job_post' | 'referral',
    level: v.channel === 'campus' ? null : v.level,
    school_tiers: v.tiers,
    city: v.channel === 'campus' ? null : (v.city ?? null),
  };
}

function SearchesTable({ r, run }: { r: Recruitment; run: (a: RecruitmentAction) => void }) {
  if (r.searches.length === 0) return null;
  return (
    <Card withBorder>
      <Title order={4} mb="xs">
        Searches
      </Title>
      <Table data-testid="searches-table">
        <Table.Thead>
          <Table.Tr>
            <Table.Th>Channel</Table.Th>
            <Table.Th>Role</Table.Th>
            <Table.Th>Opened</Table.Th>
            <Table.Th>Status</Table.Th>
            <Table.Th>Open candidates</Table.Th>
            <Table.Th />
          </Table.Tr>
        </Table.Thead>
        <Table.Tbody>
          {r.searches.map((s) => (
            <Table.Tr key={s.id}>
              <Table.Td>{s.channel_label}</Table.Td>
              <Table.Td>
                {s.role_label}
                {s.level ? ` · ${humanize(s.level)}` : ''}
                {s.school_tiers.length ? ` · ${s.school_tiers.join(', ')}` : ''}
              </Table.Td>
              <Table.Td>{s.opened_label}</Table.Td>
              <Table.Td>{humanize(s.status)}</Table.Td>
              <Table.Td className="tst-num">{s.open_candidates}</Table.Td>
              <Table.Td>
                <Group gap={4}>
                  {s.open_candidates > 0 && (
                    <Button
                      size="compact-xs"
                      variant="light"
                      onClick={() => run({ kind: 'scout', searchId: s.id })}
                    >
                      Scout
                    </Button>
                  )}
                  {s.status === 'open' && (
                    <Button
                      size="compact-xs"
                      variant="subtle"
                      onClick={() => run({ kind: 'close', searchId: s.id })}
                    >
                      Close
                    </Button>
                  )}
                </Group>
              </Table.Td>
            </Table.Tr>
          ))}
        </Table.Tbody>
      </Table>
    </Card>
  );
}

function CandidatesTable({
  r,
  run,
  onOffer,
  busy,
}: {
  r: Recruitment;
  run: (a: RecruitmentAction) => void;
  onOffer: (c: Candidate) => void;
  busy: boolean;
}) {
  return (
    <Card withBorder>
      <Title order={4} mb="xs">
        Candidates
      </Title>
      {r.candidates.length === 0 ? (
        <Text c="dimmed" size="sm">
          No candidates yet. Lateral searches bring candidates next month; campus searches bring
          summer associates in May.
        </Text>
      ) : (
        <div className="tst-table-wrap">
          <Table striped data-testid="candidates-table">
            <Table.Thead>
              <Table.Tr>
                <Table.Th>Name</Table.Th>
                <Table.Th>Level</Table.Th>
                <Table.Th>School</Table.Th>
                <Table.Th>Ability</Table.Th>
                <Table.Th>Potential</Table.Th>
                <Table.Th>Ask</Table.Th>
                <Table.Th>Until</Table.Th>
                <Table.Th />
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {r.candidates.map((c) => (
                <Table.Tr key={c.id} data-testid="candidate-row">
                  <Table.Td>
                    {c.name}
                    {c.channel === 'campus' && (
                      <Badge size="xs" ml={6} variant="light">
                        Summer
                      </Badge>
                    )}
                  </Table.Td>
                  <Table.Td>{humanize(c.level)}</Table.Td>
                  <Table.Td>{c.school_tier ?? '—'}</Table.Td>
                  <Table.Td className="tst-num">{rangeText(c.ability)}</Table.Td>
                  <Table.Td>{c.potential}</Table.Td>
                  <Table.Td className="tst-num">{formatMoneyWhole(c.ask_cents)}</Table.Td>
                  <Table.Td>{c.expires_label}</Table.Td>
                  <Table.Td>
                    <Group gap={4} wrap="nowrap">
                      <Button
                        size="compact-xs"
                        variant={c.interviewed ? 'subtle' : 'light'}
                        disabled={busy}
                        onClick={() => run({ kind: 'interview', candidateId: c.id })}
                      >
                        {c.interviewed ? 'Interview again' : 'Interview'}
                      </Button>
                      <Button
                        size="compact-xs"
                        variant="subtle"
                        disabled={busy}
                        onClick={() => run({ kind: 'reference', candidateId: c.id })}
                      >
                        References
                      </Button>
                      {c.pending_offer_id === null ? (
                        <Button
                          size="compact-xs"
                          disabled={!c.offer_allowed || busy}
                          title={
                            c.offer_blocked_reason === 'campus_offer_month'
                              ? 'Campus offers go out in the offer month'
                              : c.offer_blocked_reason === 'interview_required'
                                ? 'Interview first'
                                : undefined
                          }
                          onClick={() => onOffer(c)}
                        >
                          Make offer
                        </Button>
                      ) : (
                        <Badge variant="outline">Offer pending</Badge>
                      )}
                    </Group>
                  </Table.Td>
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
        </div>
      )}
    </Card>
  );
}

function OffersTable({ r, run }: { r: Recruitment; run: (a: RecruitmentAction) => void }) {
  if (r.offers.length === 0) return null;
  return (
    <Card withBorder>
      <Title order={4} mb="xs">
        Pending offers
      </Title>
      <Table data-testid="offers-table">
        <Table.Tbody>
          {r.offers.map((o) => (
            <Table.Tr key={o.id}>
              <Table.Td>{o.name}</Table.Td>
              <Table.Td className="tst-num">{formatMoney(o.salary_cents)}</Table.Td>
              <Table.Td>Made {o.made_label}; answered when the month is played</Table.Td>
              <Table.Td>
                <Button
                  size="compact-xs"
                  variant="subtle"
                  onClick={() => run({ kind: 'withdraw', offerId: o.id })}
                >
                  Withdraw
                </Button>
              </Table.Td>
            </Table.Tr>
          ))}
        </Table.Tbody>
      </Table>
    </Card>
  );
}

function PayPanel({
  r,
  onSave,
}: {
  r: Recruitment;
  onSave: (body: { mode: 'match' | 'lag' | 'lead'; pct_bp: number }) => void;
}) {
  const [mode, setMode] = useState<'match' | 'lag' | 'lead'>(r.pay_policy.mode);
  const [pct, setPct] = useState<number>(r.pay_policy.pct_bp / 100);
  return (
    <Card withBorder>
      <Title order={4}>Pay against the market scale</Title>
      <Group align="end" my="xs">
        <SegmentedControl
          value={mode}
          onChange={(v) => setMode(v as 'match' | 'lag' | 'lead')}
          data={[
            { value: 'match', label: 'Match' },
            { value: 'lag', label: 'Lag' },
            { value: 'lead', label: 'Lead' },
          ]}
        />
        {mode !== 'match' && (
          <NumberInput
            label="% of market"
            value={pct}
            onChange={(v) => setPct(Number(v))}
            min={r.pay_policy.min_bp / 100}
            max={r.pay_policy.max_bp / 100}
            w={120}
          />
        )}
        <Button variant="light" onClick={() => onSave({ mode, pct_bp: Math.round(pct * 100) })}>
          Set pay policy
        </Button>
      </Group>
      <Table data-testid="scale-table">
        <Table.Thead>
          <Table.Tr>
            <Table.Th>Class year</Table.Th>
            <Table.Th>Market salary</Table.Th>
            <Table.Th>Our salary</Table.Th>
            <Table.Th>Market bonus</Table.Th>
          </Table.Tr>
        </Table.Thead>
        <Table.Tbody>
          {r.scale.map((s) => (
            <Table.Tr key={s.level}>
              <Table.Td>{s.class_year}</Table.Td>
              <Table.Td className="tst-num">{formatMoneyWhole(s.market_cents)}</Table.Td>
              <Table.Td className="tst-num">{formatMoneyWhole(s.firm_cents)}</Table.Td>
              <Table.Td className="tst-num">{formatMoneyWhole(s.market_bonus_cents)}</Table.Td>
            </Table.Tr>
          ))}
        </Table.Tbody>
      </Table>
    </Card>
  );
}

function OfferDialog({
  slug,
  candidate,
  onClose,
  onSend,
}: {
  slug: string;
  candidate: Candidate | null;
  onClose: () => void;
  onSend: (candidateId: number, salaryCents: number) => void;
}) {
  const [dollars, setDollars] = useState<number | null>(null);
  const salary = candidate ? (dollars ?? Math.round(candidate.ask_cents / 100)) : 0;
  const preview = useOfferPreview(slug, candidate?.id ?? null, salary * 100);
  return (
    <Modal
      opened={candidate !== null}
      onClose={onClose}
      title={candidate ? `Offer: ${candidate.name}` : ''}
    >
      {candidate && (
        <Stack>
          <Text size="sm">Asks {formatMoneyWhole(candidate.ask_cents)} a year.</Text>
          <NumberInput
            label="Salary (dollars a year)"
            value={salary}
            onChange={(v) => setDollars(Number(v))}
            min={1}
            step={1000}
            thousandSeparator=","
          />
          {preview.data && (
            <Group>
              <Badge color={HINT_COLOR[preview.data.hint]} data-testid="offer-hint">
                {humanize(preview.data.hint)}
              </Badge>
              <Text size="sm" c="dimmed">
                {preview.data.ratio.toFixed(2)}× the ask; below{' '}
                {formatMoneyWhole(preview.data.floor_cents)} is always declined
              </Text>
            </Group>
          )}
          <Button
            onClick={() => {
              onSend(candidate.id, salary * 100);
              setDollars(null);
            }}
          >
            Send offer
          </Button>
        </Stack>
      )}
    </Modal>
  );
}
