import { Select, Stack, Text, Title } from '@mantine/core';
import { createColumnHelper, useTable } from '@tanstack/react-table';
import { useMemo, useState } from 'react';
import { useParams } from 'react-router';
import { DataTable } from '../components/DataTable';
import { Explain } from '../components/Explain';
import { Sparkline } from '../components/Sparkline';
import { useTableViews } from '../hooks/useTableViews';
import { usePracticesScreen, type PracticeScreenRow } from '../lib/api';
import {
  formatBpShort,
  formatHours,
  formatMoneyShort,
  formatMoneyWhole,
  formatRatio,
  humanize,
} from '../lib/format';
import { gameTableFeatures, type GameTableFeatures } from '../lib/table';

// Practices (spec 16): demand trend, our revenue and share, capacity, utilisation, leverage
// and rates against the rate card. Every number is the API's.
const helper = createColumnHelper<GameTableFeatures, PracticeScreenRow>();
type Rate = PracticeScreenRow['rates'][number];
const rateHelper = createColumnHelper<GameTableFeatures, Rate>();
const EMPTY: PracticeScreenRow[] = [];

const columns = helper.columns([
  helper.accessor('label', { header: 'Practice', sortFn: 'alphanumeric' }),
  helper.display({
    id: 'trend',
    header: 'Demand trend',
    cell: ({ row }) => (
      <Sparkline
        values={row.original.demand_trend.map((p) => p.cents)}
        label={`${row.original.label} demand`}
      />
    ),
  }),
  helper.accessor('demand_cents', {
    header: 'Demand (month)',
    sortFn: 'basic',
    cell: ({ getValue }) => <span className="tst-num">{formatMoneyShort(getValue())}</span>,
  }),
  helper.accessor('revenue_cents', {
    header: 'Our revenue',
    sortFn: 'basic',
    cell: ({ getValue }) => <span className="tst-num">{formatMoneyWhole(getValue())}</span>,
  }),
  helper.accessor('share_bp', {
    header: 'Share',
    sortFn: 'basic',
    cell: ({ getValue }) => <span className="tst-num">{formatBpShort(getValue())}</span>,
  }),
  helper.accessor('lawyers', {
    header: 'Lawyers',
    sortFn: 'basic',
    cell: ({ getValue }) => <span className="tst-num">{getValue()}</span>,
  }),
  helper.accessor('capacity_hours', {
    header: 'Capacity',
    sortFn: 'basic',
    cell: ({ getValue }) => <span className="tst-num">{formatHours(getValue())}</span>,
  }),
  helper.accessor('hours_last_month', {
    header: 'Hours',
    sortFn: 'basic',
    cell: ({ getValue }) => <span className="tst-num">{formatHours(getValue())}</span>,
  }),
  helper.accessor((r) => r.utilisation_bp ?? -1, {
    id: 'utilisation',
    header: 'Utilisation',
    sortFn: 'basic',
    cell: ({ row }) =>
      row.original.utilisation_bp === null || row.original.utilisation_bp === undefined ? (
        <span className="tst-muted">—</span>
      ) : (
        <span className="tst-num">
          {formatBpShort(row.original.utilisation_bp)}
          <Explain
            metric="utilisation"
            entity={`practice:${row.original.key}`}
            label={`${row.original.label} utilisation`}
          />
        </span>
      ),
  }),
  helper.accessor((r) => r.leverage ?? -1, {
    id: 'leverage',
    header: 'Leverage (norm)',
    sortFn: 'basic',
    cell: ({ row }) => (
      <span className="tst-num">
        {row.original.leverage === null || row.original.leverage === undefined
          ? '—'
          : formatRatio(row.original.leverage)}{' '}
        <span className="tst-muted">({formatRatio(row.original.leverage_norm)})</span>
      </span>
    ),
  }),
]);

const rateColumns = rateHelper.columns([
  rateHelper.accessor('band', {
    header: 'Band',
    cell: ({ getValue }) => humanize(getValue()),
  }),
  rateHelper.accessor('card_cents', {
    header: 'Rate card',
    cell: ({ getValue }) => <span className="tst-num">{formatMoneyWhole(getValue())}</span>,
  }),
  rateHelper.accessor((r) => r.ours_cents ?? null, {
    id: 'ours',
    header: 'Ours last month',
    cell: ({ getValue }) => {
      const v = getValue();
      return v === null ? (
        <span className="tst-muted">no hours</span>
      ) : (
        <span className="tst-num">{formatMoneyWhole(v)}</span>
      );
    },
  }),
]);

export function PracticesScreen() {
  const { slug = '' } = useParams();
  const practices = usePracticesScreen(slug);
  const data = practices.data ?? EMPTY;
  const views = useTableViews('practices');
  const table = useTable({
    features: gameTableFeatures,
    columns,
    data,
    getRowId: (r) => r.key,
    ...views.tableProps,
  });
  return (
    <Stack gap="lg">
      <Title order={2}>
        Practices
        <Explain metric="utilisation" entity="firm" label="the firm's utilisation" />
      </Title>
      {practices.isLoading ? (
        <Text c="dimmed">Loading…</Text>
      ) : (
        <>
          <DataTable
            views={views}
            table={table}
            label="Practices"
            rowTestId="practice-row"
            empty="No practices."
          />
          <Rates data={data} />
        </>
      )}
    </Stack>
  );
}

function Rates({ data }: { data: PracticeScreenRow[] }) {
  const [key, setKey] = useState<string | null>(data[0]?.key ?? null);
  const chosen = data.find((p) => p.key === key) ?? data[0];
  const rates = useMemo(() => chosen?.rates ?? [], [chosen]);
  const table = useTable({ features: gameTableFeatures, columns: rateColumns, data: rates });
  return (
    <div className="tst-panel">
      <h3 className="tst-ptitle">Rates against the rate card</h3>
      <Select
        mb="sm"
        w={260}
        aria-label="Rates for practice"
        data={data.map((p) => ({ value: p.key, label: p.label }))}
        value={chosen?.key ?? null}
        onChange={setKey}
      />
      <DataTable table={table} label="Rates" empty="No rate card." />
    </div>
  );
}
