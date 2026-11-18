import { Button, Stack, Text, Title } from '@mantine/core';
import { Link } from 'react-router';

export function MainMenu() {
  return (
    <Stack maw={420} mx="auto" mt={120} gap="md">
      <Title order={1}>Partner Track</Title>
      <Text c="dimmed">Found a firm in January 2005. Build a global partnership by 2034.</Text>
      <Button component={Link} to="/new">
        New game
      </Button>
      <Button component={Link} to="/saves" variant="default">
        Load game
      </Button>
      <Button component={Link} to="/settings" variant="subtle">
        Settings
      </Button>
    </Stack>
  );
}
