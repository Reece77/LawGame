import { Badge, Button, Card, Group, Stack, Text, Title } from '@mantine/core';
import { Link, useParams } from 'react-router';
import { useInbox, useMarkInboxRead, type InboxItem } from '../lib/api';

// The inbox (spec 16; TST's inbox, first cut): offers accepted and declined, the summer
// programme, a class starting, resignations, bonuses. Newest first.
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
  const markRead = useMarkInboxRead(slug);
  const items = inbox.data ?? [];
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
            <Text size="sm">{item.body}</Text>
          </Card>
        );
      })}
    </Stack>
  );
}
