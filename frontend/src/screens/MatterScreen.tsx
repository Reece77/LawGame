import {
  Alert,
  Badge,
  Button,
  Group,
  NumberInput,
  Progress,
  Select,
  SimpleGrid,
  Stack,
  Text,
  Title,
} from '@mantine/core';
import { useState, type DragEvent } from 'react';
import { Link, useParams } from 'react-router';
import { AttributeRange } from '../components/AttributeRange';
import { Explain } from '../components/Explain';
import { StrainBar } from '../components/StrainBar';
import {
  useMatter,
  useMatterAction,
  useMatterMoneyById,
  useRecentBills,
  useWriteDown,
  usePracticeLabels,
  useStaffingBoard,
  type BoardPerson,
  type MatterAction,
  type MatterDetail,
  type StaffingBoard,
} from '../lib/api';
import { formatBpShort, formatHours, formatMoneyWhole, humanize } from '../lib/format';

// A matter (spec 16): the staffing board (drag people onto the matter, hours a month, strain
// warnings), phase timeline, bills, events and settlement offers. The engine decides every
// rule: an over-capacity assignment or a conflict comes back as its error, shown as sent.

const DRAG_TYPE = 'application/x-ptk-person';
const DEFAULT_HOURS = 20;

function Stat({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <Text size="xs" c="dimmed">
        {label}
      </Text>
      <div className="tst-num">{children}</div>
    </div>
  );
}

export function MatterScreen() {
  const { slug = '', matterId = '0' } = useParams();
  const id = Number(matterId);
  const matter = useMatter(slug, id);
  const board = useStaffingBoard(slug, id);
  const action = useMatterAction(slug, id);
  if (matter.isLoading) return <Text c="dimmed">Loading…</Text>;
  if (matter.error || !matter.data) {
    return <Alert color="red">Could not load the matter: {matter.error?.message}</Alert>;
  }
  const m = matter.data;
  const run = (a: MatterAction) => action.mutate(a);
  return (
    <Stack gap="lg">
      <div>
        <Group gap="xs">
          <Title order={2} data-testid="matter-name">
            {m.name}
          </Title>
          <Badge variant="light" data-testid="matter-status">
            {humanize(m.outcome ?? m.status)}
          </Badge>
          {m.critical && (
            <Badge color="orange" variant="light">
              Critical
            </Badge>
          )}
        </Group>
        <Text c="dimmed" size="sm">
          <Link to={`/game/${slug}/clients/${m.client.id}`}>{m.client.name}</Link> · {m.kind_label}
          {m.adverse && ` · against ${m.adverse}`}
          {m.court && ` · ${m.court}`}
          {m.judge && ` · ${m.judge}`}
        </Text>
      </div>

      {action.error && (
        <Alert
          color="red"
          title="The engine refused that"
          withCloseButton
          onClose={() => action.reset()}
          data-testid="matter-error"
        >
          {action.error.message}
        </Alert>
      )}

      <MatterStats m={m} slug={slug} />
      {m.status === 'conflicted' && <ConflictPanel m={m} run={run} busy={action.isPending} />}
      {m.settlement && (
        <Alert color="blue" title="Settlement offer" data-testid="settlement">
          <Group justify="space-between">
            <Text>
              The other side offers{' '}
              <span className="tst-num">{formatMoneyWhole(m.settlement.offer_cents)}</span>, open
              until {m.settlement.expires_label}.
            </Text>
            <Group>
              <Button size="xs" onClick={() => run({ kind: 'settlement', accept: true })}>
                Accept
              </Button>
              <Button
                size="xs"
                variant="default"
                onClick={() => run({ kind: 'settlement', accept: false })}
              >
                Reject
              </Button>
            </Group>
          </Group>
        </Alert>
      )}
      {m.forums.length > 0 && <ForumPanel m={m} run={run} />}
      <PhaseTimeline m={m} />
      {board.data && (
        <StaffingBoardPanel
          m={m}
          board={board.data}
          run={run}
          busy={action.isPending}
          slug={slug}
        />
      )}
      <BillsPanel m={m} slug={slug} />
      <div className="tst-panel">
        <h3 className="tst-ptitle">Events</h3>
        {(board.data?.events ?? []).length === 0 ? (
          <Text size="sm" c="dimmed">
            Nothing has happened on this matter yet.
          </Text>
        ) : (
          <Stack gap={6} data-testid="matter-events">
            {board.data?.events.map((e) => (
              <div key={e.id}>
                <Text size="sm" fw={600}>
                  {e.date_label}: {e.title}
                </Text>
                <Text size="sm" c="dimmed">
                  {e.body}
                </Text>
              </div>
            ))}
          </Stack>
        )}
      </div>
    </Stack>
  );
}

function MatterStats({ m, slug }: { m: MatterDetail; slug: string }) {
  const practice = usePracticeLabels(slug);
  return (
    <div className="tst-panel">
      <SimpleGrid cols={{ base: 2, sm: 4, lg: 6 }} spacing="md">
        <Stat label="Practice">{practice(m.practice)}</Stat>
        <Stat label="Lead">{m.lead?.name ?? '—'}</Stat>
        <Stat label="Phase">{m.phase ? humanize(m.phase) : '—'}</Stat>
        <Stat label="Progress">{m.progress_pct}%</Stat>
        <Stat label="Hours / budget">
          {formatHours(m.worked_hours)} / {formatHours(m.budget_hours)}
        </Stat>
        <Stat label="Hours last month">{formatHours(m.hours_last_month)}</Stat>
        <Stat label="WIP">{formatMoneyWhole(m.wip_cents)}</Stat>
        <Stat label="Expected fees">{formatMoneyWhole(m.expected_fees_cents)}</Stat>
        <Stat label="Opened / due">
          {m.opened_label} / {m.due_label}
          {m.overdue && (
            <Badge ml={6} size="xs" color="red">
              overdue
            </Badge>
          )}
        </Stat>
        <Stat label="Margin">
          <Explain metric="matter_margin" entity={m.id} label="matter margin" />
        </Stat>
        <Stat label="Realisation">
          <RealisationValue slug={slug} matterId={m.id} />
          <Explain metric="realisation" entity={m.id} label="realisation" />
        </Stat>
        <Stat label="Outlook">
          <Explain metric="outlook" entity={m.id} label="the outlook" />
        </Stat>
      </SimpleGrid>
      {m.risk_notes.length > 0 && (
        <Text size="sm" c="orange" mt="sm" data-testid="risk-notes">
          Risk {m.risk}: {m.risk_notes.join('; ')}
        </Text>
      )}
    </div>
  );
}

function ConflictPanel({
  m,
  run,
  busy,
}: {
  m: MatterDetail;
  run: (a: MatterAction) => void;
  busy: boolean;
}) {
  return (
    <Alert color="orange" title="Conflict of interest" data-testid="conflict">
      <Text size="sm" mb="xs">
        This instruction is adverse to {m.adverse || 'a current client'}. It cannot open without a
        waiver.
      </Text>
      <Group>
        <Button size="xs" loading={busy} onClick={() => run({ kind: 'waiver', advance: false })}>
          Seek a waiver
        </Button>
        <Button
          size="xs"
          variant="default"
          loading={busy}
          onClick={() => run({ kind: 'waiver', advance: true })}
        >
          Seek an advance waiver
        </Button>
      </Group>
    </Alert>
  );
}

function ForumPanel({ m, run }: { m: MatterDetail; run: (a: MatterAction) => void }) {
  const [court, setCourt] = useState<string | null>(null);
  return (
    <div className="tst-panel">
      <h3 className="tst-ptitle">Forum</h3>
      <Group>
        <Select
          aria-label="Forum"
          placeholder="Choose a court"
          data={m.forums}
          value={court}
          onChange={setCourt}
        />
        <Button disabled={!court} onClick={() => court && run({ kind: 'forum', court })}>
          File here
        </Button>
      </Group>
    </div>
  );
}

function PhaseTimeline({ m }: { m: MatterDetail }) {
  const color = { done: 'teal', current: 'accent', next: 'dark.4' } as const;
  return (
    <div className="tst-panel" data-testid="phases">
      <h3 className="tst-ptitle">Phases</h3>
      <Progress.Root size={22}>
        {m.phases.map((p) => (
          <Progress.Section key={p.key} value={p.share_pct} color={color[p.state]}>
            <Progress.Label>{humanize(p.key)}</Progress.Label>
          </Progress.Section>
        ))}
      </Progress.Root>
    </div>
  );
}

function PersonCard({
  p,
  slug,
  children,
  draggable,
}: {
  p: BoardPerson;
  slug: string;
  children?: React.ReactNode;
  draggable: boolean;
}) {
  const practice = usePracticeLabels(slug);
  const onDragStart = (e: DragEvent<HTMLDivElement>) => {
    e.dataTransfer.setData(DRAG_TYPE, String(p.person.id));
    e.dataTransfer.effectAllowed = 'copy';
  };
  return (
    <div
      className="tst-panel"
      style={{ padding: '8px 10px', cursor: draggable ? 'grab' : undefined }}
      draggable={draggable}
      onDragStart={draggable ? onDragStart : undefined}
      data-testid={p.on_team ? 'team-member' : 'board-person'}
      data-person={p.person.name}
    >
      <Group justify="space-between" wrap="nowrap">
        <div>
          <Link to={`/game/${slug}/people/${p.person.id}`}>{p.person.name}</Link>
          <Text size="xs" c="dimmed">
            {humanize(p.level)} · {practice(p.home_practice)} · familiarity{' '}
            <AttributeRange range={p.familiarity} label="Familiarity" />
          </Text>
          <Text size="xs" c="dimmed" className="tst-num">
            {formatHours(p.free_hours)} free · {formatHours(p.planned_hours)} planned ·{' '}
            {formatHours(p.hours_last_month)} last month
          </Text>
        </div>
        <StrainBar strain={p.strain} burntOut={p.burnt_out} compact />
      </Group>
      {p.warnings.map((w) => (
        <Text key={w} size="xs" c="orange" data-testid="strain-warning">
          {w}
        </Text>
      ))}
      {children}
    </div>
  );
}

function TeamControls({
  p,
  run,
  busy,
  isLead,
}: {
  p: BoardPerson;
  run: (a: MatterAction) => void;
  busy: boolean;
  isLead: boolean;
}) {
  const [hours, setHours] = useState<string | number>(p.planned_here);
  const partner = p.level === 'equity_partner' || p.level === 'income_partner';
  return (
    <Group gap="xs" mt={6}>
      <NumberInput
        size="xs"
        w={90}
        min={1}
        max={400}
        value={hours}
        onChange={setHours}
        aria-label={`Hours a month for ${p.person.name}`}
        suffix=" h"
      />
      <Button
        size="xs"
        variant="default"
        loading={busy}
        onClick={() => run({ kind: 'hours', personId: p.person.id, hours: Number(hours) })}
      >
        Set
      </Button>
      {isLead ? (
        <Badge variant="light">Lead</Badge>
      ) : (
        partner && (
          <Button
            size="xs"
            variant="subtle"
            onClick={() => run({ kind: 'lead', personId: p.person.id })}
          >
            Make lead
          </Button>
        )
      )}
      <Button
        size="xs"
        variant="subtle"
        color="red"
        onClick={() => run({ kind: 'remove', personId: p.person.id })}
        aria-label={`Remove ${p.person.name}`}
      >
        Remove
      </Button>
    </Group>
  );
}

function StaffingBoardPanel({
  m,
  board,
  run,
  busy,
  slug,
}: {
  m: MatterDetail;
  board: StaffingBoard;
  run: (a: MatterAction) => void;
  busy: boolean;
  slug: string;
}) {
  const [hours, setHours] = useState<string | number>(DEFAULT_HOURS);
  const [over, setOver] = useState(false);
  const open = m.status === 'open';
  const team = board.people.filter((p) => p.on_team);
  const others = board.people.filter((p) => !p.on_team);
  const assign = (personId: number) => run({ kind: 'assign', personId, hours: Number(hours) });
  const onDrop = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setOver(false);
    const id = Number(e.dataTransfer.getData(DRAG_TYPE));
    if (id) assign(id);
  };
  return (
    <div className="tst-panel" data-testid="staffing-board">
      <Group justify="space-between" mb="sm">
        <h3 className="tst-ptitle" style={{ margin: 0 }}>
          Staffing board · {board.practice_label}
        </h3>
        {open && (
          <Group gap="xs">
            <NumberInput
              size="xs"
              w={110}
              min={1}
              max={400}
              value={hours}
              onChange={setHours}
              label="Hours a month"
              suffix=" h"
            />
            <Button
              size="xs"
              variant="default"
              mt={18}
              loading={busy}
              onClick={() => run({ kind: 'default' })}
            >
              Default staffing
            </Button>
          </Group>
        )}
      </Group>
      <SimpleGrid cols={{ base: 1, md: 2 }}>
        <div
          onDragOver={(e) => {
            if (!open) return;
            e.preventDefault();
            setOver(true);
          }}
          onDragLeave={() => setOver(false)}
          onDrop={open ? onDrop : undefined}
          data-testid="team-drop"
          style={{
            minHeight: 120,
            borderRadius: 10,
            padding: 8,
            border: `1px dashed var(${over ? '--ptk-accent' : '--ptk-border'})`,
          }}
        >
          <Text size="sm" fw={600} mb={6}>
            Team {open && <span className="tst-muted">(drop people here)</span>}
          </Text>
          <Stack gap={6}>
            {team.length === 0 && (
              <Text size="sm" c="dimmed">
                Nobody is staffed.
              </Text>
            )}
            {team.map((p) => (
              <PersonCard key={p.person.id} p={p} slug={slug} draggable={false}>
                {open && (
                  <TeamControls
                    key={p.planned_here}
                    p={p}
                    run={run}
                    busy={busy}
                    isLead={m.lead?.id === p.person.id}
                  />
                )}
              </PersonCard>
            ))}
          </Stack>
        </div>
        <div>
          <Text size="sm" fw={600} mb={6}>
            Available
          </Text>
          <Stack gap={6} mah={560} style={{ overflowY: 'auto' }}>
            {others.map((p) => (
              <PersonCard key={p.person.id} p={p} slug={slug} draggable={open}>
                {open && (
                  <Button
                    size="compact-xs"
                    variant="light"
                    mt={4}
                    onClick={() => assign(p.person.id)}
                    aria-label={`Add ${p.person.name}`}
                  >
                    Add
                  </Button>
                )}
              </PersonCard>
            ))}
          </Stack>
        </div>
      </SimpleGrid>
    </div>
  );
}

function RealisationValue({ slug, matterId }: { slug: string; matterId: number }) {
  const bp = useMatterMoneyById(slug).get(matterId)?.realisation_bp;
  return (
    <span data-testid="matter-realisation">
      {bp === null || bp === undefined ? '—' : formatBpShort(bp)}
    </span>
  );
}

function BillsPanel({ m, slug }: { m: MatterDetail; slug: string }) {
  const money = useMatterMoneyById(slug).get(m.id);
  const bills = (useRecentBills(slug).data ?? []).filter((b) => b.matter_id === m.id);
  const writeDown = useWriteDown(slug);
  const [pct, setPct] = useState<string | number>(0);
  return (
    <div className="tst-panel" data-testid="bills">
      <h3 className="tst-ptitle">Bills</h3>
      {!money ? (
        <Text size="sm" c="dimmed">
          No billing terms yet: work in progress stands at {formatMoneyWhole(m.wip_cents)} at
          standard rates.
        </Text>
      ) : (
        <Stack gap="sm">
          <SimpleGrid cols={{ base: 2, sm: 3, lg: 6 }}>
            <Stat label="Billing model">{humanize(money.model)}</Stat>
            <Stat label="Unbilled WIP">{formatMoneyWhole(money.wip_cents)}</Stat>
            <Stat label="Billed">
              <span data-testid="matter-billed">{formatMoneyWhole(money.billed_cents)}</span>
            </Stat>
            <Stat label="Collected">{formatMoneyWhole(money.collected_cents)}</Stat>
            <Stat label="On account">{formatMoneyWhole(money.funds_cents)}</Stat>
            <Stat label="Write-down for the next bill">{formatBpShort(money.writedown_bp)}</Stat>
          </SimpleGrid>
          {m.status === 'open' && (
            <Group gap="xs" align="end">
              <NumberInput
                size="xs"
                w={120}
                min={0}
                max={50}
                value={pct}
                onChange={setPct}
                label="Write the next bill down"
                suffix="%"
              />
              <Button
                size="xs"
                variant="default"
                loading={writeDown.isPending}
                onClick={() =>
                  writeDown.mutate({ matterId: m.id, bp: Math.round(Number(pct) * 100) })
                }
              >
                Set write-down
              </Button>
              {writeDown.error && (
                <Text size="xs" c="red">
                  {writeDown.error.message}
                </Text>
              )}
            </Group>
          )}
          {bills.length === 0 ? (
            <Text size="sm" c="dimmed">
              No open or recent bills.
            </Text>
          ) : (
            <table className="tst-table" aria-label="Matter bills">
              <thead>
                <tr>
                  <th>Issued</th>
                  <th>Billed</th>
                  <th>Outstanding</th>
                  <th>Age</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {bills.map((b) => (
                  <tr key={b.id} data-testid="matter-bill">
                    <td>{b.issued_label}</td>
                    <td className="tst-num">{formatMoneyWhole(b.billed_cents)}</td>
                    <td className="tst-num">{formatMoneyWhole(b.outstanding_cents)}</td>
                    <td className="tst-num">{b.age_days} days</td>
                    <td>
                      {humanize(b.status)}
                      {b.dispute && ' (disputed)'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </Stack>
      )}
    </div>
  );
}
