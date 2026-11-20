import { Badge, Text, Title } from '@mantine/core';
import { createColumnHelper, useTable } from '@tanstack/react-table';
import { useMemo } from 'react';
import { Link, useParams } from 'react-router';
import { DataTable } from '../components/DataTable';
import { useTableViews } from '../hooks/useTableViews';
import { useClients, usePracticeLabels, type ClientRow } from '../lib/api';
import { formatBpShort, formatMoneyShort, formatMoneyWhole, humanize } from '../lib/format';
import { gameTableFeatures, type GameTableFeatures } from '../lib/table';

// Clients (spec 16): wallet estimate (a range), our share (a range), relationship, the
// relationship partner, practices used, panel status. Every number is the API's.
const helper = createColumnHelper<GameTableFeatures, ClientRow>();
const EMPTY: ClientRow[] = [];
const PANEL_COLOR = { key: 'yellow', active: 'teal', dormant: 'gray' } as const;

export function ClientsScreen() {
  const { slug = '' } = useParams();
  const clients = useClients(slug);
  const practice = usePracticeLabels(slug);
  const columns = useMemo(
    () =>
      helper.columns([
        helper.accessor('name', {
          header: 'Client',
          sortFn: 'alphanumeric',
          cell: ({ row }) => (
            <Link to={`/game/${slug}/clients/${row.original.id}`} data-testid="client-link">
              {row.original.name}
            </Link>
          ),
        }),
        helper.accessor('sector', { header: 'Sector', sortFn: 'alphanumeric' }),
        helper.accessor((r) => r.wallet_estimate.hi, {
          id: 'wallet',
          header: 'Wallet (estimate)',
          sortFn: 'basic',
          cell: ({ row }) => (
            <span className="tst-num">
              {formatMoneyShort(row.original.wallet_estimate.lo)}–
              {formatMoneyShort(row.original.wallet_estimate.hi)}
            </span>
          ),
        }),
        helper.accessor('fees_12m_cents', {
          header: 'Fees (12 months)',
          sortFn: 'basic',
          cell: ({ getValue }) => <span className="tst-num">{formatMoneyWhole(getValue())}</span>,
        }),
        helper.accessor((r) => r.share_estimate.hi, {
          id: 'share',
          header: 'Our share',
          sortFn: 'basic',
          cell: ({ row }) => (
            <span className="tst-num">
              {formatBpShort(row.original.share_estimate.lo)}–
              {formatBpShort(row.original.share_estimate.hi)}
            </span>
          ),
        }),
        helper.accessor('relationship', {
          header: 'Relationship',
          sortFn: 'basic',
          cell: ({ getValue }) => <span className="tst-num">{getValue()}</span>,
        }),
        helper.accessor((r) => r.partner?.name ?? '', {
          id: 'partner',
          header: 'Partner',
          sortFn: 'alphanumeric',
          cell: ({ getValue }) => getValue() || <span className="tst-muted">—</span>,
        }),
        helper.accessor((r) => r.practices.map(practice).join(', '), {
          id: 'practices',
          header: 'Practices',
          sortFn: 'alphanumeric',
        }),
        helper.accessor('panel_status', {
          header: 'Panel',
          sortFn: 'alphanumeric',
          cell: ({ getValue }) => (
            <Badge size="sm" variant="light" color={PANEL_COLOR[getValue()]}>
              {humanize(getValue())}
            </Badge>
          ),
        }),
        helper.accessor('open_matters', {
          header: 'Open matters',
          sortFn: 'basic',
          cell: ({ getValue }) => <span className="tst-num">{getValue()}</span>,
        }),
      ]),
    [slug, practice],
  );
  const views = useTableViews('clients', {
    sorting: [{ id: 'fees_12m_cents', desc: true }],
    columnVisibility: {},
    columnOrder: [],
  });
  const table = useTable({
    features: gameTableFeatures,
    columns,
    data: clients.data ?? EMPTY,
    getRowId: (r) => String(r.id),
    ...views.tableProps,
  });
  return (
    <>
      <Title order={2} mb="md">
        Clients
      </Title>
      {clients.isLoading ? (
        <Text c="dimmed">Loading…</Text>
      ) : (
        <DataTable
          views={views}
          table={table}
          label="Clients"
          rowTestId="client-row"
          empty="The firm has no clients yet."
        />
      )}
    </>
  );
}
