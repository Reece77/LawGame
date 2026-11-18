import { Anchor, Stack, Text, Title } from '@mantine/core';
import { Link } from 'react-router';

// The LLM budget meter arrives with events (PT-M6); the adapter defaults to templates offline.
export function SettingsScreen() {
  return (
    <Stack maw={560} mx="auto" mt={80} gap="md">
      <Title order={2}>Settings</Title>
      <Text c="dimmed">
        Story text budget: $10 a calendar month (events arrive in a later milestone).
      </Text>
      <Anchor component={Link} to="/">
        Back
      </Anchor>
    </Stack>
  );
}
