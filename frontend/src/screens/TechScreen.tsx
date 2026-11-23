import {
  Alert,
  Badge,
  Button,
  Group,
  NumberInput,
  Select,
  SimpleGrid,
  Stack,
  Text,
  Title,
} from '@mantine/core';
import { createColumnHelper, useTable } from '@tanstack/react-table';
import { useState } from 'react';
import { useParams } from 'react-router';
import { DataTable } from '../components/DataTable';
import { RunBy } from '../components/RunBy';
import { formatBpShort, formatMoneyShort, formatMoneyWhole, humanize } from '../lib/format';
import { gameTableFeatures, type GameTableFeatures } from '../lib/table';
import {
  useInvestInEra,
  useLaunchProduct,
  useRetireProduct,
  useRolloutEra,
  useSetTraining,
  useTech,
  type Tech,
  type TechEra,
  type TechProduct,
  type TechTask,
} from '../lib/techApi';

// Technology (spec 13, 16; PT-M14): the eras, the firm's adoption against the market's, what
// each costs; efficiency by task and what clients cut from hourly bills; the training
// programme; client expectations and RFPs; fixed-fee products. Every number is the API's: the
// screen formats, it never computes a game value.

const FULL_BP = 10000; // a full subscription's coverage (an input value, not a game number)

function EraActions({ slug, e }: { slug: string; e: TechEra }) {
  const invest = useInvestInEra(slug);
  const rollout = useRolloutEra(slug);
  if (!e.available)
    return (
      <Text size="xs" c="dimmed">
        from {e.start_label}
      </Text>
    );
  return (
    <Group gap={4} wrap="nowrap">
      {e.subscription_bp < FULL_BP ? (
        <Button
          size="compact-xs"
          loading={invest.isPending}
          onClick={() => invest.mutate({ era: e.key, subscription_bp: FULL_BP })}
          data-testid={`invest-${e.key}`}
        >
          {e.platform ? 'Subscribe in full' : 'Invest'}
        </Button>
      ) : (
        <Button
          size="compact-xs"
          variant="default"
          loading={invest.isPending}
          onClick={() => invest.mutate({ era: e.key, subscription_bp: 0 })}
          data-testid={`stop-${e.key}`}
        >
          Stop
        </Button>
      )}
      {e.can_rollout && (
        <Button
          size="compact-xs"
          variant="light"
          loading={rollout.isPending}
          onClick={() => rollout.mutate({ era: e.key })}
          data-testid={`rollout-${e.key}`}
        >
          Roll out firm-wide
        </Button>
      )}
      {(invest.error || rollout.error) && (
        <Text size="xs" c="red" data-testid="tech-error">
          {(invest.error ?? rollout.error)?.message}
        </Text>
      )}
    </Group>
  );
}

const eraHelper = createColumnHelper<GameTableFeatures, TechEra>();

function eraColumns(slug: string) {
  return eraHelper.columns([
    eraHelper.accessor('label', { header: 'Era', sortFn: 'alphanumeric' }),
    eraHelper.accessor('strength_pct', {
      header: 'Strength',
      sortFn: 'basic',
      cell: (c) => <span className="tst-num">{c.getValue()}%</span>,
    }),
    eraHelper.accessor('market_pct', {
      header: 'Market adoption',
      sortFn: 'basic',
      cell: (c) => <span className="tst-num">{c.getValue()}%</span>,
    }),
    eraHelper.accessor('adoption_pct', {
      header: 'Our adoption',
      sortFn: 'basic',
      cell: ({ row }) => (
        <span className="tst-num" data-testid={`adoption-${row.original.key}`}>
          {row.original.adoption_pct}%{' '}
          {row.original.rolled_out ? (
            <Badge size="xs" color="teal" variant="light">
              firm-wide
            </Badge>
          ) : row.original.subscription_bp > 0 ? (
            <Badge size="xs" variant="light">
              pilot
            </Badge>
          ) : null}
        </span>
      ),
    }),
    eraHelper.accessor('monthly_cents', {
      header: 'Cost a month',
      sortFn: 'basic',
      cell: ({ row }) => (
        <span className="tst-num">
          {formatMoneyShort(row.original.monthly_cents)}{' '}
          <span className="tst-muted">
            (platform {formatMoneyShort(row.original.platform_cents)}
            {row.original.platform ? ', bought' : ''};{' '}
            {formatMoneyWhole(row.original.subscription_cents)} a lawyer)
          </span>
        </span>
      ),
    }),
    eraHelper.display({
      id: 'actions',
      header: '',
      cell: ({ row }) => <EraActions slug={slug} e={row.original} />,
    }),
  ]);
}

const taskHelper = createColumnHelper<GameTableFeatures, TechTask>();
const taskColumns = taskHelper.columns([
  taskHelper.accessor('key', {
    header: 'Task',
    sortFn: 'alphanumeric',
    cell: (c) => humanize(c.getValue()),
  }),
  taskHelper.accessor('exposure_pct', {
    header: 'AI exposure',
    sortFn: 'basic',
    cell: (c) => <span className="tst-num">{c.getValue()}%</span>,
  }),
  taskHelper.accessor('efficiency_pct', {
    header: 'Our hours (per 100)',
    sortFn: 'basic',
    cell: ({ row }) => (
      <span className="tst-num" data-testid={`task-hours-${row.original.key}`}>
        {row.original.efficiency_pct}
      </span>
    ),
  }),
  taskHelper.accessor('full_pct', {
    header: 'Fully adopted',
    sortFn: 'basic',
    cell: (c) => <span className="tst-num">{c.getValue()}</span>,
  }),
  taskHelper.accessor('market_pct', {
    header: 'Clients expect',
    sortFn: 'basic',
    cell: (c) => <span className="tst-num">{c.getValue()}</span>,
  }),
  taskHelper.accessor('client_cut_bp', {
    header: 'Hourly-bill cut',
    sortFn: 'basic',
    cell: (c) => <span className="tst-num">{formatBpShort(c.getValue())}</span>,
  }),
]);

function Training({ slug, t }: { slug: string; t: Tech['training'] }) {
  const set = useSetTraining(slug);
  const [hours, setHours] = useState<number>(t.hours || t.default);
  return (
    <div className="tst-panel" data-testid="training">
      <h3 className="tst-ptitle">Training programme</h3>
      <Text size="sm">
        <span className="tst-num">{t.hours}</span> hours a lawyer a year (full coverage at{' '}
        {t.full_hours}) for <span className="tst-num">{t.trainees}</span> associates and counsel:{' '}
        <span className="tst-num">{formatMoneyShort(t.monthly_cents)}</span> a month, non-billable.
        Hours AI removes are juniors' learning hours; training buys it back.
      </Text>
      <Group mt="xs" align="end">
        <NumberInput
          w={160}
          label="Hours a year"
          min={t.lo}
          max={t.hi}
          value={hours}
          onChange={(v) => setHours(typeof v === 'number' ? v : t.default)}
          data-testid="training-hours"
        />
        <Button
          loading={set.isPending}
          onClick={() => set.mutate({ hours })}
          data-testid="set-training"
        >
          Set
        </Button>
      </Group>
      {set.error && (
        <Text size="xs" c="red">
          {set.error.message}
        </Text>
      )}
    </div>
  );
}

function Clients({ c }: { c: Tech['clients'] }) {
  return (
    <div className="tst-panel" data-testid="client-expectations">
      <h3 className="tst-ptitle">Client expectations</h3>
      {c.pressure ? (
        <Stack gap={2}>
          <Text size="sm">
            Clients cut hourly bills for hours the market no longer needs: a case{' '}
            <span className="tst-num">{formatBpShort(c.case_cut_bp)}</span>, a deal{' '}
            <span className="tst-num">{formatBpShort(c.deal_cut_bp)}</span>, flow work{' '}
            <span className="tst-num">{formatBpShort(c.flow_cut_bp)}</span>.
          </Text>
          <Text size="sm">
            Cut from bills over the recent months:{' '}
            <span className="tst-num" data-testid="ai-cut-12m">
              {formatMoneyShort(c.cut_12m_cents)}
            </span>
            .
          </Text>
        </Stack>
      ) : (
        <Text size="sm" c="dimmed">
          Clients start pressing hourly bills on AI-exposed work from {c.pressure_from_label}.
        </Text>
      )}
      <Text size="sm" mt={4} data-testid="rfp-standing">
        {c.rfp_asks
          ? `RFPs ask for AI and efficiency: the firm is ${c.rfp_standing ?? 'level'} with the market.`
          : `RFPs ask for AI and efficiency from ${c.rfp_from_year}.`}
      </Text>
    </div>
  );
}

const productHelper = createColumnHelper<GameTableFeatures, TechProduct>();

function productColumns(slug: string, retire: ReturnType<typeof useRetireProduct>) {
  void slug;
  return productHelper.columns([
    productHelper.accessor('label', { header: 'Product', sortFn: 'alphanumeric' }),
    productHelper.accessor('price_pct_of_standard', {
      header: 'Price (of standard fees)',
      sortFn: 'basic',
      cell: (c) => <span className="tst-num">{c.getValue()}%</span>,
    }),
    productHelper.accessor('matters', { header: 'Matters', sortFn: 'basic' }),
    productHelper.accessor('billed_cents', {
      header: 'Billed (standard)',
      sortFn: 'basic',
      cell: ({ row }) => (
        <span className="tst-num">
          {formatMoneyShort(row.original.billed_cents)}{' '}
          <span className="tst-muted">({formatMoneyShort(row.original.standard_cents)})</span>
        </span>
      ),
    }),
    productHelper.accessor('launched_label', { header: 'Launched', sortFn: 'alphanumeric' }),
    productHelper.display({
      id: 'retire',
      header: '',
      cell: ({ row }) =>
        row.original.active ? (
          <Button
            size="compact-xs"
            variant="default"
            onClick={() => retire.mutate(row.original.id)}
          >
            Retire
          </Button>
        ) : (
          <Text size="xs" c="dimmed">
            retired
          </Text>
        ),
    }),
  ]);
}

function Products({ slug, t }: { slug: string; t: Tech }) {
  const launch = useLaunchProduct(slug);
  const retire = useRetireProduct(slug);
  const [kind, setKind] = useState<string | null>(null);
  const [price, setPrice] = useState<number>(t.price_default);
  const table = useTable({
    features: gameTableFeatures,
    columns: productColumns(slug, retire),
    data: t.products,
    getRowId: (r) => String(r.id),
  });
  const chosen = t.kinds.find((k) => k.kind_key === kind);
  return (
    <div className="tst-panel" data-testid="products">
      <h3 className="tst-ptitle">Fixed-fee products</h3>
      <DataTable table={table} label="Products" rowTestId="product-row" empty="No products yet." />
      {t.can_launch ? (
        <Group mt="sm" align="end">
          <Select
            w={320}
            label="Matter kind"
            searchable
            data={t.kinds.map((k) => ({
              value: k.kind_key,
              label: `${k.label} (${k.exposed_pct}% AI-exposed)`,
            }))}
            value={kind}
            onChange={setKind}
            data-testid="product-kind"
          />
          <NumberInput
            w={180}
            label="Price (bp of market cost)"
            min={t.price_lo}
            max={t.price_hi}
            step={500}
            value={price}
            onChange={(v) => setPrice(typeof v === 'number' ? v : t.price_default)}
          />
          <Button
            disabled={!chosen}
            loading={launch.isPending}
            onClick={() =>
              chosen &&
              launch.mutate({
                practice: chosen.practice,
                kind_key: chosen.kind_key,
                price_bp: price,
              })
            }
            data-testid="launch-product"
          >
            Launch
          </Button>
          {chosen && (
            <Text size="xs" c="dimmed">
              The market expects this work at {chosen.market_cost_pct}% of standard fees; the firm
              needs {chosen.hours_pct}% of its base hours.
            </Text>
          )}
        </Group>
      ) : (
        <Text size="sm" c="dimmed" mt="xs">
          Products open at stage {t.product_stage} (the firm is at stage {t.stage}).
        </Text>
      )}
      {(launch.error || retire.error) && (
        <Text size="xs" c="red" data-testid="product-error">
          {(launch.error ?? retire.error)?.message}
        </Text>
      )}
    </div>
  );
}

export function TechScreen() {
  const { slug = '' } = useParams();
  const q = useTech(slug);
  const data = q.data;
  const eras = useTable({
    features: gameTableFeatures,
    columns: eraColumns(slug),
    data: data?.eras ?? [],
    getRowId: (r) => r.key,
  });
  const tasks = useTable({
    features: gameTableFeatures,
    columns: taskColumns,
    data: data?.tasks ?? [],
    getRowId: (r) => r.key,
  });
  if (q.isLoading) return <Text c="dimmed">Loading…</Text>;
  if (q.error || !data)
    return <Alert color="red">Could not load technology: {q.error?.message}</Alert>;
  return (
    <Stack gap="lg">
      <Title order={2}>Technology</Title>
      <RunBy slug={slug} areas={['knowledge']} />
      <Text size="sm" c="dimmed">
        {data.month_label} · {data.lawyers} lawyers · stage {data.stage}
      </Text>
      <div className="tst-panel">
        <h3 className="tst-ptitle">Eras and adoption</h3>
        <DataTable table={eras} label="Eras" rowTestId="era-row" empty="No eras." />
      </div>
      <div className="tst-panel">
        <h3 className="tst-ptitle">Hours by task</h3>
        <DataTable table={tasks} label="Tasks" rowTestId="task-row" empty="No tasks." />
      </div>
      <SimpleGrid cols={{ base: 1, md: 2 }}>
        <Training slug={slug} t={data.training} />
        <Clients c={data.clients} />
      </SimpleGrid>
      <Products slug={slug} t={data} />
    </Stack>
  );
}
