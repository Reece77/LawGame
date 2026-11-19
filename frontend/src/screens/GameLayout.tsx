import { AppShell, Button, Group, NavLink, Text } from '@mantine/core';
import { Link, Outlet, useParams } from 'react-router';
import { useAdvance, useGame, useInbox } from '../lib/api';

export function GameLayout() {
  const { slug = '' } = useParams();
  const game = useGame(slug);
  const advance = useAdvance(slug);
  const inbox = useInbox(slug);
  const unread = (inbox.data ?? []).filter((i) => !i.read).length;
  const ended = game.data !== undefined && game.data.game_state !== 'active';

  return (
    <AppShell header={{ height: 52 }} navbar={{ width: 200, breakpoint: 'sm' }} padding="md">
      <AppShell.Header>
        <Group h="100%" px="md" justify="space-between">
          <Text fw={600}>{game.data?.firm_name ?? 'Partner Track'}</Text>
          <Group>
            <Text data-testid="date">{game.data?.date_label ?? ''}</Text>
            <Button
              onClick={() => advance.mutate()}
              loading={advance.isPending}
              disabled={ended || !game.data}
            >
              {ended ? 'Campaign over' : 'Continue'}
            </Button>
          </Group>
        </Group>
      </AppShell.Header>
      <AppShell.Navbar p="xs">
        <NavLink component={Link} to={`/game/${slug}`} label="Overview" />
        <NavLink
          component={Link}
          to={`/game/${slug}/inbox`}
          label={unread ? `Inbox (${unread})` : 'Inbox'}
        />
        <NavLink component={Link} to={`/game/${slug}/people`} label="People" />
        <NavLink component={Link} to={`/game/${slug}/recruitment`} label="Recruitment" />
        <NavLink component={Link} to={`/game/${slug}/org`} label="Org" />
        <NavLink component={Link} to="/" label="Main menu" />
      </AppShell.Navbar>
      <AppShell.Main>
        <Outlet />
      </AppShell.Main>
    </AppShell>
  );
}
