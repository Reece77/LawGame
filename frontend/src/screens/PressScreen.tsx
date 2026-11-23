import {
  Alert,
  Badge,
  Button,
  Card,
  Group,
  NumberInput,
  Select,
  Stack,
  Text,
  Title,
} from '@mantine/core';
import { createColumnHelper, useTable } from '@tanstack/react-table';
import { useMemo, useState } from 'react';
import { useParams } from 'react-router';
import { DataTable } from '../components/DataTable';
import {
  useAnswerPress,
  usePracticeLabels,
  usePracticesScreen,
  usePress,
  type Press,
  type PressCause,
  type PressClaim,
  type PressFeud,
  type PressMoment,
  type PressStatement,
} from '../lib/api';
import { humanize } from '../lib/format';
import { bandText, claimProblem, signedDelta, type ClaimDraft } from '../lib/standing';
import { gameTableFeatures, type GameTableFeatures } from '../lib/table';

// Press (spec 12.1-12.2, 16; PT-M16): the firm's credibility and its causes, press moments
// (the ones answerable this month first, with a tone and an optional public claim), the
// claims made and where they stand publicly, rival managing partners' statements and feuds.
// Every number is the API's; the claim form checks only the API's input rules.

const CLAIM_LABELS: Record<string, string> = {
  headcount: 'Headcount: grow to a number of lawyers',
  no_layoffs: 'No layoffs for a year',
  match_scale: 'Match the associate salary scale for a year',
  band: 'Reach a directory band in a practice',
};
const STATUS_COLOR: Record<string, string> = { open: 'accent', kept: 'teal', broken: 'red' };

function Causes({ causes, testId }: { causes: PressCause[]; testId: string }) {
  if (causes.length === 0)
    return (
      <Text size="sm" c="dimmed">
        No changes yet.
      </Text>
    );
  return (
    <Stack gap={2} data-testid={testId}>
      {causes.slice(0, 8).map((c, i) => (
        <Text size="xs" key={i}>
          <span className="tst-num">{signedDelta(c.delta)}</span> {c.cause}{' '}
          <span className="tst-muted">({c.date_label})</span>
        </Text>
      ))}
    </Stack>
  );
}

// --- An open moment: tone buttons and an optional claim ---------------------------------------

function OpenMoment({ slug, m, p }: { slug: string; m: PressMoment; p: Press }) {
  const answer = useAnswerPress(slug);
  const practices = usePracticesScreen(slug).data ?? [];
  const practiceLabel = usePracticeLabels(slug);
  const [draft, setDraft] = useState<ClaimDraft>({
    kind: null,
    practice: null,
    target: null,
    months: null,
  });
  const ctx = {
    lawyers: p.lawyers,
    claimMonths: p.claim_months,
    claimsOpen: p.claims_open,
    claimsMax: p.claims_max,
  };
  const timed = draft.kind === 'headcount' || draft.kind === 'band';
  const send = (tone: string) =>
    answer.mutate({
      momentId: m.id,
      body: {
        tone,
        claim: draft.kind,
        practice: draft.kind === 'band' ? draft.practice : null,
        target: timed ? draft.target : null,
        months: timed ? draft.months : null,
      },
    });
  return (
    <Card withBorder data-testid="moment-open">
      <Group justify="space-between">
        <Text fw={600}>The press asks about {m.about}</Text>
        <Text size="sm" c="dimmed">
          {m.date_label}
        </Text>
      </Group>
      {m.detail && <Text size="sm">{m.detail}</Text>}
      {(m.person || m.practice || m.rival) && (
        <Text size="xs" c="dimmed" data-testid="moment-about">
          {[m.person, m.practice && practiceLabel(m.practice), m.rival].filter(Boolean).join(' · ')}
        </Text>
      )}
      <Group mt="sm" align="end" data-testid="claim-form">
        <Select
          w={320}
          label="Make a public claim (optional)"
          placeholder="No claim"
          clearable
          data={p.claim_kinds.map((k) => ({ value: k, label: CLAIM_LABELS[k] ?? humanize(k) }))}
          value={draft.kind}
          onChange={(kind) => setDraft({ ...draft, kind })}
          data-testid="claim-kind"
        />
        {draft.kind === 'band' && (
          <Select
            w={220}
            label="Practice"
            data={practices.map((x) => ({
              value: x.key,
              label: `${x.label} (${bandText(x.band)})`,
            }))}
            value={draft.practice}
            onChange={(practice) => setDraft({ ...draft, practice })}
          />
        )}
        {timed && (
          <>
            <NumberInput
              w={140}
              label={draft.kind === 'band' ? 'Target band' : `Lawyers (now ${p.lawyers})`}
              min={draft.kind === 'band' ? 1 : p.lawyers + 1}
              max={draft.kind === 'band' ? 6 : undefined}
              value={draft.target ?? ''}
              onChange={(v) => setDraft({ ...draft, target: typeof v === 'number' ? v : null })}
              data-testid="claim-target"
            />
            <NumberInput
              w={120}
              label={`Months (${p.claim_months[0]}-${p.claim_months[1]})`}
              min={p.claim_months[0]}
              max={p.claim_months[1]}
              value={draft.months ?? ''}
              onChange={(v) => setDraft({ ...draft, months: typeof v === 'number' ? v : null })}
              data-testid="claim-months"
            />
          </>
        )}
      </Group>
      <Group mt="sm">
        {p.tones.map((tone) => {
          const problem = claimProblem(draft, tone, ctx);
          return (
            <Button
              key={tone}
              size="xs"
              variant={tone === 'bold' ? 'filled' : 'light'}
              data-testid={`tone-${tone}`}
              disabled={problem !== null}
              title={problem ?? undefined}
              loading={answer.isPending && answer.variables?.body.tone === tone}
              onClick={() => send(tone)}
            >
              {humanize(tone)}
            </Button>
          );
        })}
        <Text size="xs" c="dimmed">
          Costs {p.energy} energy. Claims open {p.claims_open}/{p.claims_max}.
        </Text>
      </Group>
      {draft.kind !== null && (
        <Text size="xs" c="dimmed">
          {claimProblem(draft, 'bold', ctx) ?? 'A bold or measured answer makes this claim.'}
        </Text>
      )}
      {answer.error && (
        <Alert mt="xs" color="red">
          {answer.error.message}
        </Alert>
      )}
    </Card>
  );
}

// --- Tables ----------------------------------------------------------------------------------

const momentHelper = createColumnHelper<GameTableFeatures, PressMoment>();
const momentColumns = momentHelper.columns([
  momentHelper.accessor('date_label', { header: 'When' }),
  momentHelper.accessor('about', { header: 'About' }),
  momentHelper.accessor((m) => m.person ?? '', {
    id: 'person',
    header: 'Who',
    cell: (c) => c.getValue() || <span className="tst-muted">—</span>,
  }),
  momentHelper.accessor('detail', { header: 'Detail' }),
  momentHelper.accessor('status', {
    header: 'Status',
    sortFn: 'alphanumeric',
    cell: (c) => humanize(c.getValue()),
  }),
  momentHelper.display({
    id: 'answer',
    header: 'Answer',
    cell: ({ row }) => {
      const m = row.original;
      if (!m.tone) return <span className="tst-muted">—</span>;
      return (
        <span>
          {humanize(m.tone)}
          {m.by_office && <span className="tst-muted"> (press office)</span>}
          {m.backfired && (
            <Badge ml="xs" size="xs" color="red" variant="light">
              Backfired
            </Badge>
          )}
        </span>
      );
    },
  }),
]);

const claimHelper = createColumnHelper<GameTableFeatures, PressClaim>();
const claimColumns = claimHelper.columns([
  claimHelper.accessor('words', { header: 'Claim' }),
  claimHelper.accessor('made_label', { header: 'Made' }),
  claimHelper.accessor('deadline_label', { header: 'Deadline' }),
  claimHelper.accessor('status', {
    header: 'Status',
    sortFn: 'alphanumeric',
    cell: (c) => (
      <Badge size="sm" variant="light" color={STATUS_COLOR[c.getValue()] ?? 'gray'}>
        {humanize(c.getValue())}
      </Badge>
    ),
  }),
  claimHelper.accessor('progress', { header: 'Progress' }),
]);

const statementHelper = createColumnHelper<GameTableFeatures, PressStatement>();
const statementColumns = statementHelper.columns([
  statementHelper.accessor('date_label', { header: 'When' }),
  statementHelper.accessor('rival', { header: 'Firm', sortFn: 'alphanumeric' }),
  statementHelper.accessor('kind', { header: 'Kind', cell: (c) => humanize(c.getValue()) }),
  statementHelper.accessor('text', { header: 'Statement' }),
]);

const feudHelper = createColumnHelper<GameTableFeatures, PressFeud>();
const feudColumns = feudHelper.columns([
  feudHelper.accessor('rival', { header: 'Firm', sortFn: 'alphanumeric' }),
  feudHelper.accessor('score', {
    header: 'Feud',
    sortFn: 'basic',
    cell: ({ row }) => (
      <span className="tst-num">
        {row.original.score}
        {row.original.rivalry && (
          <Badge ml="xs" size="xs" color="warn" variant="light">
            Rivalry
          </Badge>
        )}
      </span>
    ),
  }),
  feudHelper.display({
    id: 'causes',
    header: 'Causes',
    cell: ({ row }) =>
      row.original.causes.length === 0 ? (
        <span className="tst-muted">—</span>
      ) : (
        <span>
          {row.original.causes
            .slice(-3)
            .map((c) => `${signedDelta(c.delta)} ${c.cause} (${c.date_label})`)
            .join('; ')}
        </span>
      ),
  }),
]);

// --- Screen ----------------------------------------------------------------------------------

export function PressScreen() {
  const { slug = '' } = useParams();
  const q = usePress(slug);
  const data = q.data;
  const open = useMemo(() => (data?.moments ?? []).filter((m) => m.open), [data]);
  const recent = useMemo(() => (data?.moments ?? []).filter((m) => !m.open), [data]);
  const moments = useTable({
    features: gameTableFeatures,
    columns: momentColumns,
    data: recent,
    getRowId: (m) => String(m.id),
  });
  const claims = useTable({
    features: gameTableFeatures,
    columns: claimColumns,
    data: data?.claims ?? [],
    getRowId: (c) => String(c.id),
  });
  const statements = useTable({
    features: gameTableFeatures,
    columns: statementColumns,
    data: data?.statements ?? [],
    getRowId: (s) => String(s.id),
  });
  const feuds = useTable({
    features: gameTableFeatures,
    columns: feudColumns,
    data: data?.feuds ?? [],
    getRowId: (f) => String(f.rival_id),
  });
  if (q.isLoading) return <Text c="dimmed">Loading…</Text>;
  if (q.error || !data)
    return <Alert color="red">Could not load the press: {q.error?.message}</Alert>;
  return (
    <Stack gap="lg" data-testid="press-screen">
      <Title order={2}>Press</Title>
      <div className="tst-panel">
        <h3 className="tst-ptitle">Credibility</h3>
        <Text size="xl" fw={600} className="tst-num" data-testid="credibility">
          {data.credibility} / 100
        </Text>
        <Causes causes={data.credibility_causes} testId="credibility-causes" />
      </div>
      <div>
        <Title order={4} mb="xs">
          This month
        </Title>
        {open.length === 0 ? (
          <Text size="sm" c="dimmed" data-testid="no-open-moments">
            No press moment to answer this month.
          </Text>
        ) : (
          <Stack>
            {open.map((m) => (
              <OpenMoment key={m.id} slug={slug} m={m} p={data} />
            ))}
          </Stack>
        )}
      </div>
      <div className="tst-panel" data-testid="moments-table">
        <h3 className="tst-ptitle">Recent moments</h3>
        <DataTable table={moments} label="Press moments" empty="No press moments yet." />
      </div>
      <div className="tst-panel" data-testid="claims-table">
        <h3 className="tst-ptitle">
          Public claims ({data.claims_open}/{data.claims_max} open)
        </h3>
        <DataTable
          table={claims}
          label="Public claims"
          rowTestId="claim-row"
          empty="No public claims made."
        />
      </div>
      <div className="tst-panel" data-testid="statements-table">
        <h3 className="tst-ptitle">Rivals&apos; statements</h3>
        <DataTable table={statements} label="Statements" empty="No statements yet." />
      </div>
      <div className="tst-panel" data-testid="feuds-table">
        <h3 className="tst-ptitle">Feuds</h3>
        <DataTable table={feuds} label="Feuds" empty="No feuds." />
      </div>
    </Stack>
  );
}
