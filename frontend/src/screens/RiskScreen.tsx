import { Alert, Badge, Button, Group, Select, SimpleGrid, Stack, Text, Title } from '@mantine/core';
import { createColumnHelper, useTable } from '@tanstack/react-table';
import { useParams } from 'react-router';
import { DataTable } from '../components/DataTable';
import { RunBy } from '../components/RunBy';
import { formatMoneyShort, humanize } from '../lib/format';
import {
  useRespondCase,
  useRespondClaim,
  useRespondInquiry,
  useRisk,
  useSetPolicyTerms,
  useSetSupervision,
  type Risk,
  type RiskArbitration,
  type RiskAudit,
  type RiskCase,
  type RiskClaim,
  type RiskInquiry,
  type RiskReconciliation,
} from '../lib/riskApi';
import { gameTableFeatures, type GameTableFeatures } from '../lib/table';

// Risk (spec 11.3-11.6, 16; PT-M15): the insurance policy and its renewal, malpractice claims
// with their stages, disciplinary cases, regulators' inquiries, the client account's
// reconciliation, clients' audits and fee arbitrations. Every number is the API's: the screen
// formats, it never computes a game value.

function ClaimActions({ slug, c }: { slug: string; c: RiskClaim }) {
  const respond = useRespondClaim(slug);
  if (c.stage !== 'offer') return null;
  return (
    <Group gap={4} wrap="nowrap">
      <Button
        size="compact-xs"
        loading={respond.isPending}
        onClick={() => respond.mutate({ id: c.id, choice: 'settle' })}
        data-testid={`settle-claim-${c.id}`}
      >
        Settle
      </Button>
      <Button
        size="compact-xs"
        variant="default"
        loading={respond.isPending}
        onClick={() => respond.mutate({ id: c.id, choice: 'contest' })}
        data-testid={`contest-claim-${c.id}`}
      >
        Contest
      </Button>
      {respond.error && (
        <Text size="xs" c="red">
          {respond.error.message}
        </Text>
      )}
    </Group>
  );
}

const claimHelper = createColumnHelper<GameTableFeatures, RiskClaim>();
function claimColumns(slug: string) {
  return claimHelper.columns([
    claimHelper.accessor('client', {
      header: 'Claimant',
      sortFn: 'alphanumeric',
      cell: ({ row }) => (
        <span>
          {row.original.client}{' '}
          <span className="tst-muted">
            ({row.original.matter}; {humanize(row.original.practice)})
          </span>
        </span>
      ),
    }),
    claimHelper.accessor('stage', {
      header: 'Stage',
      sortFn: 'alphanumeric',
      cell: ({ row }) => (
        <span data-testid={`claim-stage-${row.original.id}`}>
          {row.original.outcome ? humanize(row.original.outcome) : humanize(row.original.stage)}{' '}
          {row.original.public && (
            <Badge size="xs" color="red" variant="light">
              public
            </Badge>
          )}
          <span className="tst-muted">
            {' '}
            {row.original.closed_label || row.original.stage_label}
          </span>
        </span>
      ),
    }),
    claimHelper.accessor('demand_cents', {
      header: 'Demand',
      sortFn: 'basic',
      cell: (c) => <span className="tst-num">{formatMoneyShort(c.getValue())}</span>,
    }),
    claimHelper.accessor('merit_lo_pct', {
      header: 'Merit (GC)',
      sortFn: 'basic',
      cell: ({ row }) => (
        <span className="tst-num">
          {row.original.merit_lo_pct}-{row.original.merit_hi_pct}%
        </span>
      ),
    }),
    claimHelper.accessor('offer_cents', {
      header: 'Offer',
      sortFn: 'basic',
      cell: ({ row }) =>
        row.original.offer_cents ? (
          <span className="tst-num">
            {formatMoneyShort(row.original.offer_cents)}{' '}
            <span className="tst-muted">to {row.original.offer_expires_label}</span>
          </span>
        ) : (
          ''
        ),
    }),
    claimHelper.accessor('deductible_paid_cents', {
      header: 'Firm / insurer',
      sortFn: 'basic',
      cell: ({ row }) => (
        <span className="tst-num" data-testid={`claim-paid-${row.original.id}`}>
          {formatMoneyShort(row.original.deductible_paid_cents + row.original.excess_paid_cents)} /{' '}
          {formatMoneyShort(row.original.insurer_paid_cents)}
          {row.original.called_cents > 0 && (
            <span className="tst-muted">
              {' '}
              (capital called {formatMoneyShort(row.original.called_cents)})
            </span>
          )}
        </span>
      ),
    }),
    claimHelper.display({
      id: 'actions',
      header: '',
      cell: ({ row }) => <ClaimActions slug={slug} c={row.original} />,
    }),
  ]);
}

function Answer({
  pending,
  choices,
  onChoose,
  testId,
}: {
  pending: boolean;
  choices: string[];
  onChoose: (c: string) => void;
  testId: string;
}) {
  return (
    <Group gap={4} wrap="nowrap">
      {choices.map((c, i) => (
        <Button
          key={c}
          size="compact-xs"
          variant={i === 0 ? 'filled' : 'default'}
          loading={pending}
          onClick={() => onChoose(c)}
          data-testid={`${testId}-${c}`}
        >
          {humanize(c)}
        </Button>
      ))}
    </Group>
  );
}

const caseHelper = createColumnHelper<GameTableFeatures, RiskCase>();
function caseColumns(respond: ReturnType<typeof useRespondCase>) {
  return caseHelper.columns([
    caseHelper.accessor('name', { header: 'Lawyer', sortFn: 'alphanumeric' }),
    caseHelper.accessor('cause', {
      header: 'Cause',
      sortFn: 'alphanumeric',
      cell: (c) => humanize(c.getValue()),
    }),
    caseHelper.accessor('jurisdiction', { header: 'Before', sortFn: 'alphanumeric' }),
    caseHelper.accessor('stage', {
      header: 'Stage',
      sortFn: 'alphanumeric',
      cell: ({ row }) => (
        <span>
          {row.original.outcome ? humanize(row.original.outcome) : humanize(row.original.stage)}
          {row.original.suspended_until_label && (
            <span className="tst-muted"> until {row.original.suspended_until_label}</span>
          )}
        </span>
      ),
    }),
    caseHelper.display({
      id: 'actions',
      header: '',
      cell: ({ row }) =>
        row.original.stage !== 'closed' && row.original.choice === null ? (
          <Answer
            pending={respond.isPending}
            choices={['cooperate', 'contest']}
            onChoose={(c) => respond.mutate({ id: row.original.id, choice: c })}
            testId={`case-${row.original.id}`}
          />
        ) : (
          <Text size="xs" c="dimmed">
            {row.original.choice ? humanize(row.original.choice) : ''}
          </Text>
        ),
    }),
  ]);
}

const inquiryHelper = createColumnHelper<GameTableFeatures, RiskInquiry>();
function inquiryColumns(respond: ReturnType<typeof useRespondInquiry>) {
  return inquiryHelper.columns([
    inquiryHelper.accessor('regulator', { header: 'Regulator', sortFn: 'alphanumeric' }),
    inquiryHelper.accessor('reason', {
      header: 'Into',
      sortFn: 'alphanumeric',
      cell: (c) => humanize(c.getValue()),
    }),
    inquiryHelper.accessor('fine_hi_cents', {
      header: 'Fine if found',
      sortFn: 'basic',
      cell: ({ row }) => (
        <span className="tst-num">
          {formatMoneyShort(row.original.fine_lo_cents)}-
          {formatMoneyShort(row.original.fine_hi_cents)}
        </span>
      ),
    }),
    inquiryHelper.accessor('stage', {
      header: 'Stage',
      sortFn: 'alphanumeric',
      cell: ({ row }) =>
        row.original.outcome
          ? `${humanize(row.original.outcome)} (${formatMoneyShort(row.original.fine_cents)})`
          : `${humanize(row.original.stage)} to ${row.original.ends_label}`,
    }),
    inquiryHelper.display({
      id: 'actions',
      header: '',
      cell: ({ row }) =>
        row.original.stage !== 'closed' && row.original.choice === null ? (
          <Answer
            pending={respond.isPending}
            choices={['settle', 'contest']}
            onChoose={(c) => respond.mutate({ id: row.original.id, choice: c })}
            testId={`inquiry-${row.original.id}`}
          />
        ) : null,
    }),
  ]);
}

const recHelper = createColumnHelper<GameTableFeatures, RiskReconciliation>();
const recColumns = recHelper.columns([
  recHelper.accessor('label', { header: 'Month', sortFn: 'alphanumeric' }),
  recHelper.accessor('owed_cents', {
    header: 'Owed to clients',
    sortFn: 'basic',
    cell: (c) => <span className="tst-num">{formatMoneyShort(c.getValue())}</span>,
  }),
  recHelper.accessor('bank_cents', {
    header: 'Client bank (as found)',
    sortFn: 'basic',
    cell: (c) => <span className="tst-num">{formatMoneyShort(c.getValue())}</span>,
  }),
  recHelper.accessor('shortfall_cents', {
    header: 'Shortfall',
    sortFn: 'basic',
    cell: ({ row }) =>
      row.original.shortfall_cents ? (
        <span className="tst-num" style={{ color: 'var(--mantine-color-red-5)' }}>
          {formatMoneyShort(row.original.shortfall_cents)} ({row.original.cause}; made good)
        </span>
      ) : (
        <span className="tst-muted">reconciles</span>
      ),
  }),
]);

const auditHelper = createColumnHelper<GameTableFeatures, RiskAudit>();
const auditColumns = auditHelper.columns([
  auditHelper.accessor('label', { header: 'Month', sortFn: 'alphanumeric' }),
  auditHelper.accessor('client', { header: 'Client', sortFn: 'alphanumeric' }),
  auditHelper.accessor('cut_cents', {
    header: 'Cut',
    sortFn: 'basic',
    cell: (c) => <span className="tst-num">{formatMoneyShort(c.getValue())}</span>,
  }),
  auditHelper.accessor('padding_found_cents', {
    header: 'Padding found',
    sortFn: 'basic',
    cell: (c) =>
      c.getValue() ? <span className="tst-num">{formatMoneyShort(c.getValue())}</span> : '',
  }),
]);

const arbHelper = createColumnHelper<GameTableFeatures, RiskArbitration>();
const arbColumns = arbHelper.columns([
  arbHelper.accessor('client', { header: 'Client', sortFn: 'alphanumeric' }),
  arbHelper.accessor('amount_cents', {
    header: 'Disputed',
    sortFn: 'basic',
    cell: (c) => <span className="tst-num">{formatMoneyShort(c.getValue())}</span>,
  }),
  arbHelper.accessor('decide_label', {
    header: 'Award',
    sortFn: 'alphanumeric',
    cell: ({ row }) =>
      row.original.decided
        ? formatMoneyShort(row.original.award_cents)
        : `due ${row.original.decide_label}`,
  }),
]);

function Policy({ slug, r }: { slug: string; r: Risk }) {
  const terms = useSetPolicyTerms(slug);
  const sup = useSetSupervision(slug);
  const p = r.policy;
  return (
    <div className="tst-panel" data-testid="policy">
      <h3 className="tst-ptitle">Insurance</h3>
      {p ? (
        <Text size="sm">
          {p.insurer} ({p.insurer_kind}): limit{' '}
          <span className="tst-num">{formatMoneyShort(p.limit_cents)}</span> a claim, deductible{' '}
          <span className="tst-num">{formatMoneyShort(p.deductible_cents)}</span>; premium{' '}
          <span className="tst-num" data-testid="premium">
            {formatMoneyShort(p.premium_cents)}
          </span>{' '}
          a year ({formatMoneyShort(p.premium_per_lawyer_cents)} a lawyer; experience{' '}
          <span className="tst-num">{p.mod.toFixed(2)}</span>, market rate{' '}
          <span className="tst-num">{(p.rate_bp / 100).toFixed(2)}%</span> of fees); renews{' '}
          {p.renews_label}.
        </Text>
      ) : (
        <Text size="sm" c="dimmed">
          No policy yet: the first month buys one.
        </Text>
      )}
      {r.compulsory_limit_cents > 0 && (
        <Text size="xs" c="dimmed">
          Compulsory cover: at least {formatMoneyShort(r.compulsory_limit_cents)} a claim.
        </Text>
      )}
      <Group mt="sm" align="end">
        <Select
          w={200}
          label="Insurer at renewal"
          clearable
          data={r.insurers.map((i) => ({ value: i.key, label: `${i.label} (${i.kind})` }))}
          value={r.terms.insurer ?? null}
          onChange={(v) => terms.mutate({ ...r.terms, insurer: v })}
          data-testid="terms-insurer"
        />
        <Select
          w={160}
          label="Limit"
          clearable
          data={r.limits.map((x) => ({ value: String(x.cents), label: formatMoneyShort(x.cents) }))}
          value={r.terms.limit_cents === null ? null : String(r.terms.limit_cents)}
          onChange={(v) => terms.mutate({ ...r.terms, limit_cents: v === null ? null : Number(v) })}
          data-testid="terms-limit"
        />
        <Select
          w={160}
          label="Deductible"
          clearable
          data={r.deductibles.map((x) => ({
            value: String(x.cents),
            label: formatMoneyShort(x.cents),
          }))}
          value={r.terms.deductible_cents === null ? null : String(r.terms.deductible_cents)}
          onChange={(v) =>
            terms.mutate({ ...r.terms, deductible_cents: v === null ? null : Number(v) })
          }
          data-testid="terms-deductible"
        />
      </Group>
      {terms.error && (
        <Text size="xs" c="red">
          {terms.error.message}
        </Text>
      )}
      <Group mt="sm">
        <Text size="sm">
          Supervision: <span data-testid="supervision">{humanize(r.supervision)}</span>
        </Text>
        <Button
          size="compact-xs"
          variant="default"
          loading={sup.isPending}
          onClick={() => sup.mutate({ supervision: r.supervision === 'lax' ? 'standard' : 'lax' })}
          data-testid="toggle-supervision"
        >
          {r.supervision === 'lax' ? 'Tighten supervision' : 'Relax supervision'}
        </Button>
      </Group>
    </div>
  );
}

export function RiskScreen() {
  const { slug = '' } = useParams();
  const q = useRisk(slug);
  const respondCase = useRespondCase(slug);
  const respondInquiry = useRespondInquiry(slug);
  const data = q.data;
  const claims = useTable({
    features: gameTableFeatures,
    columns: claimColumns(slug),
    data: data?.claims ?? [],
    getRowId: (r) => String(r.id),
  });
  const cases = useTable({
    features: gameTableFeatures,
    columns: caseColumns(respondCase),
    data: data?.cases ?? [],
    getRowId: (r) => String(r.id),
  });
  const inquiries = useTable({
    features: gameTableFeatures,
    columns: inquiryColumns(respondInquiry),
    data: data?.inquiries ?? [],
    getRowId: (r) => String(r.id),
  });
  const recs = useTable({
    features: gameTableFeatures,
    columns: recColumns,
    data: data?.reconciliations ?? [],
    getRowId: (r) => r.label,
  });
  const audits = useTable({
    features: gameTableFeatures,
    columns: auditColumns,
    data: data?.audits ?? [],
    getRowId: (r) => String(r.bill_id),
  });
  const arbs = useTable({
    features: gameTableFeatures,
    columns: arbColumns,
    data: data?.arbitrations ?? [],
    getRowId: (r) => String(r.id),
  });
  if (q.isLoading) return <Text c="dimmed">Loading…</Text>;
  if (q.error || !data) return <Alert color="red">Could not load risk: {q.error?.message}</Alert>;
  return (
    <Stack gap="lg">
      <Title order={2}>Risk</Title>
      <RunBy slug={slug} areas={['risk']} />
      <Text size="sm" c="dimmed">
        {data.lawyers} lawyers · {data.claims_12m} claims noticed in the last 12 months
      </Text>
      <Policy slug={slug} r={data} />
      <div className="tst-panel">
        <h3 className="tst-ptitle">Malpractice claims</h3>
        <DataTable table={claims} label="Claims" rowTestId="claim-row" empty="No claims." />
      </div>
      <SimpleGrid cols={{ base: 1, md: 2 }}>
        <div className="tst-panel">
          <h3 className="tst-ptitle">Disciplinary cases</h3>
          <DataTable table={cases} label="Cases" rowTestId="case-row" empty="No cases." />
        </div>
        <div className="tst-panel">
          <h3 className="tst-ptitle">Regulators' inquiries</h3>
          <DataTable
            table={inquiries}
            label="Inquiries"
            rowTestId="inquiry-row"
            empty="No inquiries."
          />
        </div>
      </SimpleGrid>
      <div className="tst-panel" data-testid="trust">
        <h3 className="tst-ptitle">Client account reconciliation</h3>
        <DataTable
          table={recs}
          label="Reconciliations"
          rowTestId="reconciliation-row"
          empty="No client money held."
        />
      </div>
      <SimpleGrid cols={{ base: 1, md: 2 }}>
        <div className="tst-panel">
          <h3 className="tst-ptitle">Clients' audits</h3>
          <DataTable table={audits} label="Audits" rowTestId="audit-row" empty="No audits." />
        </div>
        <div className="tst-panel">
          <h3 className="tst-ptitle">Fee arbitration</h3>
          <DataTable
            table={arbs}
            label="Arbitrations"
            rowTestId="arbitration-row"
            empty="No fee arbitrations."
          />
        </div>
      </SimpleGrid>
    </Stack>
  );
}
