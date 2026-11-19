import { Badge, Group, SimpleGrid, Stack, Table, Text, Title } from '@mantine/core';
import { Link, useParams } from 'react-router';
import { AttributeRange } from '../components/AttributeRange';
import { PersonOrgPanel } from '../components/PersonOrgPanel';
import { rangeText } from '../lib/attr';
import { StrainBar } from '../components/StrainBar';
import { usePerson, type PersonProfile } from '../lib/api';
import { formatMoneyWhole, humanize } from '../lib/format';

// The Person profile (spec 16): skills and personality as revealed ranges, the practice
// familiarity grid, potential as a phrase, and strain for the player's own people.
const GROUPS: { key: string; label: string }[] = [
  { key: 'legal', label: 'Legal craft' },
  { key: 'client', label: 'Client' },
  { key: 'working', label: 'Working' },
  { key: 'leadership', label: 'Leadership' },
  { key: 'business_services', label: 'Business services' },
];

function Panel({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="tst-panel">
      <h3 className="tst-ptitle">{title}</h3>
      {children}
    </div>
  );
}

function Rows({ items }: { items: PersonProfile['skills'] }) {
  return (
    <>
      {items.map((s) => (
        <div className="tst-row" key={s.key}>
          <span>{s.label}</span>
          <AttributeRange range={s} label={s.label} />
        </div>
      ))}
    </>
  );
}

export function PersonScreen() {
  const { slug = '', personId = '' } = useParams();
  const person = usePerson(slug, Number(personId));
  if (person.error) return <Text c="red">{person.error.message}</Text>;
  if (!person.data) return <Text c="dimmed">Loading…</Text>;
  const p = person.data;
  return (
    <Stack gap="md">
      <Group justify="space-between" align="flex-end">
        <div>
          <Text size="sm">
            <Link to={`/game/${slug}/people`}>People</Link>
          </Text>
          <Title order={2} data-testid="person-name">
            {p.name}
          </Title>
          <Text c="dimmed">
            {humanize(p.level)} · {p.role_label} · age {p.age}
            {p.school_tier ? ` · ${p.school_tier} law school` : ''}
          </Text>
        </div>
        <Group gap="xs">
          {p.is_founder && <Badge variant="light">You</Badge>}
          {p.founding_partner && <Badge variant="outline">Founding partner</Badge>}
        </Group>
      </Group>

      <SimpleGrid cols={{ base: 1, md: 3 }}>
        <Panel title="Summary">
          <div className="tst-row">
            <span>Ability</span>
            <span className="tst-num">{rangeText(p.ability)}</span>
          </div>
          <div className="tst-row">
            <span>Potential</span>
            <span data-testid="potential">{p.potential}</span>
          </div>
          <div className="tst-row">
            <span>Bar admissions</span>
            <span>{p.bar_admissions.length ? p.bar_admissions.join(', ') : '—'}</span>
          </div>
          {p.background && (
            <div className="tst-row">
              <span>Background</span>
              <span>{p.background}</span>
            </div>
          )}
          {p.book_cents != null && (
            <div className="tst-row">
              <span>Book of business</span>
              <span className="tst-num">{formatMoneyWhole(p.book_cents)} a year</span>
            </div>
          )}
          <div className="tst-row">
            <span>Capacity / target</span>
            <span className="tst-num">
              {p.capacity_hours.toLocaleString()} / {p.billable_target_hours.toLocaleString()} h
            </span>
          </div>
          {p.strain != null && (
            <div className="tst-row">
              <span>Strain</span>
              <StrainBar strain={p.strain} burntOut={p.burnt_out ?? false} />
            </div>
          )}
          <div className="tst-row">
            <span>Interests</span>
            <span>{p.interests ? p.interests.map(humanize).join(', ') : 'Unknown'}</span>
          </div>
          <div className="tst-row">
            <span>Work style</span>
            <span>{p.work_style ? humanize(p.work_style) : 'Unknown'}</span>
          </div>
          {p.tags.length > 0 && (
            <div className="tst-row">
              <span>Traits</span>
              <span>{p.tags.map((t) => t.label).join(', ')}</span>
            </div>
          )}
        </Panel>

        <Panel title="Practice familiarity">
          <Table data-testid="familiarity-grid">
            <Table.Tbody>
              {p.familiarity.map((f) => (
                <Table.Tr key={f.practice}>
                  <Table.Td>{f.label}</Table.Td>
                  <Table.Td ta="right">
                    <AttributeRange range={f} label={f.label} />
                  </Table.Td>
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
        </Panel>

        <Panel title="Personality">
          <Rows items={p.personality} />
        </Panel>
      </SimpleGrid>

      {p.own_firm && <PersonOrgPanel slug={slug} personId={p.id} />}

      <SimpleGrid cols={{ base: 1, md: 3 }} data-testid="skills">
        {GROUPS.map((g) => (
          <Panel key={g.key} title={g.label}>
            <Rows items={p.skills.filter((s) => s.group === g.key)} />
          </Panel>
        ))}
      </SimpleGrid>
    </Stack>
  );
}
