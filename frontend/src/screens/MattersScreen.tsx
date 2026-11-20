import { Group, SegmentedControl, Text, Title } from '@mantine/core';
import { createColumnHelper, useTable } from '@tanstack/react-table';
import { useMemo, useState } from 'react';
import { Link, useParams } from 'react-router';
import { DataTable } from '../components/DataTable';
import { RiskBadge } from '../components/RiskBadge';
import { useTableViews } from '../hooks/useTableViews';
import { useMatters, usePracticeLabels, type MatterRow, type MatterStatusFilter } from '../lib/api';
import { formatHours, formatMoneyWhole, humanize } from '../lib/format';
import { gameTableFeatures, type GameTableFeatures } from '../lib/table';

// Matters (spec 16): the firm's named matters. Every number is the API's, formatted here.
const helper = createColumnHelper<GameTableFeatures, MatterRow>();
const EMPTY: MatterRow[] = [];
const RISK_ORDER = { low: 0, medium: 1, high: 2 } as const;

export function MattersScreen() {
  const { slug = '' } = useParams();
  const [status, setStatus] = useState<MatterStatusFilter>('open');
  const matters = useMatters(slug, status);
  const practice = usePracticeLabels(slug);
  const columns = useMemo(
    () =>
      helper.columns([
        helper.accessor('name', {
          header: 'Matter',
          sortFn: 'alphanumeric',
          cell: ({ row }) => (
            <Link to={`/game/${slug}/matters/${row.original.id}`} data-testid="matter-link">
              {row.original.name}
            </Link>
          ),
        }),
        helper.accessor((r) => r.client.name, {
          id: 'client',
          header: 'Client',
          sortFn: 'alphanumeric',
          cell: ({ row }) => (
            <Link to={`/game/${slug}/clients/${row.original.client.id}`}>
              {row.original.client.name}
            </Link>
          ),
        }),
        helper.accessor((r) => practice(r.practice), {
          id: 'practice',
          header: 'Practice',
          sortFn: 'alphanumeric',
        }),
        helper.accessor('kind_label', { header: 'Kind', sortFn: 'alphanumeric' }),
        helper.accessor((r) => r.lead?.name ?? '', {
          id: 'lead',
          header: 'Lead',
          sortFn: 'alphanumeric',
          cell: ({ getValue }) => getValue() || <span className="tst-muted">—</span>,
        }),
        helper.accessor((r) => r.phase ?? r.outcome ?? r.status, {
          id: 'phase',
          header: 'Phase',
          sortFn: 'alphanumeric',
          cell: ({ getValue }) => humanize(getValue()),
        }),
        helper.accessor('worked_hours', {
          header: 'Hours / budget',
          sortFn: 'basic',
          cell: ({ row }) => (
            <span className="tst-num">
              {formatHours(row.original.worked_hours)} / {formatHours(row.original.budget_hours)}
            </span>
          ),
        }),
        helper.accessor('hours_last_month', {
          header: 'Last month',
          sortFn: 'basic',
          cell: ({ getValue }) => <span className="tst-num">{formatHours(getValue())}</span>,
        }),
        helper.accessor('wip_cents', {
          header: 'WIP',
          sortFn: 'basic',
          cell: ({ getValue }) => <span className="tst-num">{formatMoneyWhole(getValue())}</span>,
        }),
        helper.accessor((r) => RISK_ORDER[r.risk], {
          id: 'risk',
          header: 'Risk',
          sortFn: 'basic',
          cell: ({ row }) => <RiskBadge risk={row.original.risk} notes={row.original.risk_notes} />,
        }),
        helper.accessor('due_label', { header: 'Due', enableSorting: false }),
      ]),
    [slug, practice],
  );
  const views = useTableViews('matters');
  const table = useTable({
    features: gameTableFeatures,
    columns,
    data: matters.data ?? EMPTY,
    getRowId: (r) => String(r.id),
    ...views.tableProps,
  });
  return (
    <>
      <Group justify="space-between" mb="md">
        <Title order={2}>Matters</Title>
        <SegmentedControl
          value={status}
          onChange={(v) => setStatus(v as MatterStatusFilter)}
          data={[
            { value: 'open', label: 'Open' },
            { value: 'conflicted', label: 'Conflicted' },
            { value: 'closed', label: 'Closed' },
            { value: 'all', label: 'All' },
          ]}
          aria-label="Matter status"
        />
      </Group>
      {matters.isLoading ? (
        <Text c="dimmed">Loading…</Text>
      ) : (
        <DataTable
          views={views}
          table={table}
          label="Matters"
          rowTestId="matter-row"
          empty="No named matters in this view."
        />
      )}
    </>
  );
}
