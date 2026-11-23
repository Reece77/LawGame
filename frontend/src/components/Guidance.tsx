import { Button, Card, Checkbox, Group, List, Stack, Text, Title } from '@mantine/core';
import { useState } from 'react';
import { Link } from 'react-router';
import { useGuidance } from '../lib/api';

// The Overview's guidance (PT-M7; TST M29's 42.2 and 42.3): What next, and the guided first
// year's Getting started checklist. Everything is the API's; dismissing the checklist is a
// browser setting (localStorage), like a table's view.
const ROUTES: Record<string, string> = {
  event: 'inbox',
  finance: 'finance',
  matter: 'matters',
  matters: 'matters',
  partnership: 'partnership',
  market: 'market',
  recruitment: 'recruitment',
  clients: 'clients',
  org: 'org',
  rankings: 'rankings', // PT-M16
  press: 'press',
};

function route(slug: string, kind: string, id?: number | null): string {
  const base = `/game/${slug}/${ROUTES[kind] ?? ''}`;
  return kind === 'matter' && id ? `${base}/${id}` : base;
}

function dismissKey(slug: string): string {
  return `ptk.gettingStarted.${slug}`;
}

function readDismissed(slug: string): boolean {
  try {
    return window.localStorage.getItem(dismissKey(slug)) === '1';
  } catch {
    return false;
  }
}

export function Guidance({ slug }: { slug: string }) {
  const guidance = useGuidance(slug);
  const [dismissed, setDismissed] = useState(() => readDismissed(slug));
  if (!guidance.data) return null;
  const g = guidance.data;
  const dismiss = () => {
    try {
      window.localStorage.setItem(dismissKey(slug), '1');
    } catch {
      // a private window: the checklist simply stays
    }
    setDismissed(true);
  };
  return (
    <Group align="flex-start" mt="md">
      <Card withBorder maw={460} data-testid="what-next">
        <Title order={4} mb="xs">
          What next
        </Title>
        {g.what_next.length === 0 ? (
          <Text size="sm" c="dimmed">
            Nothing needs you this month.
          </Text>
        ) : (
          <List size="sm" spacing={4}>
            {g.what_next.map((item) => (
              <List.Item key={item.key} data-testid="what-next-item">
                {item.text} <Link to={route(slug, item.link_kind, item.link_id)}>Open</Link>
              </List.Item>
            ))}
          </List>
        )}
      </Card>
      {g.first_year && !dismissed && (
        <Card withBorder maw={460} data-testid="getting-started">
          <Group justify="space-between" mb="xs">
            <Title order={4}>Getting started</Title>
            <Button size="xs" variant="subtle" onClick={dismiss}>
              Dismiss
            </Button>
          </Group>
          <Stack gap={4}>
            {g.getting_started.map((step) => (
              <Checkbox
                key={step.key}
                readOnly
                checked={step.done}
                data-testid={`step-${step.key}`}
                label={step.text}
              />
            ))}
          </Stack>
        </Card>
      )}
    </Group>
  );
}
