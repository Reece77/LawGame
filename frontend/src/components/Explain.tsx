// Ported from TST frontend/src/components/Explain.tsx @ 02fba2aa; changed: the breakdown, its
// band and note only (no 12-month trend or Ask why yet); a slug route param.
import { Drawer, Text } from '@mantine/core';
import { createColumnHelper, useTable } from '@tanstack/react-table';
import { useMemo, useState } from 'react';
import { useParams } from 'react-router';
import { useExplain, type ExplainData, type ExplainMetric } from '../lib/api';
import { formatUnit, itemText } from '../lib/explain';
import { gameTableFeatures, type GameTableFeatures } from '../lib/table';
import { DataTable } from './DataTable';

// Explain this (spec 16): a number's drivers as the API built them. Read-only: it never
// changes the game. A matter's outlook comes as a band, never a number.

type Item = ExplainData['items'][number];

interface Props {
  metric: ExplainMetric;
  entity?: string | number | null;
  label?: string; // what the button's tooltip names
}

/** The Explain affordance: a small button beside a number that opens its panel. */
export function Explain({ metric, entity, label }: Props) {
  const { slug = '' } = useParams();
  const [open, setOpen] = useState(false);
  const key = entity === undefined || entity === null ? null : String(entity);
  return (
    <>
      <button
        type="button"
        className="tst-explain"
        aria-label={`Explain ${label ?? 'this number'}`}
        title={`Explain ${label ?? 'this number'}`}
        data-testid={`explain-${metric}${key === null ? '' : `-${key}`}`}
        onClick={(e) => {
          e.preventDefault();
          e.stopPropagation();
          setOpen(true);
        }}
      >
        ?
      </button>
      {open && (
        <ExplainPanel slug={slug} metric={metric} entity={key} onClose={() => setOpen(false)} />
      )}
    </>
  );
}

const helper = createColumnHelper<GameTableFeatures, Item>();

function Breakdown({ items }: { items: Item[] }) {
  const columns = useMemo(
    () =>
      helper.columns([
        helper.accessor('label', { header: 'Driver' }),
        helper.display({
          id: 'amount',
          header: 'Amount',
          cell: ({ row }) => <span className="tst-num">{itemText(row.original)}</span>,
        }),
      ]),
    [],
  );
  const table = useTable({ features: gameTableFeatures, columns, data: items });
  return (
    <DataTable
      table={table}
      label="Breakdown"
      rowTestId="explain-item"
      empty="Nothing to break down yet."
    />
  );
}

export function ExplainPanel({
  slug,
  metric,
  entity,
  onClose,
}: {
  slug: string;
  metric: ExplainMetric;
  entity: string | null;
  onClose: () => void;
}) {
  const explain = useExplain(slug, metric, entity, true);
  const e = explain.data;
  return (
    <Drawer
      opened
      onClose={onClose}
      position="right"
      size="lg"
      title={e ? `${e.label}: ${e.subject}` : 'Explain'}
    >
      {explain.isPending ? (
        <Text c="dimmed">Loading…</Text>
      ) : explain.error || !e ? (
        <Text c="red">Could not explain this number: {explain.error?.message}</Text>
      ) : (
        <div
          style={{ display: 'flex', flexDirection: 'column', gap: 16 }}
          data-testid="explain-panel"
        >
          <div className="tst-num" style={{ fontSize: 22, fontWeight: 600 }}>
            {e.band ??
              (e.value === null || e.value === undefined ? '—' : formatUnit(e.value, e.unit))}
          </div>
          <Breakdown items={e.items} />
          <Text size="sm" c="dimmed">
            {e.note}
          </Text>
        </div>
      )}
    </Drawer>
  );
}
