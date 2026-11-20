import { Badge, Button, Card, Group, Stack, Text, Title } from '@mantine/core';
import { Link, useParams } from 'react-router';
import { EventCard } from '../components/EventCard';
import { useEvents, useInbox, useMarkInboxRead, type GameEvent, type InboxItem } from '../lib/api';

// The inbox (spec 16; TST's inbox): offers, the summer programme, resignations, bonuses,
// written texts (briefings, letters, memos) and events (PT-M6), whose cards are answered here.
// Newest first.
function linkTo(slug: string, item: InboxItem): string | null {
  if (item.link_kind === 'person' && item.link_id !== null)
    return `/game/${slug}/people/${item.link_id}`;
  if (item.link_kind === 'candidate' || item.link_kind === 'search')
    return `/game/${slug}/recruitment`;
  return null;
}

export function InboxScreen() {
  const { slug = '' } = useParams();
  const inbox = useInbox(slug);
  const events = useEvents(slug);
  const markRead = useMarkInboxRead(slug);
  const items = inbox.data ?? [];
  const byId = new Map<number, GameEvent>((events.data ?? []).map((e) => [e.id, e]));
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
