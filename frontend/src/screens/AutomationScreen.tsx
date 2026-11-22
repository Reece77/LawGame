// Ported from TST frontend/src/screens/AutomationScreen.tsx @ 80a38079; changed: Partner
// Track's areas (spec 9.4), one firm (no company switcher), no Automate everything preview or
// headcount targets, a per-decision and a monthly limit, guardrails edited inline, proposals
// answered here, and the month's digest. Every rule is the engine's; this only shows and sends.
import {
  Alert,
  Badge,
  Button,
  Group,
  Modal,
  NumberInput,
  Select,
  Stack,
  Switch,
  Text,
  Title,
} from '@mantine/core';
import { createColumnHelper, useTable } from '@tanstack/react-table';
import { useState } from 'react';
import { Link, useParams, useSearchParams } from 'react-router';
import { DataTable } from '../components/DataTable';
import { OwnerRecordPanel } from '../components/OwnerRecord';
import {
  useAutomation,
  useAutomationAction,
  useDigest,
  type Area,
  type Automation,
  type Proposal,
} from '../lib/automation';
import { formatMoney, formatMoneyWhole, humanize } from '../lib/format';
import { gameTableFeatures, type GameTableFeatures } from '../lib/table';

const helper = createColumnHelper<GameTableFeatures, Area>();
const CENTS = 100;
const STATUS: Record<string, { label: string; color: string }> = {
  automated: { label: 'Automated', color: 'teal' },
  manual: { label: 'Manage myself', color: 'gray' },
  unavailable: { label: "Can't automate yet", color: 'yellow' },
};

function rowKey(a: Area): string {
  return `${a.area}:${a.slot}`;
}

export function AutomationScreen() {
  const { slug = '' } = useParams();
  const auto = useAutomation(slug);
  if (auto.error) return <Text c="red">{auto.error.message}</Text>;
  if (!auto.data) return <Text c="dimmed">Loading…</Text>;
  return <Body slug={slug} a={auto.data} />;
}

function Body({ slug, a }: { slug: string; a: Automation }) {
  const action = useAutomationAction(slug);
  const [editing, setEditing] = useState<Area | null>(null);
  const [params] = useSearchParams();
  const month = params.get('month');
  const columns = helper.columns([
    helper.accessor('label', { header: 'Area', sortFn: 'alphanumeric' }),
    helper.display({
      id: 'status',
      header: 'Status',
      cell: ({ row }) => {
        const s = STATUS[row.original.status] ?? STATUS.manual;
        return (
          <Stack gap={2}>
            <Badge size="sm" color={s.color} variant="light">
              {s.label}
            </Badge>
            {row.original.reason && (
              <Text size="xs" c="dimmed">
                {row.original.reason}
              </Text>
            )}
          </Stack>
        );
      },
    }),
    helper.display({
      id: 'owner',
      header: 'Owner',
      cell: ({ row }) => <OwnerCell slug={slug} area={row.original} act={action.mutate} />,
    }),
    helper.accessor((r) => r.limit_cents ?? -1, {
      id: 'limit',
      header: 'Limit (decision / month)',
      cell: ({ row }) =>
        row.original.limit_cents === null || row.original.limit_cents === undefined
          ? '—'
          : `${formatMoneyWhole(row.original.limit_cents)} / ${formatMoneyWhole(row.original.monthly_cents ?? 0)}`,
    }),
    helper.accessor((r) => r.priority ?? 99, {
      id: 'priority',
      header: 'Priority',
      cell: ({ row }) => row.original.priority ?? '—',
    }),
    helper.accessor('energy', { header: 'Workload' }),
    helper.display({
      id: 'last',
      header: 'Last month',
      cell: ({ row }) =>
        row.original.last_month.length === 0 ? (
          <Text size="xs" c="dimmed">
            —
          </Text>
        ) : (
          <Stack gap={0}>
            {row.original.last_month.slice(0, 3).map((l, i) => (
              <Text key={i} size="xs">
                {l.text}
              </Text>
            ))}
          </Stack>
        ),
    }),
    helper.display({
      id: 'edit',
      header: '',
      cell: ({ row }) =>
        row.original.status === 'automated' ? (
          <Button
            size="compact-xs"
            variant="subtle"
            onClick={() => setEditing(row.original)}
            data-testid={`settings-${rowKey(row.original)}`}
          >
            Limits and guardrails
          </Button>
        ) : null,
    }),
  ]);
  const table = useTable({
    features: gameTableFeatures,
    columns,
    data: a.areas,
    getRowId: rowKey,
  });
  const pending = a.proposals.filter((p) => p.status === 'pending');
  return (
    <Stack gap="lg" data-testid="automation-screen">
      <Group justify="space-between">
        <Title order={2}>Automation</Title>
        <Text size="sm" c="dimmed">
          {a.month_label}. One-offs and anything at or above a limit come to you as proposals;
          critical events always do.
        </Text>
      </Group>
      {action.error && (
        <Alert
          color="red"
          withCloseButton
          onClose={() => action.reset()}
          data-testid="automation-error"
        >
          {action.error.message}
        </Alert>
      )}
      <div className="tst-panel">
        <DataTable table={table} label="Areas" rowTestId="area-row" empty="No areas." />
      </div>
      <Proposals slug={slug} proposals={pending} act={action.mutate} />
      {month !== null && <DigestPanel slug={slug} turn={Number(month)} />}
      <OwnerRecordPanel slug={slug} owners={a.owners} />
      {editing && (
        <SettingsModal
          area={editing}
          onClose={() => setEditing(null)}
          act={(cmd) => {
            action.mutate(cmd);
            setEditing(null);
          }}
        />
      )}
    </Stack>
  );
}

type Act = ReturnType<typeof useAutomationAction>['mutate'];

function OwnerCell({ slug, area, act }: { slug: string; area: Area; act: Act }) {
  const [pick, setPick] = useState<string | null>(null);
  if (area.owner) {
    return (
      <Group gap={6} wrap="nowrap">
        <Link to={`/game/${slug}/people/${area.owner.person_id}`}>{area.owner.name}</Link>
        <Badge size="xs" variant="outline">
          {area.owner.fit} fit
        </Badge>
        <Button
          size="compact-xs"
          variant="subtle"
          color="red"
          onClick={() => act({ kind: 'take_over', area: area.area, slot: area.slot })}
          data-testid={`take-over-${rowKey(area)}`}
        >
          Take over
        </Button>
      </Group>
    );
  }
  if (area.eligible.length === 0) return <Text size="xs">You</Text>;
  return (
    <Group gap={6} wrap="nowrap">
      <Select
        size="xs"
        w={190}
        aria-label={`Owner for ${area.label}`}
        placeholder="Give to…"
        data={area.eligible.map((p) => ({
          value: String(p.person_id),
          label: `${p.name} (${p.fit} fit)`,
        }))}
        value={pick}
        onChange={setPick}
        data-testid={`owner-pick-${rowKey(area)}`}
      />
      <Button
        size="compact-xs"
        disabled={pick === null}
        onClick={() =>
          pick !== null &&
          act({ kind: 'give', area: area.area, slot: area.slot, personId: Number(pick) })
        }
        data-testid={`give-${rowKey(area)}`}
      >
        Give
      </Button>
    </Group>
  );
}

function Proposals({ slug, proposals, act }: { slug: string; proposals: Proposal[]; act: Act }) {
  return (
    <div className="tst-panel" data-testid="proposals">
      <h3 className="tst-ptitle">Proposals waiting ({proposals.length})</h3>
      {proposals.length === 0 && <Text c="dimmed">Nothing waits for you.</Text>}
      <Stack gap="xs">
        {proposals.map((p) => (
          <div key={p.id} data-testid="proposal">
            <Group justify="space-between" wrap="nowrap">
              <Text fw={600} size="sm">
                {p.title}
              </Text>
              <Group gap={6}>
                <Button
                  size="compact-xs"
                  onClick={() => act({ kind: 'answer', proposalId: p.id, approve: true })}
                  data-testid={`approve-${p.id}`}
                >
                  Approve
                </Button>
                <Button
                  size="compact-xs"
                  variant="default"
                  onClick={() => act({ kind: 'answer', proposalId: p.id, approve: false })}
                >
                  Decline
                </Button>
              </Group>
            </Group>
            <Text size="xs" c="dimmed">
              <Link to={`/game/${slug}/people/${p.person_id}`}>{p.name}</Link> · {p.area_label} ·{' '}
              {p.why} · commits {formatMoney(p.commitment_cents)} · expires {p.expires_label}
            </Text>
            <Text size="sm">{p.recommendation}</Text>
          </div>
        ))}
      </Stack>
    </div>
  );
}

function DigestPanel({ slug, turn }: { slug: string; turn: number }) {
  const digest = useDigest(slug, turn);
  if (!digest.data) return null;
  const d = digest.data;
  return (
    <div className="tst-panel" data-testid="digest">
      <h3 className="tst-ptitle">Your month: {d.month_label}</h3>
      <Stack gap="sm">
        {d.areas.map((area) => (
          <div key={`${area.area}:${area.slot}`}>
            <Text fw={600} size="sm">
              {area.label} · {area.owner}
              {area.committed_cents > 0 &&
                ` · ${formatMoney(area.committed_cents)} of ${formatMoney(area.monthly_cents)} committed`}
              {area.near_limit > 0 && (
                <Badge ml={6} size="xs" color="orange">
                  near a limit
                </Badge>
              )}
            </Text>
            {area.lines
              .filter((l) => l.kind !== 'stretched')
              .map((l, i) => (
                <Text key={i} size="xs">
                  {l.kind === 'proposal' ? 'Proposed: ' : ''}
                  {l.link_kind === 'person' && l.link_id !== null ? (
                    <Link to={`/game/${slug}/people/${l.link_id}`}>{l.text}</Link>
                  ) : l.link_kind === 'client' && l.link_id !== null ? (
                    <Link to={`/game/${slug}/clients/${l.link_id}`}>{l.text}</Link>
                  ) : (
                    l.text
                  )}
                </Text>
              ))}
            <Text size="xs" c="dimmed" fs="italic">
              “{area.note}”
            </Text>
          </div>
        ))}
      </Stack>
    </div>
  );
}

function SettingsModal({
  area,
  onClose,
  act,
}: {
  area: Area;
  onClose: () => void;
  act: (cmd: Parameters<Act>[0]) => void;
}) {
  const [limit, setLimit] = useState<number>((area.limit_cents ?? 0) / CENTS);
  const [monthly, setMonthly] = useState<number>((area.monthly_cents ?? 0) / CENTS);
  const [priority, setPriority] = useState<number>(area.priority ?? 0);
  const [events, setEvents] = useState<boolean>(area.answer_events ?? true);
  const [rails, setRails] = useState<Record<string, number>>(
    Object.fromEntries(area.guardrails.map((g) => [g.key, g.value])),
  );
  return (
    <Modal opened onClose={onClose} title={area.label} data-testid="area-settings">
      <Stack gap="xs">
        <NumberInput
          label="Limit a decision ($)"
          value={limit}
          min={0}
          onChange={(v) => setLimit(Number(v))}
          data-testid="limit-input"
        />
        <NumberInput
          label="Limit a month ($)"
          value={monthly}
          min={0}
          onChange={(v) => setMonthly(Number(v))}
        />
        <NumberInput
          label="Priority (lowest runs first)"
          value={priority}
          min={0}
          onChange={(v) => setPriority(Number(v))}
        />
        <Switch
          label="Let them answer routine events"
          checked={events}
          onChange={(e) => setEvents(e.currentTarget.checked)}
        />
        {area.guardrails.map((g) => (
          <NumberInput
            key={g.key}
            label={g.label || humanize(g.key)}
            value={rails[g.key]}
            min={g.min}
            max={g.max}
            onChange={(v) => setRails({ ...rails, [g.key]: Number(v) })}
          />
        ))}
        <Group justify="flex-end">
          <Button variant="default" onClick={onClose}>
            Cancel
          </Button>
          <Button
            data-testid="save-settings"
            onClick={() =>
              act({
                kind: 'settings',
                area: area.area,
                slot: area.slot,
                limitCents: Math.round(limit * CENTS),
                monthlyCents: Math.round(monthly * CENTS),
                priority,
                answerEvents: events,
                guardrails: Object.entries(rails).map(([key, value]) => ({ key, value })),
              })
            }
          >
            Save
          </Button>
        </Group>
      </Stack>
    </Modal>
  );
}
