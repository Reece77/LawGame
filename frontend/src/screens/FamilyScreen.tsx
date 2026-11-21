import {
  Alert,
  Badge,
  Button,
  Card,
  Group,
  NumberInput,
  Select,
  Slider,
  Stack,
  Table,
  Text,
  Title,
} from '@mantine/core';
import { useState } from 'react';
import { useParams } from 'react-router';
import { useFamily, useFamilyAction, type Family, type FamilyMember } from '../lib/api';
import { formatBpPercent, formatMoneyWhole, humanize } from '../lib/format';

// The Family screen (spec 2.4, 16; PT-M17; TST 45.1-45.3, 45.6): family time and the
// relationship, each member's public facts and the player's view of them (ranges and a
// potential phrase, never the number), education, a child joining the firm, and estate
// planning with the year's estate-tax quote.

type Act = ReturnType<typeof useFamilyAction>;
const money = (c: number) => formatMoneyWhole(c);

function Member({ m, f, act }: { m: FamilyMember; f: Family; act: Act }) {
  const [tier, setTier] = useState<string | null>(null);
  return (
    <Table.Tr data-testid={`member-${m.person_id}`}>
      <Table.Td>{m.name}</Table.Td>
      <Table.Td>{humanize(m.relation)}</Table.Td>
      <Table.Td className="tst-num">{m.age}</Table.Td>
      <Table.Td className="tst-num">{m.closeness ?? '—'}</Table.Td>
      <Table.Td>
        {m.ability.lo}-{m.ability.hi} ({m.potential})
      </Table.Td>
      <Table.Td>
        {[m.school && `${m.school} school`, m.law_school && `${m.law_school} law school`]
          .filter(Boolean)
          .join(', ') || '—'}
        {m.at_firm && (
          <Badge ml="xs" size="xs">
            {humanize(m.level ?? 'at the firm')}
          </Badge>
        )}
      </Table.Td>
      <Table.Td>
        {f.active && (m.can_choose_school || m.can_choose_law_school) && (
          <Group gap="xs" wrap="nowrap">
            <Select
              size="xs"
              w={110}
              placeholder={m.can_choose_school ? 'School' : 'Law school'}
              data={m.can_choose_school ? f.schools : f.law_schools}
              value={tier}
              onChange={setTier}
            />
            <Button
              size="xs"
              variant="light"
              disabled={!tier}
              onClick={() =>
                tier &&
                act.mutate({
                  kind: 'education',
                  child_id: m.person_id,
                  stage: m.can_choose_school ? 'school' : 'law_school',
                  tier,
                })
              }
            >
              Choose
            </Button>
          </Group>
        )}
        {f.active && m.can_join && (
          <Button size="xs" onClick={() => act.mutate({ kind: 'join', child_id: m.person_id })}>
            Offer a place at the firm
          </Button>
        )}
        {f.active && m.at_firm && (
          <Button
            size="xs"
            variant="subtle"
            onClick={() => act.mutate({ kind: 'mentor', child_id: m.person_id, on: !m.mentored })}
          >
            {m.mentored ? 'Stop mentoring' : 'Mentor'}
          </Button>
        )}
      </Table.Td>
    </Table.Tr>
  );
}

export function FamilyScreen() {
  const { slug = '' } = useParams();
  const q = useFamily(slug);
  const act = useFamilyAction(slug);
  const [time, setTime] = useState<number | null>(null);
  const [trust, setTrust] = useState<string | number>(100000);
  const f = q.data;
  if (!f) return <Text>Loading...</Text>;
  if (f.setting === 'none')
    return (
      <Stack>
        <Title order={2}>Family</Title>
        <Text data-testid="no-family">
          You started this game without a family (New Game&apos;s Family setting).
        </Text>
      </Stack>
    );
  return (
    <Stack>
      <Title order={2}>Family</Title>
      {act.error && <Alert color="red">{act.error.message}</Alert>}
      {!f.active && (
        <Alert>This is your predecessor&apos;s family; it is shown for the record.</Alert>
      )}
      <Card withBorder>
        <Group>
          <Text>
            Relationship {f.relationship ?? '—'}
            {f.married ? ' (married)' : ''}
          </Text>
          <Text w={260}>Family time {time ?? f.family_time} energy a month</Text>
          <Slider
            w={200}
            min={0}
            max={f.max_time}
            value={time ?? f.family_time}
            onChange={setTime}
            onChangeEnd={(v) => act.mutate({ kind: 'time', energy: v })}
            disabled={!f.active}
            data-testid="family-time"
          />
        </Group>
      </Card>
      <Table data-testid="family-members">
        <Table.Thead>
          <Table.Tr>
            <Table.Th>Name</Table.Th>
            <Table.Th>Relation</Table.Th>
            <Table.Th>Age</Table.Th>
            <Table.Th>Closeness</Table.Th>
            <Table.Th>Ability (potential)</Table.Th>
            <Table.Th>Education</Table.Th>
            <Table.Th />
          </Table.Tr>
        </Table.Thead>
        <Table.Tbody>
          {f.members.map((m) => (
            <Member key={m.person_id} m={m} f={f} act={act} />
          ))}
        </Table.Tbody>
      </Table>
      {f.estate && (
        <Card withBorder data-testid="estate">
          <Title order={4}>Estate</Title>
          <Text size="sm">
            Estate {money(f.estate.estate_cents)}; exemption {money(f.estate.exemption_cents)} at{' '}
            {formatBpPercent(f.estate.rate_bp)}: tax {money(f.estate.tax_cents)} if it passed today.
            Lifetime gifts {money(f.estate.lifetime_gifts_cents)}; in trust{' '}
            {money(f.estate.trust_cents)}.
          </Text>
          {f.active && (
            <Group mt="xs" align="end">
              <NumberInput label="Into the trust ($)" value={trust} onChange={setTrust} w={160} />
              <Button
                variant="light"
                onClick={() =>
                  act.mutate({ kind: 'trust', amount_cents: Math.round(Number(trust) * 100) })
                }
              >
                Move
              </Button>
            </Group>
          )}
        </Card>
      )}
      {f.notes.length > 0 && (
        <Stack gap={2}>
          {f.notes.map((n, i) => (
            <Text size="xs" key={i}>
              {n.when}: {n.text}
            </Text>
          ))}
        </Stack>
      )}
    </Stack>
  );
}
