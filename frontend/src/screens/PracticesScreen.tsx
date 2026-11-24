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
import { bandText, signedDelta } from '../lib/standing';
import { gameTableFeatures, type GameTableFeatures } from '../lib/table';

// Practices (spec 16): demand trend, our revenue and share, capacity, utilisation, leverage
// and rates against the rate card; PT-M16: reputation (and the market's top decile), the
// directory band and each practice's latest reputation causes; PT-M7b: the firm's card by practice (its share of the top
// card, and in brackets the share its reputation has earned). Every number is the API's.
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
  helper.accessor('card_bp', {
    header: 'Our card (earned)',
    sortFn: 'basic',
    cell: ({ row }) => (
      <span className="tst-num" data-testid="practice-card">
        {formatBpShort(row.original.card_bp)}{' '}
        <span className="tst-muted">({formatBpShort(row.original.card_target_bp)})</span>
      </span>
    ),
  }),
  helper.accessor('reputation', {
    header: 'Reputation (top)',
    sortFn: 'basic',
    cell: ({ row }) => (
      <span className="tst-num" data-testid="practice-reputation">
        {row.original.reputation} <span className="tst-muted">({row.original.reputation_top})</span>
      </span>
    ),
  }),
  helper.accessor((r) => r.band ?? 99, {
    id: 'band',
    header: 'Band',
    sortFn: 'basic',
    cell: ({ row }) => <span data-testid="practice-band">{bandText(row.original.band)}</span>,
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
  helper.accessor('ai_cut_bp', {
    // PT-M14 (spec 13): what clients cut from hourly bills for AI-able hours, and products
    header: 'AI cut (products)',
    sortFn: 'basic',
    cell: ({ row }) => (
      <span className="tst-num" data-testid="practice-ai-cut">
        {formatBpShort(row.original.ai_cut_bp ?? 0)}{' '}
        <span className="tst-muted">({row.original.ai_products ?? 0})</span>
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
    header: 'Top card (2005)',
    cell: ({ getValue }) => <span className="tst-num">{formatMoneyWhole(getValue())}</span>,
  }),
  rateHelper.accessor('firm_card_cents', {
    header: 'Our card',
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
          <ReputationCauses data={data} />
          <Rates data={data} />
        </>
      )}
    </Stack>
  );
}

const CAUSES_PER_PRACTICE = 3; // display: each practice's latest reputation changes

function ReputationCauses({ data }: { data: PracticeScreenRow[] }) {
  const shown = data.filter((p) => p.reputation_causes.length > 0);
  return (
    <div className="tst-panel" data-testid="reputation-causes">
      <h3 className="tst-ptitle">Recent reputation changes</h3>
      {shown.length === 0 ? (
        <Text size="sm" c="dimmed">
          No changes yet.
        </Text>
      ) : (
        <Stack gap={4}>
          {shown.map((p) => (
            <Text size="xs" key={p.key}>
              <b>{p.label}:</b>{' '}
              {p.reputation_causes.slice(0, CAUSES_PER_PRACTICE).map((c, i) => (
                <span key={i}>
                  {i > 0 && ' · '}
                  <span className="tst-num">{signedDelta(c.delta)}</span> {c.cause}{' '}
                  <span className="tst-muted">({c.date_label})</span>
                </span>
              ))}
            </Text>
          ))}
        </Stack>
      )}
    </div>
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
