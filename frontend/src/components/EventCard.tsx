import { Badge, Button, Card, Group, List, Stack, Text } from '@mantine/core';
import { useChooseEvent, type GameEvent } from '../lib/api';

// One event (spec 15; TST's event card): its words, and each choice with its effects in words
// and numbers as the API describes them. An open event can be answered here; Continue answers
// minor and major ones with their first choice, and a critical one must be answered first.
const SEVERITY_COLOR: Record<GameEvent['severity'], string> = {
  minor: 'gray',
  major: 'yellow',
  critical: 'red',
};

export function EventCard({ slug, event }: { slug: string; event: GameEvent }) {
  const choose = useChooseEvent(slug);
  const open = event.status === 'open';
  return (
    <Card
      withBorder
      data-testid="event-card"
      data-severity={event.severity}
      data-event-id={event.id}
    >
      <Group justify="space-between" mb={4}>
        <Group gap={6}>
          <Badge size="sm" color={SEVERITY_COLOR[event.severity]} variant="filled">
            {event.severity}
          </Badge>
          <Badge size="sm" variant="light">
            {event.category}
          </Badge>
          {event.storyline && (
            <Badge size="sm" variant="outline">
              {event.storyline}
            </Badge>
          )}
        </Group>
        <Text size="sm" c="dimmed">
          {event.date_label}
        </Text>
      </Group>
      <Text fw={600}>{event.title}</Text>
      <Text size="sm" mb="xs">
        {event.body}
      </Text>
      <Stack gap={6}>
        {event.choices.map((choice) => {
          const chosen = event.chosen === choice.key;
          return (
            <Group key={choice.key} justify="space-between" wrap="nowrap" align="flex-start">
              <div>
                <Text size="sm" fw={chosen ? 700 : 500}>
                  {choice.key}. {choice.label}
                  {chosen && (event.status === 'auto' ? ' (chosen at Continue)' : ' (chosen)')}
                </Text>
                <List size="xs" c="dimmed">
                  {choice.effects.map((effect) => (
                    <List.Item key={effect}>{effect}</List.Item>
                  ))}
                </List>
              </div>
              {open && (
                <Button
                  size="xs"
                  variant={choice.key === 'A' ? 'filled' : 'default'}
                  loading={choose.isPending}
                  onClick={() => choose.mutate({ eventId: event.id, choice: choice.key })}
                >
                  Choose {choice.key}
                </Button>
              )}
            </Group>
          );
        })}
      </Stack>
      {choose.error && (
        <Text size="sm" c="red" mt="xs">
          {choose.error.message}
        </Text>
      )}
    </Card>
  );
}
