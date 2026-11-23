import {
  Alert,
  Badge,
  Button,
  Checkbox,
  Group,
  Select,
  Stack,
  Tabs,
  Text,
  Title,
} from '@mantine/core';
import { createColumnHelper, useTable } from '@tanstack/react-table';
import { useMemo, useState } from 'react';
import { useParams } from 'react-router';
import { DataTable } from '../components/DataTable';
import {
  useMakeSubmission,
  usePracticeLabels,
  useRankings,
  type BandFirm,
  type LeagueRow,
  type PersonBand,
  type PlacesRow,
  type PlayerPlace,
  type PracticeBands,
  type Rankings,
  type Submission,
  type SubmissionMatter,
  type SubmissionReferee,
  type TableRow,
} from '../lib/api';
import { formatMoneyShort, formatWhole, humanize } from '../lib/format';
import { bandHistoryText, bandText, toggleId } from '../lib/standing';
import { gameTableFeatures, type GameTableFeatures } from '../lib/table';

// Rankings (spec 12.2-12.3, 16; PT-M16): the spring revenue and PEP tables, the quarter's
// league tables by practice, October's directory bands by practice with the firm's band in
// every year, ranked individuals, Best places to work, and the March-April submission. Every
// number is the API's; the firm's own row is highlighted.

const you = (name: string, isPlayer: boolean) => (
  <span>
    {name}
    {isPlayer && (
      <Badge ml="xs" size="xs" variant="light">
        You
      </Badge>
    )}
  </span>
);
const num = (v: number | string) => <span className="tst-num">{v}</span>;

// --- Spring tables ---------------------------------------------------------------------------

const tableHelper = createColumnHelper<GameTableFeatures, TableRow>();
const tableColumns = (valueHeader: string) =>
  tableHelper.columns([
    tableHelper.accessor('place', { header: '#', sortFn: 'basic', cell: (c) => num(c.getValue()) }),
    tableHelper.accessor('name', {
      header: 'Firm',
      sortFn: 'alphanumeric',
      cell: ({ row }) => you(row.original.name, row.original.is_player),
    }),
    tableHelper.accessor('value_cents', {
      header: valueHeader,
      sortFn: 'basic',
      cell: (c) => num(formatMoneyShort(c.getValue())),
    }),
    tableHelper.accessor('lawyers', {
      header: 'Lawyers',
      sortFn: 'basic',
      cell: (c) => num(formatWhole(c.getValue())),
    }),
  ]);
const revenueColumns = tableColumns('Revenue');
const pepColumns = tableColumns('PEP');

function FirmTable({
  rows,
  columns,
  label,
  testId,
}: {
  rows: TableRow[];
  columns: typeof revenueColumns;
  label: string;
  testId: string;
}) {
  const table = useTable({
    features: gameTableFeatures,
    columns,
    data: rows,
    getRowId: (r) => String(r.firm_id),
  });
  const player = rows.find((r) => r.is_player);
  return (
    <div className="tst-panel" data-testid={testId}>
      <h3 className="tst-ptitle">{label}</h3>
      <DataTable
        table={table}
        label={label}
        selectedRowId={player ? String(player.firm_id) : undefined}
        empty="Not published yet (each spring)."
      />
    </div>
  );
}

function TablesTab({ r }: { r: Rankings }) {
  return (
    <Stack>
      <Text c="dimmed" size="sm">
        {r.tables_year !== null ? `The ${r.tables_year} tables.` : 'No tables published yet.'}
      </Text>
      <Group align="start" grow>
        <FirmTable
          rows={r.revenue}
          columns={revenueColumns}
          label="Revenue"
          testId="revenue-table"
        />
        <FirmTable
          rows={r.pep}
          columns={pepColumns}
          label="Profit per partner"
          testId="pep-table"
        />
      </Group>
    </Stack>
  );
}

// --- League tables ---------------------------------------------------------------------------

const leagueHelper = createColumnHelper<GameTableFeatures, LeagueRow>();
const leagueColumns = leagueHelper.columns([
  leagueHelper.accessor('place', { header: '#', sortFn: 'basic', cell: (c) => num(c.getValue()) }),
  leagueHelper.accessor('name', {
    header: 'Firm',
    sortFn: 'alphanumeric',
    cell: ({ row }) => you(row.original.name, row.original.is_player),
  }),
  leagueHelper.accessor('deals', {
    header: 'Deals',
    sortFn: 'basic',
    cell: (c) => num(formatWhole(c.getValue())),
  }),
  leagueHelper.accessor('value_cents', {
    header: 'Value',
    sortFn: 'basic',
    cell: (c) => num(formatMoneyShort(c.getValue())),
  }),
]);

function LeagueTab({ r }: { r: Rankings }) {
  const [key, setKey] = useState<string | null>(null);
  const chosen = r.league.find((l) => l.practice === key) ?? r.league[0];
  const rows = useMemo(() => chosen?.rows ?? [], [chosen]);
  const table = useTable({
    features: gameTableFeatures,
    columns: leagueColumns,
    data: rows,
    getRowId: (x) => String(x.firm_id),
  });
  const player = rows.find((x) => x.is_player);
  return (
    <Stack>
      <Text c="dimmed" size="sm">
        {r.league_label ? `Published ${r.league_label}.` : 'No league tables published yet.'}
      </Text>
      {r.league.length > 0 && (
        <Select
          w={260}
          aria-label="League table practice"
          data={r.league.map((l) => ({ value: l.practice, label: l.label }))}
          value={chosen?.practice ?? null}
          onChange={setKey}
        />
      )}
      <div data-testid="league-table">
        <DataTable
          table={table}
          label="League table"
          selectedRowId={player ? String(player.firm_id) : undefined}
          empty="No league table yet."
        />
      </div>
    </Stack>
  );
}

// --- Directory bands -------------------------------------------------------------------------

const bandsHelper = createColumnHelper<GameTableFeatures, PracticeBands>();
const bandsColumns = bandsHelper.columns([
  bandsHelper.accessor('label', { header: 'Practice', sortFn: 'alphanumeric' }),
  bandsHelper.accessor((p) => p.player_band ?? 99, {
    id: 'band',
    header: 'Our band',
    sortFn: 'basic',
    cell: ({ row }) => <span data-testid="player-band">{bandText(row.original.player_band)}</span>,
  }),
  bandsHelper.accessor((p) => p.firms.length, {
    id: 'ranked',
    header: 'Firms ranked',
    sortFn: 'basic',
    cell: (c) => num(c.getValue()),
  }),
  bandsHelper.display({
    id: 'history',
    header: 'Our bands by year',
    cell: ({ row }) => (
      <span className="tst-num" data-testid="band-history">
        {bandHistoryText(row.original.player_history)}
      </span>
    ),
  }),
]);

const firmBandHelper = createColumnHelper<GameTableFeatures, BandFirm>();
const firmBandColumns = firmBandHelper.columns([
  firmBandHelper.accessor('band', {
    header: 'Band',
    sortFn: 'basic',
    cell: (c) => num(c.getValue()),
  }),
  firmBandHelper.accessor('name', {
    header: 'Firm',
    sortFn: 'alphanumeric',
    cell: ({ row }) => you(row.original.name, row.original.is_player),
  }),
]);

function BandsTab({ r }: { r: Rankings }) {
  const bandsTable = useTable({
    features: gameTableFeatures,
    columns: bandsColumns,
    data: r.bands,
    getRowId: (p) => p.practice,
  });
  const [key, setKey] = useState<string | null>(null);
  const chosen = r.bands.find((b) => b.practice === key) ?? r.bands[0];
  const firms = useMemo(() => chosen?.firms ?? [], [chosen]);
  const firmsTable = useTable({
    features: gameTableFeatures,
    columns: firmBandColumns,
    data: firms,
    getRowId: (f) => String(f.firm_id),
  });
  const player = firms.find((f) => f.is_player);
  return (
    <Stack>
      <Text c="dimmed" size="sm" data-testid="bands-year">
        {r.bands_year !== null
          ? `The directory's ${r.bands_year} bands (published each October).`
          : 'No bands published yet (each October).'}
      </Text>
      <div data-testid="bands-table">
        <DataTable
          table={bandsTable}
          label="Directory bands"
          rowTestId="band-row"
          empty="No practices."
        />
      </div>
      {chosen && (
        <div className="tst-panel">
          <h3 className="tst-ptitle">Firms by band</h3>
          <Select
            mb="sm"
            w={260}
            aria-label="Bands for practice"
            data={r.bands.map((b) => ({ value: b.practice, label: b.label }))}
            value={chosen.practice}
            onChange={setKey}
          />
          <DataTable
            table={firmsTable}
            label="Firms by band"
            selectedRowId={player ? String(player.firm_id) : undefined}
            empty="No firms ranked in this practice yet."
          />
        </div>
      )}
    </Stack>
  );
}

// --- Individuals -----------------------------------------------------------------------------

const personHelper = createColumnHelper<GameTableFeatures, PersonBand>();
type Label = (key: string) => string;
const personColumns = (practice: Label) =>
  personHelper.columns([
    personHelper.accessor('band', {
      header: 'Band',
      sortFn: 'basic',
      cell: (c) => num(c.getValue()),
    }),
    personHelper.accessor('name', {
      header: 'Name',
      sortFn: 'alphanumeric',
      cell: ({ row }) => you(row.original.name, row.original.is_player),
    }),
    personHelper.accessor('firm', { header: 'Firm', sortFn: 'alphanumeric' }),
    personHelper.accessor('practice', {
      header: 'Practice',
      sortFn: 'alphanumeric',
      cell: (c) => practice(c.getValue()),
    }),
  ]);

function PeopleTab({ r, practice }: { r: Rankings; practice: Label }) {
  const columns = useMemo(() => personColumns(practice), [practice]);
  const table = useTable({
    features: gameTableFeatures,
    columns,
    data: r.people,
    getRowId: (p) => String(p.person_id),
  });
  return (
    <div data-testid="people-bands">
      <DataTable
        table={table}
        label="Ranked individuals"
        rowTestId="person-band-row"
        empty="No individuals ranked yet."
      />
    </div>
  );
}

// --- Best places to work ---------------------------------------------------------------------

const placesHelper = createColumnHelper<GameTableFeatures, PlacesRow>();
const placesColumns = placesHelper.columns([
  placesHelper.accessor('place', { header: '#', sortFn: 'basic', cell: (c) => num(c.getValue()) }),
  placesHelper.accessor('name', {
    header: 'Firm',
    sortFn: 'alphanumeric',
    cell: ({ row }) => you(row.original.name, row.original.is_player),
  }),
  placesHelper.accessor('score', {
    header: 'Score',
    sortFn: 'basic',
    cell: (c) => num(c.getValue().toFixed(1)),
  }),
]);

const historyHelper = createColumnHelper<GameTableFeatures, PlayerPlace>();
const historyColumns = (practice: Label) =>
  historyHelper.columns([
    historyHelper.accessor('date_label', { header: 'When' }),
    historyHelper.accessor('kind', { header: 'Ranking', cell: (c) => humanize(c.getValue()) }),
    historyHelper.accessor((h) => h.practice ?? '', {
      id: 'practice',
      header: 'Practice',
      cell: (c) => (c.getValue() ? practice(c.getValue()) : '—'),
    }),
    historyHelper.accessor('place', { header: 'Place', cell: (c) => num(c.getValue()) }),
  ]);

function PlacesTab({ r, practice }: { r: Rankings; practice: Label }) {
  const columns = useMemo(() => historyColumns(practice), [practice]);
  const table = useTable({
    features: gameTableFeatures,
    columns: placesColumns,
    data: r.places,
    getRowId: (p) => String(p.firm_id),
  });
  const history = useTable({
    features: gameTableFeatures,
    columns,
    data: r.history,
  });
  const player = r.places.find((p) => p.is_player);
  return (
    <Stack>
      <Text c="dimmed" size="sm">
        {r.places_year !== null ? `The ${r.places_year} survey.` : 'No survey published yet.'}
      </Text>
      <div data-testid="places-table">
        <DataTable
          table={table}
          label="Best places to work"
          selectedRowId={player ? String(player.firm_id) : undefined}
          empty="No survey yet."
        />
      </div>
      <div className="tst-panel">
        <h3 className="tst-ptitle">Our places over time</h3>
        <DataTable table={history} label="Our places" empty="Not placed in any ranking yet." />
      </div>
    </Stack>
  );
}

// --- Submission ------------------------------------------------------------------------------

const matterHelper = createColumnHelper<GameTableFeatures, SubmissionMatter>();
const refereeHelper = createColumnHelper<GameTableFeatures, SubmissionReferee>();

function SubmissionTab({ slug, s, practice }: { slug: string; s: Submission; practice: Label }) {
  const submit = useMakeSubmission(slug);
  const [matters, setMatters] = useState<number[]>([]);
  const [referees, setReferees] = useState<number[]>([]);
  const canPick = s.window_open && !s.made;

  const matterColumns = useMemo(
    () =>
      matterHelper.columns([
        matterHelper.display({
          id: 'pick',
          header: 'Showcase',
          cell: ({ row }) => {
            const on = matters.includes(row.original.matter_id);
            return (
              <Checkbox
                aria-label={`Showcase ${row.original.name}`}
                data-testid="submission-matter"
                checked={on || s.matter_ids.includes(row.original.matter_id)}
                disabled={!canPick || (!on && matters.length >= s.max_matters)}
                onChange={() =>
                  setMatters((ids) => toggleId(ids, row.original.matter_id, s.max_matters))
                }
              />
            );
          },
        }),
        matterHelper.accessor('name', { header: 'Matter', sortFn: 'alphanumeric' }),
        matterHelper.accessor('practice', {
          header: 'Practice',
          sortFn: 'alphanumeric',
          cell: (c) => practice(c.getValue()),
        }),
        matterHelper.accessor('status', {
          header: 'Status',
          sortFn: 'alphanumeric',
          cell: (c) => humanize(c.getValue()),
        }),
        matterHelper.accessor('fees_cents', {
          header: 'Fees',
          sortFn: 'basic',
          cell: (c) => num(formatMoneyShort(c.getValue())),
        }),
      ]),
    [matters, canPick, s.max_matters, s.matter_ids, practice],
  );
  const refereeColumns = useMemo(
    () =>
      refereeHelper.columns([
        refereeHelper.display({
          id: 'pick',
          header: 'Referee',
          cell: ({ row }) => {
            const on = referees.includes(row.original.client_id);
            return (
              <Checkbox
                aria-label={`Name ${row.original.name} as a referee`}
                data-testid="submission-referee"
                checked={on || s.referee_ids.includes(row.original.client_id)}
                disabled={!canPick || (!on && referees.length >= s.max_referees)}
                onChange={() =>
                  setReferees((ids) => toggleId(ids, row.original.client_id, s.max_referees))
                }
              />
            );
          },
        }),
        refereeHelper.accessor('name', { header: 'Client', sortFn: 'alphanumeric' }),
        refereeHelper.accessor('relationship', {
          header: 'Relationship',
          sortFn: 'basic',
          cell: (c) => num(c.getValue()),
        }),
      ]),
    [referees, canPick, s.max_referees, s.referee_ids],
  );
  const matterTable = useTable({
    features: gameTableFeatures,
    columns: matterColumns,
    data: s.matters,
    getRowId: (m) => String(m.matter_id),
  });
  const refereeTable = useTable({
    features: gameTableFeatures,
    columns: refereeColumns,
    data: s.referees,
    getRowId: (c) => String(c.client_id),
  });

  return (
    <Stack data-testid={canPick ? 'submission-form' : 'submission'}>
      {s.made ? (
        <Alert color="teal" data-testid="submission-made">
          The {s.year} submission is in: strength {s.strength_pct ?? 0}%, showcasing{' '}
          {s.matter_ids.length} matters with {s.referee_ids.length} referees.
        </Alert>
      ) : s.window_open ? (
        <Text size="sm">
          The {s.year} directory submission is open (March-April). Showcase up to {s.max_matters}{' '}
          matters and name up to {s.max_referees} clients as referees; each referee costs{' '}
          {s.referee_cost} relationship points. Submitting costs {s.energy} energy.
        </Text>
      ) : (
        <Text size="sm" c="dimmed" data-testid="submission-closed">
          The submission window opens in March. The {s.year} submission has not been made.
        </Text>
      )}
      <div className="tst-panel">
        <h3 className="tst-ptitle">
          Matters ({matters.length}/{s.max_matters})
        </h3>
        <DataTable table={matterTable} label="Submission matters" empty="No matters to show." />
      </div>
      <div className="tst-panel">
        <h3 className="tst-ptitle">
          Referees ({referees.length}/{s.max_referees}; {s.referee_cost} relationship each)
        </h3>
        <DataTable table={refereeTable} label="Submission referees" empty="No clients yet." />
      </div>
      {submit.error && <Alert color="red">{submit.error.message}</Alert>}
      {canPick && (
        <Group>
          <Button
            data-testid="submission-submit"
            loading={submit.isPending}
            disabled={matters.length === 0 && referees.length === 0}
            onClick={() => submit.mutate({ matter_ids: matters, referee_ids: referees })}
          >
            Submit to the directory
          </Button>
        </Group>
      )}
    </Stack>
  );
}

// --- Screen ----------------------------------------------------------------------------------

export function RankingsScreen() {
  const { slug = '' } = useParams();
  const q = useRankings(slug);
  const practice = usePracticeLabels(slug);
  if (q.isLoading) return <Text c="dimmed">Loading…</Text>;
  if (q.error || !q.data)
    return <Alert color="red">Could not load the rankings: {q.error?.message}</Alert>;
  const r = q.data;
  const s = r.submission;
  const due = s.window_open && !s.made;
  return (
    <Stack gap="lg" data-testid="rankings-screen">
      <Title order={2}>Rankings</Title>
      <Tabs defaultValue={due ? 'submission' : 'tables'} keepMounted={false}>
        <Tabs.List>
          <Tabs.Tab value="tables" data-testid="tab-tables">
            Tables
          </Tabs.Tab>
          <Tabs.Tab value="league" data-testid="tab-league">
            League tables
          </Tabs.Tab>
          <Tabs.Tab value="bands" data-testid="tab-bands">
            Directory bands
          </Tabs.Tab>
          <Tabs.Tab value="people" data-testid="tab-people">
            Individuals
          </Tabs.Tab>
          <Tabs.Tab value="places" data-testid="tab-places">
            Best places to work
          </Tabs.Tab>
          <Tabs.Tab value="submission" data-testid="tab-submission">
            Submission
            {due && (
              <Badge ml="xs" size="xs" color="warn">
                Open
              </Badge>
            )}
          </Tabs.Tab>
        </Tabs.List>
        <Tabs.Panel value="tables" pt="md">
          <TablesTab r={r} />
        </Tabs.Panel>
        <Tabs.Panel value="league" pt="md">
          <LeagueTab r={r} />
        </Tabs.Panel>
        <Tabs.Panel value="bands" pt="md">
          <BandsTab r={r} />
        </Tabs.Panel>
        <Tabs.Panel value="people" pt="md">
          <PeopleTab r={r} practice={practice} />
        </Tabs.Panel>
        <Tabs.Panel value="places" pt="md">
          <PlacesTab r={r} practice={practice} />
        </Tabs.Panel>
        <Tabs.Panel value="submission" pt="md">
          <SubmissionTab key={`${s.year}-${s.made}`} slug={slug} s={s} practice={practice} />
        </Tabs.Panel>
      </Tabs>
    </Stack>
  );
}
