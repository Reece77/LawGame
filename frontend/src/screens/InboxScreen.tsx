import { Badge, Button, Card, Group, Stack, Text, Title } from '@mantine/core';
import { Link, useParams } from 'react-router';
import { EventCard } from '../components/EventCard';
import { PitchCard } from '../components/PitchCard';
import { useEvents, useInbox, useMarkInboxRead, type GameEvent, type InboxItem } from '../lib/api';
import { useLeadership, type SeatPitch } from '../lib/leadership';

// The inbox (spec 16; TST's inbox): offers, the summer programme, resignations, bonuses,
// written texts (briefings, letters, memos, seat reports) and events (PT-M6), whose cards are
// answered here; seat holders' pitches (PT-M8) are answered here too.
// Newest first.
function linkTo(slug: string, item: InboxItem): string | null {
  if (item.link_kind === 'person' && item.link_id !== null)
    return `/game/${slug}/people/${item.link_id}`;
  if (item.link_kind === 'candidate' || item.link_kind === 'search')
    return `/game/${slug}/recruitment`;
  if (item.link_kind === 'org') return `/game/${slug}/org`;
  if (item.link_kind === 'rankings') return `/game/${slug}/rankings`; // PT-M16
  if (item.link_kind === 'press') return `/game/${slug}/press`;
  if (item.link_kind === 'tech') return `/game/${slug}/technology`; // PT-M14
  if (item.link_kind === 'risk') return `/game/${slug}/risk`; // PT-M15
  if (item.link_kind === 'automation')
    return item.template === 'automation_digest' && item.link_id !== null
      ? `/game/${slug}/automation?month=${item.link_id}`
      : `/game/${slug}/automation`;
  return null;
}

export function InboxScreen() {
  const { slug = '' } = useParams();
  const inbox = useInbox(slug);
  const events = useEvents(slug);
  const markRead = useMarkInboxRead(slug);
  const items = inbox.data ?? [];
  const byId = new Map<number, GameEvent>((events.data ?? []).map((e) => [e.id, e]));
  const leadership = useLeadership(slug);
  const pitches = new Map<number, SeatPitch>(
    (leadership.data?.pitches ?? []).map((p) => [p.id, p]),
  );
  const shownPitches = new Set<number>();
  return (
    <Stack>
      <Group justify="space-between">
        <Title order={2}>Inbox</Title>
        <Button
          variant="subtle"
          onClick={() => markRead.mutate()}
          disabled={items.every((i) => i.read)}
        >
          Mark all read
        </Button>
      </Group>
      {items.length === 0 && <Text c="dimmed">Nothing yet.</Text>}
      {items.map((item) => {
        const event =
          item.link_kind === 'event' && item.link_id !== null ? byId.get(item.link_id) : undefined;
        if (event) return <EventCard key={item.id} slug={slug} event={event} />;
        const pitch =
          item.link_kind === 'pitch' && item.link_id !== null
            ? pitches.get(item.link_id)
            : undefined;
        if (pitch && item.template === 'pitch' && !shownPitches.has(pitch.id)) {
          shownPitches.add(pitch.id);
          return <PitchCard key={item.id} slug={slug} pitch={pitch} />;
        }
        const to = linkTo(slug, item);
        return (
          <Card withBorder key={item.id} data-testid="inbox-item">
            <Group justify="space-between">
              <Text fw={item.read ? 400 : 600}>
                {to ? <Link to={to}>{item.title}</Link> : item.title}
              </Text>
              <Group gap={6}>
                {!item.read && (
                  <Badge size="xs" variant="filled">
                    New
                  </Badge>
                )}
                <Text size="sm" c="dimmed">
                  {item.date_label}
                </Text>
              </Group>
            </Group>
            <Text size="sm" style={{ whiteSpace: 'pre-line' }}>
              {item.body}
            </Text>
          </Card>
        );
      })}
    </Stack>
  );
}
