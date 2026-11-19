import { Badge, Table, Text, Title } from '@mantine/core';
import { createColumnHelper, tableFeatures, useTable } from '@tanstack/react-table';
import { useMemo } from 'react';
import { Link, useParams } from 'react-router';
import { AttributeRange } from '../components/AttributeRange';
import { rangeText } from '../lib/attr';
import { StrainBar } from '../components/StrainBar';
import { usePeople, type PersonRow } from '../lib/api';
import { humanize } from '../lib/format';

// The squad (spec 16): level, practice, ability and potential as the firm sees them, the
// familiarity grid and strain. Hours and utilisation arrive with matters (PT-M3a).
const features = tableFeatures({});
const helper = createColumnHelper<typeof features, PersonRow>();
const EMPTY: PersonRow[] = [];

function familiarityColumns(sample: PersonRow | undefined) {
  return (sample?.familiarity ?? []).map((fam, index) =>
    helper.display({
      id: `fam_${fam.practice}`,
      header: () => <span title={fam.label}>{fam.short_label}</span>,
      cell: ({ row }) => {
        const f = row.original.familiarity[index];
        return f ? <AttributeRange range={f} label={`${row.original.name}, ${f.label}`} /> : null;
      },
    }),
  );
}

const baseColumns = [
  helper.display({
    id: 'name',
    header: 'Name',
    cell: ({ row }) => (
      <>
        <Link to={`${row.original.id}`}>{row.original.name}</Link>
        {row.original.is_founder && (
          <Badge size="xs" ml={6} variant="light">
            You
          </Badge>
        )}
      </>
    ),
  }),
  helper.display({ id: 'level', header: 'Level', cell: ({ row }) => humanize(row.original.level) }),
  helper.display({ id: 'role', header: 'Role', cell: ({ row }) => row.original.role_label }),
  helper.display({
    id: 'age',
    header: 'Age',
    cell: ({ row }) => <span className="tst-num">{row.original.age}</span>,
  }),
  helper.display({
    id: 'ability',
    header: 'Ability',
    cell: ({ row }) => <span className="tst-num">{rangeText(row.original.ability)}</span>,
  }),
  helper.display({
    id: 'potential',
    header: 'Potential',
    cell: ({ row }) => row.original.potential,
  }),
  helper.display({
    id: 'strain',
    header: 'Strain',
    cell: ({ row }) =>
      row.original.strain == null ? (
        '—'
      ) : (
        <StrainBar
          strain={row.original.strain}
          burntOut={row.original.burnt_out ?? false}
          compact
        />
      ),
  }),
];

export function PeopleScreen() {
  const { slug = '' } = useParams();
  const people = usePeople(slug);
  const data = people.data ?? EMPTY;
  return <PeopleTable data={data} loading={people.isLoading} />;
}

function PeopleTable({ data, loading }: { data: PersonRow[]; loading: boolean }) {
  const sample = data[0];
  const practices = (sample?.familiarity ?? []).map((f) => f.practice).join(',');
  // Columns stay stable while the practice list does (TanStack Table v9's rule).
  // eslint-disable-next-line react-hooks/exhaustive-deps
  const columns = useMemo(() => [...baseColumns, ...familiarityColumns(sample)], [practices]);
  const table = useTable({ features, columns, data });
  return (
    <>
      <Title order={2} mb="md">
        People
      </Title>
      {loading ? (
        <Text c="dimmed">Loading…</Text>
      ) : (
        <div className="tst-table-wrap">
          <Table striped highlightOnHover data-testid="people-table">
            <Table.Thead>
              {table.getHeaderGroups().map((group) => (
                <Table.Tr key={group.id}>
                  {group.headers.map((header) => (
                    <Table.Th key={header.id}>
                      {header.isPlaceholder ? null : <table.FlexRender header={header} />}
                    </Table.Th>
                  ))}
                </Table.Tr>
              ))}
            </Table.Thead>
            <Table.Tbody>
              {table.getRowModel().rows.map((row) => (
                <Table.Tr key={row.id}>
                  {row.getAllCells().map((cell) => (
                    <Table.Td key={cell.id}>
                      <table.FlexRender cell={cell} />
                    </Table.Td>
                  ))}
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
        </div>
      )}
    </>
  );
}
