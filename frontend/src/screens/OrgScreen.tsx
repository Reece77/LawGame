import {
  Alert,
  Badge,
  Button,
  Group,
  NumberInput,
  Select,
  SimpleGrid,
  Stack,
  Table,
  Text,
  TextInput,
  Title,
} from '@mantine/core';
import { createColumnHelper, tableFeatures, useTable } from '@tanstack/react-table';
import { useMemo, useState } from 'react';
import { Link, useParams } from 'react-router';
import { humanize } from '../lib/format';
import {
  supervisorColor,
  useOrg,
  useOrgAction,
  type Org,
  type OrgMember,
  type OrgUnit,
  type Plan,
  type PlanBody,
} from '../lib/org';

// The Org screen (PT-M2; TST formulas.md 13): practice groups and teams, who sits where,
// each supervising partner's load, and delegated hiring plans. Every rule is the engine's.
const ROOT = 'root';
const CHANNELS = ['job_post', 'recruiter', 'referral', 'campus', 'any'];

function Panel({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="tst-panel">
      <h3 className="tst-ptitle">{title}</h3>
      {children}
    </div>
  );
}

function unitOptions(org: Org) {
  return [
    { value: ROOT, label: 'Firm (no group)' },
    ...org.units.map((u) => ({ value: String(u.id), label: u.name })),
  ];
}

const toUnit = (value: string | null): number | null =>
  value === null || value === ROOT ? null : Number(value);

export function OrgScreen() {
  const { slug = '' } = useParams();
  const org = useOrg(slug);
  const action = useOrgAction(slug);
  if (org.error) return <Text c="red">{org.error.message}</Text>;
  if (!org.data) return <Text c="dimmed">Loading…</Text>;
  const o = org.data;
  const groups = o.units.filter((u) => u.kind === 'practice_group');
  const teams = o.units.filter((u) => u.kind === 'team');
  const ordered = [
    ...groups.flatMap((g) => [g, ...teams.filter((t) => t.parent_id === g.id)]),
    ...teams.filter((t) => t.parent_id === null),
  ];
  return (
    <Stack gap="md">
      <Title order={2}>Org</Title>
      {action.error && (
        <Alert color="red" data-testid="org-error" withCloseButton onClose={() => action.reset()}>
          {action.error.message}
        </Alert>
      )}
      <SimpleGrid cols={{ base: 1, md: 2 }}>
        <NewUnits org={o} act={action.mutate} busy={action.isPending} />
        <Supervisors org={o} slug={slug} />
      </SimpleGrid>
      <SimpleGrid cols={{ base: 1, md: 2 }} data-testid="org-units">
        {ordered.map((u) => (
          <UnitCard key={u.id} unit={u} org={o} slug={slug} act={action.mutate} />
        ))}
      </SimpleGrid>
      <Panel title={`Firm (${o.founder?.name ?? 'no founding partner'})`}>
        <MemberTable members={o.root_members} org={o} slug={slug} act={action.mutate} />
      </Panel>
      <Plans org={o} act={action.mutate} busy={action.isPending} />
    </Stack>
  );
}

type Act = ReturnType<typeof useOrgAction>['mutate'];

function NewUnits({ org, act, busy }: { org: Org; act: Act; busy: boolean }) {
  const [practice, setPractice] = useState<string | null>(null);
  const [team, setTeam] = useState('');
  const [parent, setParent] = useState<string | null>(ROOT);
  const parents = [
    { value: ROOT, label: 'Firm' },
    ...org.units
      .filter((u) => u.kind === 'practice_group')
      .map((u) => ({ value: String(u.id), label: u.name })),
  ];
  return (
    <Panel title="Practice groups and teams">
      <Text size="sm" c="dimmed" mb="xs" data-testid="unlock-note">
        {org.practice_groups_unlocked
          ? `${org.lawyers} lawyers: one practice group per practice.`
          : `Practice groups unlock at ${org.unlock_at} lawyers (you have ${org.lawyers}).`}
      </Text>
      <Group align="flex-end" mb="sm">
        <Select
          label="Practice"
          placeholder="Choose a practice"
          data={org.open_practices.map((p) => ({ value: p.key, label: p.label }))}
          value={practice}
          onChange={setPractice}
          disabled={!org.practice_groups_unlocked}
        />
        <Button
          disabled={!org.practice_groups_unlocked || practice === null}
          loading={busy}
          onClick={() => {
            if (practice) act({ kind: 'create_unit', body: { kind: 'practice_group', practice } });
            setPractice(null);
          }}
        >
          Create practice group
        </Button>
      </Group>
      <Group align="flex-end">
        <TextInput
          label="Team name"
          value={team}
          onChange={(e) => setTeam(e.currentTarget.value)}
        />
        <Select label="Under" data={parents} value={parent} onChange={setParent} />
        <Button
          variant="light"
          disabled={team.trim() === ''}
          loading={busy}
          onClick={() => {
            act({
              kind: 'create_unit',
              body: { kind: 'team', name: team, parent_id: toUnit(parent) },
            });
            setTeam('');
          }}
        >
          Create team
        </Button>
      </Group>
    </Panel>
  );
}

function Supervisors({ org, slug }: { org: Org; slug: string }) {
  return (
    <Panel title="Supervising partners">
      <Table data-testid="supervisors">
        <Table.Thead>
          <Table.Tr>
            <Table.Th>Supervisor</Table.Th>
            <Table.Th ta="right">Direct reports</Table.Th>
            <Table.Th>Comes across as</Table.Th>
          </Table.Tr>
        </Table.Thead>
        <Table.Tbody>
          {org.supervisors.map((s) => (
            <Table.Tr key={s.person.id}>
              <Table.Td>
                <Link to={`/game/${slug}/people/${s.person.id}`}>{s.person.name}</Link>
              </Table.Td>
              <Table.Td ta="right" className="tst-num">
                {s.reports}
                {s.over_span && (
                  <Badge ml={6} size="xs" color="orange" variant="light">
                    over span
                  </Badge>
                )}
              </Table.Td>
              <Table.Td>
                <Badge color={supervisorColor(s.label)} variant="light">
                  {s.label}
                </Badge>
              </Table.Td>
            </Table.Tr>
          ))}
        </Table.Tbody>
      </Table>
    </Panel>
  );
}

function UnitCard({ unit, org, slug, act }: { unit: OrgUnit; org: Org; slug: string; act: Act }) {
  const parent = org.units.find((u) => u.id === unit.parent_id);
  return (
    <div className="tst-panel" data-testid={`unit-${unit.id}`}>
      <Group justify="space-between" mb="xs">
        <div>
          <h3 className="tst-ptitle">{unit.name}</h3>
          <Text size="xs" c="dimmed">
            {unit.kind === 'practice_group'
              ? 'Practice group'
              : `Team${parent ? ` in ${parent.name}` : ''}`}
            {unit.campus_target != null && ` · campus target ${unit.campus_target}`}
          </Text>
        </div>
        <Button
          size="xs"
          color="red"
          variant="subtle"
          onClick={() => act({ kind: 'dissolve_unit', unitId: unit.id })}
        >
          Dissolve
        </Button>
      </Group>
      <Select
        label={`Leader of ${unit.name}`}
        placeholder={unit.members.length ? 'No leader' : 'Move someone in first'}
        data={unit.members.map((m) => ({ value: String(m.id), label: m.name }))}
        value={unit.leader ? String(unit.leader.id) : null}
        onChange={(v) =>
          act({ kind: 'set_leader', unitId: unit.id, personId: v ? Number(v) : null })
        }
        clearable
        mb="xs"
      />
      <MemberTable members={unit.members} org={org} slug={slug} act={act} />
    </div>
  );
}

function MemberTable({
  members,
  org,
  slug,
  act,
}: {
  members: OrgMember[];
  org: Org;
  slug: string;
  act: Act;
}) {
  if (members.length === 0) return <Text c="dimmed">Nobody here yet.</Text>;
  const names = new Map<number, string>();
  for (const m of [...org.root_members, ...org.units.flatMap((u) => u.members)])
    names.set(m.id, m.name);
  if (org.founder) names.set(org.founder.id, org.founder.name);
  return (
    <Table>
      <Table.Thead>
        <Table.Tr>
          <Table.Th>Name</Table.Th>
          <Table.Th>Level</Table.Th>
          <Table.Th>Supervisor</Table.Th>
          <Table.Th>Move to</Table.Th>
        </Table.Tr>
      </Table.Thead>
      <Table.Tbody>
        {members.map((m) => (
          <Table.Tr key={m.id}>
            <Table.Td>
              <Link to={`/game/${slug}/people/${m.id}`}>{m.name}</Link>
              {m.leads_unit_id != null && (
                <Badge ml={6} size="xs" variant="light">
                  leader
                </Badge>
              )}
            </Table.Td>
            <Table.Td>{humanize(m.level)}</Table.Td>
            <Table.Td>{m.supervisor_id != null ? names.get(m.supervisor_id) : '—'}</Table.Td>
            <Table.Td>
              <Select
                aria-label={`Move ${m.name}`}
                size="xs"
                data={unitOptions(org)}
                value={null}
                placeholder="Move…"
                disabled={m.leads_unit_id != null}
                onChange={(v) =>
                  v !== null && act({ kind: 'move_person', personId: m.id, unitId: toUnit(v) })
                }
              />
            </Table.Td>
          </Table.Tr>
        ))}
      </Table.Tbody>
    </Table>
  );
}

const features = tableFeatures({});
const helper = createColumnHelper<typeof features, Plan>();

function planColumns(act: Act) {
  return [
    helper.display({ id: 'owner', header: 'Delegate', cell: ({ row }) => row.original.owner.name }),
    helper.display({ id: 'unit', header: 'Joins', cell: ({ row }) => row.original.unit_name }),
    helper.display({ id: 'role', header: 'Hires', cell: ({ row }) => row.original.role_label }),
    helper.display({
      id: 'progress',
      header: 'Hired',
      cell: ({ row }) => (
        <span className="tst-num">
          {row.original.hired} / {row.original.target}
        </span>
      ),
    }),
    helper.display({
      id: 'channel',
      header: 'Channel',
      cell: ({ row }) => (row.original.campus ? 'Campus target' : humanize(row.original.channel)),
    }),
    helper.display({
      id: 'status',
      header: 'Status',
      cell: ({ row }) => humanize(row.original.status),
    }),
    helper.display({
      id: 'activity',
      header: 'Last month',
      cell: ({ row }) => row.original.last_activity ?? '—',
    }),
    helper.display({
      id: 'close',
      header: '',
      cell: ({ row }) => (
        <Button
          size="xs"
          variant="subtle"
          onClick={() => act({ kind: 'close_plan', planId: row.original.id })}
        >
          Close
        </Button>
      ),
    }),
  ];
}

function Plans({ org, act, busy }: { org: Org; act: Act; busy: boolean }) {
  const columns = useMemo(() => planColumns(act), [act]);
  const table = useTable({ features, columns, data: org.plans });
  const [owner, setOwner] = useState<string | null>(null);
  const [role, setRole] = useState<string | null>(null);
  const [channel, setChannel] = useState<string | null>('job_post');
  const [unit, setUnit] = useState<string | null>(ROOT);
  const [target, setTarget] = useState<number | string>(1);
  const ready = owner !== null && role !== null && channel !== null;
  const open = () => {
    if (!ready) return;
    const body: PlanBody = {
      owner_id: Number(owner),
      role,
      channel: channel as PlanBody['channel'],
      target: Number(target),
      unit_id: toUnit(unit),
    };
    act({ kind: 'create_plan', body });
  };
  return (
    <Panel title="Hiring plans">
      <Text size="sm" c="dimmed" mb="xs">
        A practice group leader or a recruiting manager runs a plan each month with their own time
        {org.delegates_ready ? '.' : '; delegates start work once hiring is built.'}
      </Text>
      <Group align="flex-end" mb="sm" wrap="wrap">
        <Select
          label="Delegate"
          placeholder={org.plan_owners.length ? 'Choose' : 'Set a leader first'}
          data={org.plan_owners.map((p) => ({ value: String(p.id), label: p.name }))}
          value={owner}
          onChange={setOwner}
        />
        <Select
          label="Role"
          data={org.roles.map((r) => ({ value: r.key, label: r.label }))}
          value={role}
          onChange={setRole}
          searchable
        />
        <Select
          label="Channel"
          data={CHANNELS.map((c) => ({
            value: c,
            label: c === 'campus' ? 'Campus target' : humanize(c),
          }))}
          value={channel}
          onChange={setChannel}
        />
        <Select label="Joins" data={unitOptions(org)} value={unit} onChange={setUnit} />
        <NumberInput label="Hires" min={1} max={50} value={target} onChange={setTarget} w={90} />
        <Button disabled={!ready} loading={busy} onClick={open}>
          Open plan
        </Button>
      </Group>
      {org.plans.length === 0 ? (
        <Text c="dimmed">No hiring plans.</Text>
      ) : (
        <div className="tst-table-wrap">
          <Table striped data-testid="plans-table">
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
      )}
    </Panel>
  );
}
