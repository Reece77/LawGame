import { Button, Stack, Text, Title } from '@mantine/core';
import { Link, useNavigate } from 'react-router';
import { usePracticeSave } from '../lib/api';

export function MainMenu() {
  const navigate = useNavigate();
  const practice = usePracticeSave();
  // PT-M7: the practice save pt-2008 (made once; afterwards it opens like any save)
  const openPractice = () =>
    practice.mutate('pt-2008', { onSettled: () => void navigate('/game/pt-2008') });
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
      <Button
        variant="default"
        onClick={openPractice}
        loading={practice.isPending}
        data-testid="practice-2008"
      >
        Practice: June 2008, before the crash
      </Button>
      <Button component={Link} to="/settings" variant="subtle">
        Settings
      </Button>
    </Stack>
  );
}
