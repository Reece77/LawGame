import { Alert, Badge, Button, Group, Select, SimpleGrid, Stack, Text, Title } from '@mantine/core';
import { createColumnHelper, useTable } from '@tanstack/react-table';
import { useMemo, useState } from 'react';
import { Link, useParams } from 'react-router';
import { DataTable } from '../components/DataTable';
import { RiskBadge } from '../components/RiskBadge';
import {
  useClient,
  useIntroduce,
  usePracticeLabels,
  type ClientDetail,
  type MatterRow,
} from '../lib/api';
import { formatBpShort, formatMoneyShort, formatMoneyWhole, humanize } from '../lib/format';
import { gameTableFeatures, type GameTableFeatures } from '../lib/table';

// A client (spec 16): relationship, relationship partner, practices used, panel, the GC (as
// revealed), its matters and the cross-sell map with Introduce.
const helper = createColumnHelper<GameTableFeatures, MatterRow>();
const AFFINITY = { high: 'teal', medium: 'yellow', low: 'gray' } as const;

export function ClientScreen() {
  const { slug = '', clientId = '0' } = useParams();
  const id = Number(clientId);
  const client = useClient(slug, id);
  const practice = usePracticeLabels(slug);
  if (client.isLoading) return <Text c="dimmed">Loading…</Text>;
  if (client.error || !client.data) {
    return <Alert color="red">Could not load the client: {client.error?.message}</Alert>;
  }
  const c = client.data;
  return (
    <Stack gap="lg">
      <div>
        <Group gap="xs">
          <Title order={2} data-testid="client-name">
            {c.name}
          </Title>
          {c.key_client && (
            <Badge color="yellow" variant="light">
              Key client
            </Badge>
          )}
          {c.advance_waiver && <Badge variant="light">Advance waiver</Badge>}
        </Group>
        <Text c="dimmed" size="sm">
          {c.sector} · {humanize(c.size_class)} company · panel status {c.panel_status}
        </Text>
      </div>
      <div className="tst-panel">
        <SimpleGrid cols={{ base: 2, sm: 4 }}>
          <Field label="Relationship">
            <span data-testid="relationship">{c.relationship}</span> / 100
          </Field>
          <Field label="Relationship partner">{c.partner?.name ?? '—'}</Field>
          <Field label="Wallet (estimate, a year)">
            {formatMoneyShort(c.wallet_estimate.lo)}–{formatMoneyShort(c.wallet_estimate.hi)}
          </Field>
          <Field label="Our share">
            {formatBpShort(c.share_estimate.lo)}–{formatBpShort(c.share_estimate.hi)}
          </Field>
          <Field label="Fees (12 months)">{formatMoneyWhole(c.fees_12m_cents)}</Field>
          <Field label="Practices used">{c.practices.map(practice).join(', ') || '—'}</Field>
          <Field label="General counsel">
            {c.general_counsel.name}, {c.general_counsel.age}
          </Field>
          <Field label="Other panel firms">{c.panel.join(' · ') || '—'}</Field>
        </SimpleGrid>
      </div>
      <ClientMatters slug={slug} matters={c.matters} />
      <CrossSell slug={slug} c={c} />
    </Stack>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <Text size="xs" c="dimmed">
        {label}
      </Text>
      <div style={{ whiteSpace: 'normal' }}>
        {children}
      </div>
    </div>
  );
}

function ClientMatters({ slug, matters }: { slug: string; matters: MatterRow[] }) {
  const columns = useMemo(
    () =>
      helper.columns([
        helper.accessor('name', {
          header: 'Matter',
          sortFn: 'alphanumeric',
          cell: ({ row }) => (
            <Link to={`/game/${slug}/matters/${row.original.id}`}>{row.original.name}</Link>
          ),
        }),
        helper.accessor((r) => r.outcome ?? r.status, {
          id: 'status',
          header: 'Status',
          sortFn: 'alphanumeric',
          cell: ({ getValue }) => humanize(getValue()),
        }),
        helper.accessor('wip_cents', {
          header: 'WIP',
          sortFn: 'basic',
          cell: ({ getValue }) => <span className="tst-num">{formatMoneyWhole(getValue())}</span>,
        }),
        helper.display({
          id: 'risk',
          header: 'Risk',
          cell: ({ row }) => <RiskBadge risk={row.original.risk} notes={row.original.risk_notes} />,
        }),
      ]),
    [slug],
  );
  const table = useTable({ features: gameTableFeatures, columns, data: matters });
  return (
    <div>
      <Title order={4} mb="xs">
        Matters
      </Title>
      <DataTable table={table} label="Client matters" empty="No named matters for this client." />
    </div>
  );
}

function CrossSell({ slug, c }: { slug: string; c: ClientDetail }) {
  const introduce = useIntroduce(slug, c.id);
  const [chosen, setChosen] = useState<Record<string, string | null>>({});
  return (
    <div className="tst-panel" data-testid="cross-sell">
      <h3 className="tst-ptitle">Cross-sell map</h3>
      {introduce.error && (
        <Alert color="red" mb="sm" withCloseButton onClose={() => introduce.reset()}>
          {introduce.error.message}
        </Alert>
      )}
      {introduce.isSuccess && (
        <Alert color="teal" mb="sm" data-testid="introduce-done">
          Introduction made.
        </Alert>
      )}
      <Stack gap={8}>
        {c.cross_sell.map((x) => (
          <Group key={x.practice} justify="space-between" data-testid="cross-sell-row">
            <Group gap="xs">
              <Text size="sm" w={220}>
                {x.label}
              </Text>
              <Badge size="sm" variant="light" color={AFFINITY[x.affinity]}>
                {x.affinity} affinity
              </Badge>
            </Group>
            {x.colleagues.length === 0 ? (
              <Text size="sm" c="dimmed">
                Nobody at the firm practises this yet
              </Text>
            ) : (
              <Group gap="xs">
                <Select
                  size="xs"
                  w={200}
                  aria-label={`Colleague for ${x.label}`}
                  placeholder="Colleague"
                  data={x.colleagues.map((p) => ({ value: String(p.id), label: p.name }))}
                  value={chosen[x.practice] ?? null}
                  onChange={(v) => setChosen({ ...chosen, [x.practice]: v })}
                />
                <Button
                  size="xs"
                  disabled={!chosen[x.practice]}
                  loading={introduce.isPending}
                  onClick={() =>
                    introduce.mutate({
                      colleague_id: Number(chosen[x.practice]),
                      practice: x.practice,
                    })
                  }
                  aria-label={`Introduce for ${x.label}`}
                >
                  Introduce
                </Button>
              </Group>
            )}
          </Group>
        ))}
      </Stack>
    </div>
  );
}
