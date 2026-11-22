import {
  Alert,
  Badge,
  Button,
  Card,
  Group,
  NumberInput,
  Select,
  SimpleGrid,
  Stack,
  Switch,
  Text,
  Title,
} from '@mantine/core';
import { useState } from 'react';
import { Link } from 'react-router';
import { humanize } from '../lib/format';
import { useLeadership, useLeadershipAction, type Seat, type SeatSlot } from '../lib/leadership';

// The Org screen's Leadership panel (PT-M8; spec 9.1-9.2): every seat open at the firm's
// stage with its holder (revealed ranges and a fit band, never a score), vacancies with the
// best-fit candidates, authority and guardrails, and what holders did under authority.
// Every rule is the engine's; this only shows and sends.
const FIT_COLOR: Record<string, string> = {
  strong: 'teal',
  good: 'green',
  fair: 'yellow',
  weak: 'red',
  unknown: 'gray',
};

type Act = ReturnType<typeof useLeadershipAction>['mutate'];

export function LeadershipPanel({ slug }: { slug: string }) {
  const view = useLeadership(slug);
  const action = useLeadershipAction(slug);
  if (view.error) return <Text c="red">{view.error.message}</Text>;
  if (!view.data) return <Text c="dimmed">Loading…</Text>;
  const v = view.data;
  const open = v.seats.filter((s) => s.open && s.slots.length > 0);
  const later = v.seats.filter((s) => !s.open);
  return (
    <div className="tst-panel" data-testid="leadership-panel">
      <h3 className="tst-ptitle">Leadership</h3>
      {action.error && (
        <Alert
          color="red"
          data-testid="leadership-error"
          withCloseButton
          onClose={() => action.reset()}
        >
          {action.error.message}
        </Alert>
      )}
      <Group mb="xs" gap="xs">
        <Text size="sm">
          Stage {v.stage}. Executive committee: {v.exco_mode} by the{' '}
          {v.exco_mode === 'elected' ? 'partners each December' : 'managing partner'}.
        </Text>
        {v.exco_proposed !== null && v.exco_proposed !== undefined ? (
          <Badge size="sm" variant="light">
            {v.exco_proposed ? 'Elected' : 'Appointed'} committee proposed for December
          </Badge>
        ) : (
          <Button
            size="compact-xs"
            variant="subtle"
            onClick={() => action.mutate({ kind: 'exco_term', elected: v.exco_mode !== 'elected' })}
          >
            Propose an {v.exco_mode === 'elected' ? 'appointed' : 'elected'} committee
          </Button>
        )}
      </Group>
      {open.length === 0 && (
        <Text size="sm" c="dimmed" mb="xs">
          No seats open yet: the first business-services chiefs arrive at stage 2.
        </Text>
      )}
      <SimpleGrid cols={{ base: 1, md: 2 }}>
        {open.map((seat) =>
          seat.slots.map((slot) => (
            <SlotCard
              key={`${seat.key}-${slot.slot}`}
              seat={seat}
              slot={slot}
              slug={slug}
              act={action.mutate}
              busy={action.isPending}
            />
          )),
        )}
      </SimpleGrid>
      {later.length > 0 && (
        <Text size="xs" c="dimmed" mt="xs">
          Later: {later.map((s) => `${s.label} (stage ${s.stage})`).join(', ')}.
        </Text>
      )}
    </div>
  );
}

function SlotCard({
  seat,
  slot,
  slug,
  act,
  busy,
}: {
  seat: Seat;
  slot: SeatSlot;
  slug: string;
  act: Act;
  busy: boolean;
}) {
  const [pick, setPick] = useState<string | null>(null);
  const h = slot.holder;
  const title = slot.label === seat.label ? seat.label : `${seat.short}: ${slot.label}`;
  return (
    <Card withBorder data-testid={`seat-${seat.key}-${slot.slot}`}>
      <Group justify="space-between" mb={4}>
        <Title order={5}>{title}</Title>
        {h ? (
          <Badge color={FIT_COLOR[h.fit]} data-testid="seat-fit">
            {h.fit} fit
          </Badge>
        ) : (
          <Badge color="red" variant="light">
            vacant
          </Badge>
        )}
      </Group>
      <Text size="xs" c="dimmed" mb={6}>
        {seat.effect}
      </Text>
      {h && (
        <Stack gap={2} mb={6}>
          <Group gap="xs">
            <Link to={`/game/${slug}/people/${h.person_id}`} data-testid="seat-holder">
              {h.name}
            </Link>
            <Text size="xs" c="dimmed">
              {humanize(h.level)}
              {h.hits + h.misses > 0 && ` · pitches ${h.hits} hit, ${h.misses} missed`}
            </Text>
            {!h.eligible && (
              <Badge size="xs" color="orange">
                no longer eligible: counts vacant
              </Badge>
            )}
          </Group>
          <Text size="xs">
            {h.ranges
              .map((r) => `${r.label} ${r.lo === r.hi ? r.lo : `${r.lo}-${r.hi}`}`)
              .join(' · ')}
          </Text>
          {seat.who !== 'player' && (
            <Group>
              <Button
                size="compact-xs"
                variant="subtle"
                color="red"
                onClick={() =>
                  act({ kind: 'appoint', seat: seat.key, slot: slot.slot, personId: null })
                }
              >
                Vacate
              </Button>
            </Group>
          )}
        </Stack>
      )}
      {seat.who !== 'player' && (!h || !h.eligible) && (
        <Group align="flex-end" mb={6}>
          <Select
            size="xs"
            label="Candidates (best fit first)"
            placeholder={slot.candidates.length ? 'Choose' : 'Nobody eligible'}
            data={slot.candidates.map((c) => ({
              value: String(c.person_id),
              label: `${c.name} (${humanize(c.level)}, ${c.fit})`,
            }))}
            value={pick}
            onChange={setPick}
            data-testid="seat-candidates"
          />
          <Button
            size="xs"
            disabled={pick === null}
            loading={busy}
            data-testid="seat-appoint"
            onClick={() => {
              if (pick)
                act({ kind: 'appoint', seat: seat.key, slot: slot.slot, personId: Number(pick) });
              setPick(null);
            }}
          >
            Appoint
          </Button>
        </Group>
      )}
      {seat.authority_does && h && <Authority seat={seat} slot={slot} act={act} />}
      {slot.decisions.length > 0 && (
        <Stack gap={0} mt={6}>
          {slot.decisions.slice(0, 3).map((d, i) => (
            <Text size="xs" key={i}>
              {d.date_label}: {d.text}
            </Text>
          ))}
        </Stack>
      )}
    </Card>
  );
}

function Authority({ seat, slot, act }: { seat: Seat; slot: SeatSlot; act: Act }) {
  const [rails, setRails] = useState<Record<string, number>>(() =>
    Object.fromEntries(slot.guardrails.map((g) => [g.key, g.value])),
  );
  const send = (enabled: boolean) =>
    act({
      kind: 'authority',
      seat: seat.key,
      slot: slot.slot,
      enabled,
      guardrails: Object.entries(rails).map(([key, value]) => ({ key, value })),
    });
  return (
    <Stack gap={4}>
      <Switch
        size="xs"
        label={`Authority: ${seat.authority_does}`}
        checked={slot.authority_enabled}
        onChange={(e) => send(e.currentTarget.checked)}
        data-testid="seat-authority"
      />
      {slot.guardrails.length > 0 && (
        <Group align="flex-end" gap="xs">
          {slot.guardrails.map((g) => (
            <NumberInput
              key={g.key}
              size="xs"
              w={150}
              label={g.label}
              min={g.min}
              max={g.max}
              value={rails[g.key] ?? g.value}
              onChange={(value) => setRails({ ...rails, [g.key]: Number(value) })}
            />
          ))}
          <Button size="compact-xs" variant="light" onClick={() => send(slot.authority_enabled)}>
            Set guardrails
          </Button>
        </Group>
      )}
    </Stack>
  );
}
