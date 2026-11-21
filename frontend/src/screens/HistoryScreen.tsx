import { Badge, Tabs, Text, Title } from '@mantine/core';
import { createColumnHelper, useTable } from '@tanstack/react-table';
import { useMemo } from 'react';
import { useParams } from 'react-router';
import { DataTable } from '../components/DataTable';
import { useTableViews } from '../hooks/useTableViews';
import { useHistory, type HistoryData } from '../lib/api';
import { formatBpPercent, formatMoneyWhole, humanize } from '../lib/format';
import { gameTableFeatures, type GameTableFeatures } from '../lib/table';

// History (spec 16, PT-M7): the firm's years (revenue, PEP, revenue per lawyer, margin,
// equity partners, its rank among the rivals by that year's revenue) and its timeline.
type YearRow = HistoryData['years'][number];
type TimelineRow = HistoryData['timeline'][number];
const years = createColumnHelper<GameTableFeatures, YearRow>();
const lines = createColumnHelper<GameTableFeatures, TimelineRow>();
const NO_YEARS: YearRow[] = [];
const NO_LINES: TimelineRow[] = [];

const money = (cents: number | null | undefined) =>
  cents === null || cents === undefined ? '—' : formatMoneyWhole(cents);

function YearsTable({ rows }: { rows: YearRow[] }) {
  const columns = useMemo(
    () =>
      years.columns([
        years.accessor('year', {
          header: 'Year',
          sortFn: 'basic',
          cell: ({ row }) => (
            <>
              {row.original.year}
              {!row.original.complete && (
                <Badge size="xs" ml="xs" variant="light">
                  to date
                </Badge>
              )}
            </>
          ),
        }),
        years.accessor('revenue_cents', {
          header: 'Revenue',
          sortFn: 'basic',
          cell: ({ getValue }) => <span className="tst-num">{money(getValue())}</span>,
        }),
        years.accessor((r) => r.pep_cents ?? 0, {
          id: 'pep',
          header: 'PEP',
          sortFn: 'basic',
          cell: ({ row }) => <span className="tst-num">{money(row.original.pep_cents)}</span>,
        }),
        years.accessor((r) => r.rpl_cents ?? 0, {
          id: 'rpl',
          header: 'Revenue per lawyer',
          sortFn: 'basic',
          cell: ({ row }) => <span className="tst-num">{money(row.original.rpl_cents)}</span>,
        }),
        years.accessor((r) => r.margin_bp ?? 0, {
          id: 'margin',
          header: 'Margin',
          sortFn: 'basic',
          cell: ({ row }) => (
            <span className="tst-num">
              {row.original.margin_bp === null ? '—' : formatBpPercent(row.original.margin_bp)}
            </span>
          ),
        }),
        years.accessor('equity_partners', {
          header: 'Equity partners',
          sortFn: 'basic',
          cell: ({ getValue }) => <span className="tst-num">{getValue()}</span>,
        }),
        years.accessor((r) => r.rank ?? 9999, {
          id: 'rank',
          header: 'Rank by revenue',
          sortFn: 'basic',
          cell: ({ row }) =>
            row.original.rank === null ? (
              <span className="tst-muted">—</span>
            ) : (
              <span className="tst-num" data-testid="history-rank">
                {row.original.rank} of {row.original.firms_ranked}
              </span>
            ),
        }),
      ]),
    [],
  );
  const views = useTableViews('history-years', {
    sorting: [{ id: 'year', desc: true }],
    columnVisibility: {},
    columnOrder: [],
  });
  const table = useTable({
    features: gameTableFeatures,
    columns,
    data: rows,
    getRowId: (r) => String(r.year),
    ...views.tableProps,
  });
  return (
    <DataTable
      views={views}
      table={table}
      label="Years"
      rowTestId="history-year"
      empty="No month has been played yet."
    />
  );
}

function TimelineTable({ rows }: { rows: TimelineRow[] }) {
  const columns = useMemo(
    () =>
      lines.columns([
        lines.accessor('turn', {
          header: 'Date',
          sortFn: 'basic',
          cell: ({ row }) => row.original.date_label,
        }),
        lines.accessor('kind', {
          header: 'Kind',
          sortFn: 'alphanumeric',
          cell: ({ getValue }) => (
            <Badge size="sm" variant="light" color={getValue() === 'market' ? 'gray' : 'teal'}>
              {getValue() === 'market' ? 'Legal market' : humanize(getValue())}
            </Badge>
          ),
        }),
        lines.accessor('title', { header: 'What happened', sortFn: 'alphanumeric' }),
      ]),
    [],
  );
  const views = useTableViews('history-timeline', {
    sorting: [{ id: 'turn', desc: true }],
    columnVisibility: {},
    columnOrder: [],
  });
  const table = useTable({
    features: gameTableFeatures,
    columns,
    data: rows,
    getRowId: (r) => `${r.turn}-${r.kind}-${r.title}`,
    ...views.tableProps,
  });
  return (
    <DataTable
      views={views}
      table={table}
      label="Timeline"
      rowTestId="history-line"
      empty="Nothing on the record yet."
    />
  );
}

export function HistoryScreen() {
  const { slug = '' } = useParams();
  const history = useHistory(slug);
  return (
    <>
      <Title order={2} mb="md">
        History
      </Title>
      {history.isLoading ? (
        <Text c="dimmed">Loading…</Text>
      ) : (
        <Tabs defaultValue="years">
          <Tabs.List mb="sm">
            <Tabs.Tab value="years">Years and rankings</Tabs.Tab>
            <Tabs.Tab value="timeline">Timeline</Tabs.Tab>
          </Tabs.List>
          <Tabs.Panel value="years">
            <YearsTable rows={history.data?.years ?? NO_YEARS} />
          </Tabs.Panel>
          <Tabs.Panel value="timeline">
            <TimelineTable rows={history.data?.timeline ?? NO_LINES} />
          </Tabs.Panel>
        </Tabs>
      )}
    </>
  );
}
