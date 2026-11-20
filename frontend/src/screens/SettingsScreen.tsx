import {
  Anchor,
  Card,
  Group,
  NumberInput,
  Progress,
  Stack,
  Switch,
  Text,
  Title,
} from '@mantine/core';
import { Link } from 'react-router';
import { useLlmMeter, useLlmSettings, useSetLlmSettings } from '../lib/api';
import { formatMoney } from '../lib/format';

// The story-text settings (ADR-0005 sections 6-7; PT-M6): offline mode writes every event and
// text from templates; otherwise Claude writes them within the monthly budget, then templates.
export function SettingsScreen() {
  const settings = useLlmSettings();
  const meter = useLlmMeter();
  const save = useSetLlmSettings();
  const s = settings.data;
  const m = meter.data;
  const used = m && m.budget_cents > 0 ? Math.min(100, (100 * m.spent_cents) / m.budget_cents) : 0;
  return (
    <Stack maw={560} mx="auto" mt={80} gap="md">
      <Title order={2}>Settings</Title>
      {s && (
        <Card withBorder>
          <Title order={4} mb="xs">
            Story text
          </Title>
          <Switch
            label="Offline mode (templates only)"
            data-testid="offline-switch"
            checked={s.adapter === 'templates'}
            onChange={(e) =>
              save.mutate({
                adapter: e.currentTarget.checked ? 'templates' : 'claude',
                monthly_budget_cents: s.monthly_budget_cents,
              })
            }
          />
          <Text size="sm" c="dimmed" mt={4} data-testid="writer-in-use">
            Writing with: {s.in_use}
            {s.adapter === 'claude' && !s.key_present && ' (no API key found: templates are used)'}
          </Text>
          <NumberInput
            mt="sm"
            label="Monthly budget (dollars)"
            min={0}
            max={1000}
            value={s.monthly_budget_cents / 100}
            onChange={(value) =>
              typeof value === 'number' &&
              save.mutate({ adapter: s.adapter, monthly_budget_cents: Math.round(value * 100) })
            }
          />
        </Card>
      )}
      {m && (
        <Card withBorder data-testid="budget-meter">
          <Group justify="space-between">
            <Text fw={600}>This month ({m.month})</Text>
            <Text size="sm">
              {formatMoney(m.spent_cents)} of {formatMoney(m.budget_cents)}
            </Text>
          </Group>
          <Progress value={used} mt="xs" />
          <Text size="sm" c="dimmed" mt="xs">
            {m.calls} calls; {m.events_claude} events written by Claude, {m.events_rejected}{' '}
            replaced by templates; resets {m.reset_date}.
          </Text>
        </Card>
      )}
      <Anchor component={Link} to="/">
        Back
      </Anchor>
    </Stack>
  );
}
