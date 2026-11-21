import {
  Alert,
  Badge,
  Button,
  Card,
  Group,
  Modal,
  NumberInput,
  Progress,
  Select,
  SimpleGrid,
  Stack,
  Switch,
  Table,
  Text,
  TextInput,
  Title,
} from '@mantine/core';
import { useState } from 'react';
import { useParams } from 'react-router';
import { useFounder, useFounderAction, type Founder, type SuccessorCandidate } from '../lib/api';
import { formatBpPercent, formatMoneyWhole, humanize } from '../lib/format';

// The Founder screen (spec 2.3-2.5, 16; PT-M17): the persona and its causes, the personal
// account, the foundation, bar politics, the legacy score, retirement and annuities, and the
// succession flow (choose a successor, see the predicted vote range, confirm). Every number
// arrives from the API; this screen only formats it and sends one action per button.

type Act = ReturnType<typeof useFounderAction>;
const money = (c: number) => formatMoneyWhole(c);
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

function Persona({ f }: { f: Founder }) {
  return (
    <Card withBorder data-testid="persona">
      <Title order={4}>Persona</Title>
      <Text size="sm" c="dimmed" mb="xs">
        The profession sees you as {f.public_words}.
      </Text>
      {f.persona_traits.map((t) => (
        <Group key={t.key} gap="xs" wrap="nowrap">
          <Text w={90}>{humanize(t.key)}</Text>
          <Progress value={t.value} w={200} color={t.strong ? 'teal' : 'gray'} />
          <Text className="tst-num" w={30}>
            {t.value}
          </Text>
          {t.strong && (
            <Badge size="xs" variant="light">
              in effect
            </Badge>
          )}
        </Group>
      ))}
      {f.causes.length > 0 && (
        <Table mt="sm" fz="xs">
          <Table.Tbody>
            {f.causes.slice(0, 6).map((c, i) => (
              <Table.Tr key={i}>
                <Table.Td>{c.when}</Table.Td>
                <Table.Td>{humanize(c.trait)}</Table.Td>
                <Table.Td className="tst-num">
                  {c.change > 0 ? '+' : ''}
                  {c.change}
                </Table.Td>
                <Table.Td>{c.why}</Table.Td>
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
      )}
    </Card>
  );
}

function Personal({ f, act }: { f: Founder; act: Act }) {
  const p = f.personal;
  const [amount, setAmount] = useState<string | number>(10000);
  const [mandate, setMandate] = useState<string | null>(p.mandate ?? 'balanced');
  return (
    <Card withBorder data-testid="personal">
      <Title order={4}>Personal account</Title>
      <Table fz="sm" mt="xs">
        <Table.Tbody>
          <Table.Tr>
            <Table.Td>Personal cash</Table.Td>
            <Table.Td className="tst-num" data-testid="personal-cash">
              {money(p.cash_cents)}
            </Table.Td>
          </Table.Tr>
          <Table.Tr>
            <Table.Td>Investments</Table.Td>
            <Table.Td className="tst-num">{money(p.investments_cents)}</Table.Td>
          </Table.Tr>
          <Table.Tr>
            <Table.Td>Family office {p.mandate ? `(${p.mandate})` : ''}</Table.Td>
            <Table.Td className="tst-num">{money(p.family_office_cents)}</Table.Td>
          </Table.Tr>
          <Table.Tr>
            <Table.Td>Capital in the firm</Table.Td>
            <Table.Td className="tst-num">{money(p.firm_capital_cents)}</Table.Td>
          </Table.Tr>
          <Table.Tr>
            <Table.Td>Capital loan</Table.Td>
            <Table.Td className="tst-num">-{money(p.loan_cents)}</Table.Td>
          </Table.Tr>
          <Table.Tr>
            <Table.Td fw={600}>Net worth</Table.Td>
            <Table.Td className="tst-num" fw={600} data-testid="net-worth">
              {money(p.net_worth_cents)}
            </Table.Td>
          </Table.Tr>
        </Table.Tbody>
      </Table>
      <Text size="sm" mt="sm" fw={600}>
        The last 12 months
      </Text>
      <Text size="sm" data-testid="income-year">
        Draws {money(p.year.draws_cents)} + true-up {money(p.year.true_up_cents)} - tax{' '}
        {money(p.year.tax_cents)} = after tax {money(p.year.after_tax_cents)}
        {p.year.annuity_cents > 0 && `; annuity ${money(p.year.annuity_cents)}`}
      </Text>
      <Group mt="sm" align="end">
        <NumberInput label="Amount ($)" value={amount} onChange={setAmount} w={140} />
        <Button
          variant="light"
          onClick={() => act.mutate({ kind: 'invest', amount_cents: dollars(amount) })}
          data-testid="invest"
        >
          Invest
        </Button>
        <Button
          variant="subtle"
          onClick={() => act.mutate({ kind: 'invest', amount_cents: -dollars(amount) })}
        >
          Sell
        </Button>
        <Select
          label="Family office"
          data={p.mandates}
          value={mandate}
          onChange={setMandate}
          w={150}
        />
        <Button
          variant="light"
          onClick={() =>
            act.mutate({
              kind: 'family_office',
              mandate: mandate ?? 'balanced',
              amount_cents: dollars(amount),
            })
          }
          disabled={!p.mandate && p.net_worth_cents < p.family_office_min_cents}
        >
          {p.mandate ? 'Add' : 'Form'}
        </Button>
      </Group>
      {p.recent.length > 0 && (
        <Table mt="sm" fz="xs" data-testid="personal-entries">
          <Table.Tbody>
            {p.recent.slice(0, 8).map((e, i) => (
              <Table.Tr key={i}>
                <Table.Td>{e.when}</Table.Td>
                <Table.Td>{e.memo}</Table.Td>
                <Table.Td className="tst-num">{e.cash_cents ? money(e.cash_cents) : ''}</Table.Td>
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
      )}
    </Card>
  );
}

function FoundationCard({ f, act }: { f: Founder; act: Act }) {
  const [cause, setCause] = useState<string | null>('access_to_justice');
  const [name, setName] = useState('');
  const [gift, setGift] = useState<string | number>(100000);
  const fd = f.foundation;
  return (
    <Card withBorder data-testid="foundation">
      <Title order={4}>Foundation</Title>
      {fd ? (
        <>
          <Text>
            {fd.name}: {fd.cause_label}
          </Text>
          <Text size="sm">
            Endowment {money(fd.endowment_cents)}; lifetime grants {money(fd.grants_cents)}
          </Text>
          <Group mt="xs" align="end">
            <NumberInput label="Gift ($)" value={gift} onChange={setGift} w={140} />
            <Button
              variant="light"
              onClick={() => act.mutate({ kind: 'gift', amount_cents: dollars(gift) })}
            >
              Give
            </Button>
          </Group>
        </>
      ) : (
        <>
          <Text size="sm" c="dimmed">
            A foundation needs {money(f.foundation_min_cents)} of personal cash.
          </Text>
          <Group mt="xs" align="end">
            <Select
              label="Cause"
              data={f.causes_available.map((c) => ({ value: c, label: humanize(c) }))}
              value={cause}
              onChange={setCause}
              w={190}
            />
            <TextInput
              label="Name"
              placeholder="The ... Foundation"
              value={name}
              onChange={(e) => setName(e.currentTarget.value)}
            />
            <Button
              variant="light"
              disabled={f.personal.cash_cents < f.foundation_min_cents}
              onClick={() =>
                act.mutate({ kind: 'foundation', cause: cause ?? 'access_to_justice', name })
              }
            >
              Create
            </Button>
          </Group>
        </>
      )}
    </Card>
  );
}

function Bar({ f, act }: { f: Founder; act: Act }) {
  const i = f.influence;
  const [spend, setSpend] = useState<string | number>(i.spend_cents / 100);
  return (
    <Card withBorder data-testid="bar">
      <Title order={4}>Bar politics</Title>
      <Group gap="xs">
        <Text>Influence</Text>
        <Progress value={i.value} w={160} />
        <Text className="tst-num" data-testid="influence">
          {i.value}
        </Text>
        {i.in_office && <Badge>Bar president until {i.office_until}</Badge>}
      </Group>
      <Switch
        mt="xs"
        label="Sit on a bar committee (energy each month)"
        checked={i.committee}
        onChange={(e) => act.mutate({ kind: 'committee', on: e.currentTarget.checked })}
        data-testid="committee"
      />
      <Group mt="xs" align="end">
        <NumberInput
          label="Bar politics a month ($)"
          value={spend}
          onChange={setSpend}
          min={0}
          max={i.max_spend_cents / 100}
          w={180}
        />
        <Button
          variant="light"
          onClick={() => act.mutate({ kind: 'spend', monthly_cents: dollars(spend) })}
        >
          Set
        </Button>
        <Button
          variant="subtle"
          disabled={!i.can_stand || i.standing || i.in_office}
          onClick={() => act.mutate({ kind: 'stand' })}
        >
          {i.standing ? 'Standing for office' : 'Stand for bar office'}
        </Button>
      </Group>
    </Card>
  );
}

function LegacyCard({ f }: { f: Founder }) {
  const l = f.legacy;
  return (
    <Card withBorder data-testid="legacy">
      <Title order={4}>Legacy {l.total}</Title>
      <Text size="sm">
        The firm {l.firm}; name on the door {l.name_on_door}; the foundation {l.giving}; persona{' '}
        {l.persona}; family {l.family}; bar office {l.bar}
      </Text>
    </Card>
  );
}

function Retirement({ f, act }: { f: Founder; act: Act }) {
  const [age, setAge] = useState<string | number>(f.retirement_age);
  const [share, setShare] = useState<string | number>(25);
  const [years, setYears] = useState<string | number>(10);
  return (
    <Card withBorder data-testid="retirement">
      <Title order={4}>Retirement and annuities</Title>
      <Text size="sm">
        The agreement retires partners at {f.retirement_age}; you have{' '}
        {Math.max(0, f.years_to_retirement)} years to go.{' '}
        {f.age >= f.plan_from_age &&
          !f.plan_id &&
          'The partnership expects a succession plan: name a successor-designate.'}
      </Text>
      <Text size="sm">
        Annuities:{' '}
        {f.annuities_granted
          ? `${formatBpPercent(f.annuity_share_bp)} of the last allocation for ${f.annuity_years} years`
          : 'none'}
        ; owed {money(f.annuities_owed_cents)}
      </Text>
      {f.is_mp && (
        <Group mt="xs" align="end">
          <NumberInput
            label="Retirement age"
            value={age}
            onChange={setAge}
            min={55}
            max={80}
            w={130}
          />
          <Button
            variant="light"
            onClick={() => act.mutate({ kind: 'retirement_age', age: Number(age) })}
          >
            Put to a vote
          </Button>
          <NumberInput
            label="Annuity %"
            value={share}
            onChange={setShare}
            min={0}
            max={50}
            w={110}
          />
          <NumberInput label="Years" value={years} onChange={setYears} min={1} max={30} w={90} />
          <Button
            variant="light"
            onClick={() =>
              act.mutate({
                kind: 'annuities',
                share_bp: Math.round(Number(share) * 100),
                years: Number(years),
              })
            }
          >
            Vote on annuities
          </Button>
        </Group>
      )}
    </Card>
  );
}

function SuccessionFlow({ f, act }: { f: Founder; act: Act }) {
  const [pick, setPick] = useState<string | null>(null);
  const [confirm, setConfirm] = useState(false);
  const chosen: SuccessorCandidate | undefined = f.candidates.find(
    (c) => String(c.person_id) === pick,
  );
  return (
    <Card withBorder data-testid="succession">
      <Title order={4}>Succession</Title>
      {f.due && (
        <Alert color="yellow" mt="xs" data-testid="succession-due">
          {f.due_trigger === 'health' ? 'Your health' : 'The retirement age'} asks you to hand over:
          name a successor by {f.due}.
        </Alert>
      )}
      {f.open_succession && (
        <Alert mt="xs" data-testid="succession-open">
          The partnership votes on your successor at the end of this month.
        </Alert>
      )}
      <Select
        mt="xs"
        label="Successor (an equity partner)"
        placeholder="Choose a partner"
        data={f.candidates.map((c) => ({
          value: String(c.person_id),
          label: `${c.name} (${c.practice}, ${c.age})${c.is_child ? ' - your child' : ''}`,
        }))}
        value={pick}
        onChange={setPick}
        data-testid="successor-select"
      />
      {chosen && (
        <Text size="sm" mt="xs" data-testid="predicted-vote">
          Rated {chosen.rating.lo}-{chosen.rating.hi}. Predicted vote for {chosen.name}:{' '}
          {chosen.predicted_yes.lo}-{chosen.predicted_yes.hi} of {chosen.total_weight} (needs{' '}
          {chosen.needed_weight.toFixed(1)})
          {chosen.rival_name ? `; ${chosen.rival_name} would stand against them` : '; unopposed'}.
        </Text>
      )}
      <Group mt="xs">
        <Button
          variant="light"
          disabled={!chosen}
          onClick={() => chosen && act.mutate({ kind: 'plan', person_id: chosen.person_id })}
          data-testid="plan-successor"
        >
          Make them the succession plan
        </Button>
        <Button
          disabled={!chosen || f.open_succession}
          onClick={() => setConfirm(true)}
          data-testid="hand-over"
        >
          Hand over
        </Button>
      </Group>
      {f.plan_id && (
        <Text size="sm" mt="xs">
          Succession plan: {f.candidates.find((c) => c.person_id === f.plan_id)?.name ?? '—'}
        </Text>
      )}
      <Modal opened={confirm} onClose={() => setConfirm(false)} title="Hand over the firm">
        {chosen && (
          <Stack>
            <Text>
              The partnership will vote on {chosen.name} as managing partner this month. If they are
              elected you play them from next month; you stay on as senior partner until you retire.
            </Text>
            <Button
              onClick={() => {
                act.mutate({ kind: 'name', person_id: chosen.person_id });
                setConfirm(false);
              }}
              data-testid="confirm-hand-over"
            >
              Confirm
            </Button>
          </Stack>
        )}
      </Modal>
      {f.played.length > 1 && (
        <Table mt="sm" fz="xs" data-testid="played">
          <Table.Tbody>
            {f.played.map((x) => (
              <Table.Tr key={x.person_id}>
                <Table.Td>{x.name}</Table.Td>
                <Table.Td>{humanize(x.status)}</Table.Td>
                <Table.Td>
                  {x.since}
                  {x.until ? ` - ${x.until}` : ''}
                </Table.Td>
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
      )}
      {f.opinions.length > 0 && (
        <Stack mt="sm" gap={4}>
          {f.opinions.slice(0, 3).map((o, i) => (
            <Text size="xs" key={i}>
              {o.when}: {o.adviser} would {o.stance} {o.title}: &ldquo;{o.text}&rdquo;
            </Text>
          ))}
        </Stack>
      )}
    </Card>
  );
}

export function FounderScreen() {
  const { slug = '' } = useParams();
  const q = useFounder(slug);
  const act = useFounderAction(slug);
  const f = q.data;
  if (!f) return <Text>Loading...</Text>;
  return (
    <Stack>
      <Title order={2}>Founder</Title>
      <Text data-testid="founder-name">
        {f.name}, {f.age}: {humanize(f.status)}
      </Text>
      {act.error && <Alert color="red">{act.error.message}</Alert>}
      <SimpleGrid cols={{ base: 2, md: 4 }}>
        <Tile label="Net worth" value={money(f.personal.net_worth_cents)} />
        <Tile label="After-tax income (12 months)" value={money(f.personal.year.after_tax_cents)} />
        <Tile label="Legacy" value={String(f.legacy.total)} />
        <Tile
          label="Retirement"
          value={`at ${f.retirement_age}`}
          note={`${Math.max(0, f.years_to_retirement)} years to go`}
          testId="retirement-age"
        />
      </SimpleGrid>
      <SimpleGrid cols={{ base: 1, md: 2 }}>
        <Persona f={f} />
        <Personal f={f} act={act} />
        <SuccessionFlow f={f} act={act} />
        <Retirement f={f} act={act} />
        <FoundationCard f={f} act={act} />
        <Bar f={f} act={act} />
        <LegacyCard f={f} />
      </SimpleGrid>
    </Stack>
  );
}
