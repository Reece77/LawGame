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
import {
  useCloseOffice,
  useMoveLawyer,
  useOfferContracts,
  useOffices,
  useOpenOffice,
  usePracticeMarket,
  useSeekAdmission,
  type CityRow,
  type OfficeLawyer,
  type OfficeRow,
  type Offices,
} from '../lib/api';
import { formatMoney, formatMoneyShort, formatWhole, humanize } from '../lib/format';
import { gameTableFeatures, type GameTableFeatures } from '../lib/table';

// Offices (spec 8.8, 11.1, 5.7; PT-M11): the firm's offices with their leases, headcount,
// managing partner, local clients and P&L; the cities it may open in; each office's bar rules;
// admissions; and the UK path's training contracts and trainees. Every number is the API's.

const num = (v: number | string) => <span className="tst-num">{v}</span>;

const officeHelper = createColumnHelper<GameTableFeatures, OfficeRow>();
const officeColumns = officeHelper.columns([
  officeHelper.accessor('label', { header: 'Office', sortFn: 'alphanumeric' }),
  officeHelper.accessor('how', { header: 'Opened by', cell: (c) => humanize(c.getValue()) }),
  officeHelper.accessor('opened', { header: 'Since' }),
  officeHelper.accessor('lawyers', {
    header: 'Lawyers',
    sortFn: 'basic',
    cell: (c) => num(formatWhole(c.getValue())),
  }),
  officeHelper.accessor('seats', {
    header: 'Seats',
    cell: (c) => num(c.getValue() ?? '—'),
  }),
  officeHelper.accessor('rent_cents', {
    header: 'Rent / month',
    cell: (c) => num(c.getValue() === null ? 'per head' : formatMoneyShort(c.getValue() ?? 0)),
  }),
  officeHelper.accessor('lease_months_left', {
    header: 'Lease left',
    cell: (c) => num(c.getValue() === null ? '—' : `${c.getValue()} mo`),
  }),
  officeHelper.accessor('managing_partner', {
    header: 'Office MP',
    cell: (c) => c.getValue() ?? '—',
  }),
  officeHelper.accessor('clients', { header: 'Clients', cell: (c) => num(c.getValue()) }),
  officeHelper.accessor((r) => r.pnl.year_fees_cents, {
    id: 'fees',
    header: 'Fees (12 mo)',
    sortFn: 'basic',
    cell: (c) => num(formatMoneyShort(c.getValue())),
  }),
  officeHelper.accessor((r) => r.pnl.year_profit_cents, {
    id: 'profit',
    header: 'Profit (12 mo)',
    sortFn: 'basic',
    cell: (c) => num(formatMoneyShort(c.getValue())),
  }),
  officeHelper.accessor((r) => r.pnl.month_profit_cents, {
    id: 'month',
    header: 'Last month',
    sortFn: 'basic',
    cell: (c) => num(formatMoneyShort(c.getValue())),
  }),
]);

const cityHelper = createColumnHelper<GameTableFeatures, CityRow>();
const cityColumns = cityHelper.columns([
  cityHelper.accessor('label', {
    header: 'City',
    sortFn: 'alphanumeric',
    cell: ({ row }) => (
      <span>
        {row.original.label}
        {row.original.is_home && (
          <Badge ml="xs" size="xs" variant="light">
            Home
          </Badge>
        )}
        {row.original.has_office && !row.original.is_home && (
          <Badge ml="xs" size="xs" variant="light" color="green">
            Office
          </Badge>
        )}
      </span>
    ),
  }),
  cityHelper.accessor('jurisdiction_label', { header: 'Bar' }),
  cityHelper.accessor('demand_pct', {
    header: 'Market',
    sortFn: 'basic',
    cell: (c) => num(`${c.getValue()}%`),
  }),
  cityHelper.accessor('rate_pct', { header: 'Rates', cell: (c) => num(`${c.getValue()}%`) }),
  cityHelper.accessor('pay_pct', { header: 'Pay', cell: (c) => num(`${c.getValue()}%`) }),
  cityHelper.accessor('rent_per_seat_cents', {
    header: 'Rent / seat',
    cell: (c) => num(formatMoneyShort(c.getValue())),
  }),
  cityHelper.accessor((r) => r.rivals.map((f) => f.name).join(', '), {
    id: 'rivals',
    header: 'Firms there',
  }),
]);

const lawyerHelper = createColumnHelper<GameTableFeatures, OfficeLawyer>();

function OfficesTable({ o }: { o: Offices }) {
  const table = useTable({
    features: gameTableFeatures,
    columns: officeColumns,
    data: o.offices,
    getRowId: (r) => String(r.id),
  });
  return (
    <div className="tst-panel" data-testid="offices-table">
      <h3 className="tst-ptitle">Offices</h3>
      <DataTable table={table} label="Offices" rowTestId="office-row" />
      <Text size="xs" c="dimmed" mt="xs">
        Lease liabilities {formatMoney(o.lease_liabilities_cents)} · leases run {o.lease_months}{' '}
        months · fit-out {formatMoneyShort(o.fit_out_per_seat_cents)} a seat
      </Text>
    </div>
  );
}

function CitiesTable({ o }: { o: Offices }) {
  const table = useTable({
    features: gameTableFeatures,
    columns: cityColumns,
    data: o.cities,
    getRowId: (r) => r.key,
  });
  return (
    <div className="tst-panel" data-testid="cities-table">
      <h3 className="tst-ptitle">Cities</h3>
      <DataTable table={table} label="Cities" />
    </div>
  );
}

function OpenForm({ o, slug }: { o: Offices; slug: string }) {
  const open = useOpenOffice(slug);
  const practices = usePracticeMarket(slug).data ?? [];
  const cities = o.cities.filter((c) => !c.has_office && !c.is_home);
  const [city, setCity] = useState<string | null>(null);
  const [how, setHow] = useState<string>('team_lift');
  const [seats, setSeats] = useState<string>(String(o.seat_sizes[1] ?? o.seat_sizes[0]));
  const [practice, setPractice] = useState<string | null>(null);
  const [rival, setRival] = useState<string | null>(null);
  const [partner, setPartner] = useState<string | null>(null);
  const [partners, setPartners] = useState<number>(2);
  const [associates, setAssociates] = useState<number>(4);
  const chosen = o.cities.find((c) => c.key === city);
  const partnersHere = o.lawyers.filter(
    (l) => l.office_id === 0 && (l.level === 'equity partner' || l.level === 'income partner'),
  );
  return (
    <div className="tst-panel" data-testid="open-office">
      <h3 className="tst-ptitle">Open an office</h3>
      <Group align="end" wrap="wrap">
        <Select
          label="City"
          data={cities.map((c) => ({ value: c.key, label: c.label }))}
          value={city}
          onChange={setCity}
          data-testid="open-city"
        />
        <Select
          label="How"
          data={[
            { value: 'team_lift', label: 'Team lift' },
            { value: 'lateral_group', label: 'Lateral group' },
            { value: 'organic', label: 'Organic start' },
          ]}
          value={how}
          onChange={(v) => setHow(v ?? 'team_lift')}
          data-testid="open-how"
        />
        <Select
          label="Seats"
          data={o.seat_sizes.map((s) => String(s))}
          value={seats}
          onChange={(v) => setSeats(v ?? seats)}
          data-testid="open-seats"
        />
        {how === 'organic' ? (
          <Select
            label="Partner who moves"
            data={partnersHere.map((l) => ({ value: String(l.person_id), label: l.name }))}
            value={partner}
            onChange={setPartner}
            data-testid="open-partner"
          />
        ) : (
          <>
            <Select
              label="Practice"
              data={practices.map((p) => ({ value: p.key, label: p.label }))}
              value={practice}
              onChange={setPractice}
              data-testid="open-practice"
            />
            {how === 'team_lift' && (
              <Select
                label="From"
                data={(chosen?.rivals ?? []).map((f) => ({ value: f.key, label: f.name }))}
                value={rival}
                onChange={setRival}
                data-testid="open-rival"
              />
            )}
            <NumberInput
              label="Partners"
              min={1}
              max={10}
              value={partners}
              onChange={(v) => setPartners(Number(v))}
              w={90}
            />
            <NumberInput
              label="Associates"
              min={0}
              max={60}
              value={associates}
              onChange={(v) => setAssociates(Number(v))}
              w={100}
            />
          </>
        )}
        <Button
          disabled={city === null}
          loading={open.isPending}
          data-testid="open-submit"
          onClick={() =>
            city &&
            open.mutate({
              city,
              seats: Number(seats),
              how: how as 'organic' | 'lateral_group' | 'team_lift',
              practice,
              rival_key: how === 'team_lift' ? rival : null,
              partner_id: how === 'organic' && partner ? Number(partner) : null,
              partners,
              associates,
            })
          }
        >
          Sign the lease
        </Button>
      </Group>
      {open.error && (
        <Alert color="red" mt="xs" data-testid="open-error">
          {open.error.message}
        </Alert>
      )}
    </div>
  );
}

function OfficeActions({ o, slug }: { o: Offices; slug: string }) {
  const close = useCloseOffice(slug);
  const contracts = useOfferContracts(slug);
  const [count, setCount] = useState<number>(2);
  const uk = new Set(o.cities.filter((c) => c.region === 'uk').map((c) => c.key));
  const leased = o.offices.filter((x) => x.id !== 0);
  if (leased.length === 0) return null;
  return (
    <div className="tst-panel" data-testid="office-actions">
      <h3 className="tst-ptitle">Office decisions</h3>
      <Stack gap="xs">
        {leased.map((x) => (
          <Group key={x.id} gap="sm">
            <Text w={180}>{x.label}</Text>
            {uk.has(x.city) && (
              <>
                <NumberInput
                  aria-label="Training contracts"
                  min={1}
                  max={30}
                  value={count}
                  onChange={(v) => setCount(Number(v))}
                  w={80}
                />
                <Button
                  size="xs"
                  variant="light"
                  loading={contracts.isPending}
                  data-testid={`offer-contracts-${x.id}`}
                  onClick={() => contracts.mutate({ officeId: x.id, count })}
                >
                  Offer training contracts
                </Button>
              </>
            )}
            <Button
              size="xs"
              color="red"
              variant="subtle"
              loading={close.isPending}
              onClick={() => close.mutate(x.id)}
            >
              Close (a one-off)
            </Button>
          </Group>
        ))}
      </Stack>
      {(contracts.error ?? close.error) && (
        <Alert color="red" mt="xs">
          {(contracts.error ?? close.error)?.message}
        </Alert>
      )}
    </div>
  );
}

function LawyersTable({ o, slug }: { o: Offices; slug: string }) {
  const seek = useSeekAdmission(slug);
  const move = useMoveLawyer(slug);
  const officeName = new Map(o.offices.map((x) => [x.id, x.label]));
  const juris = o.cities
    .map((c) => ({ value: c.jurisdiction, label: c.jurisdiction_label }))
    .filter((v, i, a) => a.findIndex((w) => w.value === v.value) === i);
  const columns = lawyerHelper.columns([
    lawyerHelper.accessor('name', { header: 'Lawyer', sortFn: 'alphanumeric' }),
    lawyerHelper.accessor('level', { header: 'Level' }),
    lawyerHelper.accessor((r) => officeName.get(r.office_id) ?? '', {
      id: 'office',
      header: 'Office',
    }),
    lawyerHelper.accessor((r) => r.admissions.join(', '), { id: 'bars', header: 'Admitted' }),
    lawyerHelper.display({
      id: 'act',
      header: '',
      cell: ({ row }) => (
        <Group gap={4} wrap="nowrap">
          <Select
            size="xs"
            placeholder="Admission"
            w={170}
            data={[
              ...juris.map((j) => ({ value: `exam:${j.value}`, label: `Exam: ${j.label}` })),
              ...juris.map((j) => ({ value: `motion:${j.value}`, label: `Motion: ${j.label}` })),
              { value: 'register:ew_rfl', label: 'Register as foreign lawyer' },
            ]}
            onChange={(v) => {
              if (!v) return;
              const [route, jurisdiction] = v.split(':');
              seek.mutate({
                person_id: row.original.person_id,
                jurisdiction,
                route: route as 'exam' | 'motion' | 'register',
              });
            }}
          />
          <Select
            size="xs"
            placeholder="Move to"
            w={130}
            data={o.offices.map((x) => ({ value: String(x.id), label: x.label }))}
            onChange={(v) =>
              v !== null && move.mutate({ person_id: row.original.person_id, office_id: Number(v) })
            }
          />
        </Group>
      ),
    }),
  ]);
  const table = useTable({
    features: gameTableFeatures,
    columns,
    data: o.lawyers,
    getRowId: (r) => String(r.person_id),
  });
  return (
    <div className="tst-panel" data-testid="lawyers-table">
      <h3 className="tst-ptitle">Lawyers and admissions</h3>
      {(seek.error ?? move.error) && (
        <Alert color="red" mb="xs">
          {(seek.error ?? move.error)?.message}
        </Alert>
      )}
      <DataTable table={table} label="Lawyers" />
    </div>
  );
}

function UkPath({ o }: { o: Offices }) {
  if (o.contracts.length === 0 && o.trainees.length === 0 && o.exams.length === 0) return null;
  return (
    <div className="tst-panel" data-testid="uk-path">
      <h3 className="tst-ptitle">Training and admissions in progress</h3>
      <Stack gap={4}>
        {o.contracts.map((c, i) => (
          <Text key={`c${i}`} size="sm">
            {c.count} training contracts offered {c.offered}: {c.filled ? 'joined' : 'join'}{' '}
            {c.starts}
          </Text>
        ))}
        {o.trainees.map((t) => (
          <Text key={t.person_id} size="sm" data-testid="trainee-row">
            {t.name}: seat in {t.seat} (seats: {t.seats.join(', ')}); qualifies {t.qualifies}
          </Text>
        ))}
        {o.exams.map((e) => (
          <Text key={`${e.person_id}-${e.jurisdiction}`} size="sm">
            {e.name}: {e.kind} in {e.jurisdiction}, result {e.result}
          </Text>
        ))}
      </Stack>
    </div>
  );
}

function Rules({ o }: { o: Offices }) {
  return (
    <SimpleGrid cols={{ base: 1, md: 2 }}>
      {o.rules.map((r) => (
        <div className="tst-panel" key={r.jurisdiction} data-testid={`rules-${r.jurisdiction}`}>
          <h3 className="tst-ptitle">{r.label}</h3>
          <Stack gap={2}>
            <Text size="sm">Regulator: {r.regulator}</Text>
            <Text size="sm">Ownership: {r.ownership}</Text>
            {r.insurance_min_cents !== null && (
              <Text size="sm">
                Indemnity insurance compulsory: at least {formatMoneyShort(r.insurance_min_cents)} a
                claim ({formatMoneyShort(r.insurance_llp_min_cents ?? 0)} for an LLP)
              </Text>
            )}
            {r.client_money && <Text size="sm">Client money: {r.client_money}</Text>}
            {r.llp && <Text size="sm">Firms practise as LLPs</Text>}
            {r.foreign_lawyers && (
              <Text size="sm" c="dimmed">
                {r.foreign_lawyers}
              </Text>
            )}
          </Stack>
        </div>
      ))}
    </SimpleGrid>
  );
}

export function OfficesScreen() {
  const { slug = '' } = useParams();
  const offices = useOffices(slug);
  if (offices.isLoading) return <Text>Loading…</Text>;
  if (offices.error || !offices.data)
    return <Alert color="red">{offices.error?.message ?? 'No offices'}</Alert>;
  const o = offices.data;
  return (
    <Stack gap="md" data-testid="offices-screen">
      <Title order={2}>Offices</Title>
      <OfficesTable o={o} />
      <OfficeActions o={o} slug={slug} />
      <OpenForm o={o} slug={slug} />
      <CitiesTable o={o} />
      <Rules o={o} />
      <UkPath o={o} />
      <LawyersTable o={o} slug={slug} />
    </Stack>
  );
}
