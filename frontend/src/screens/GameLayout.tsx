import { AppShell, Button, Group, Modal, NavLink, Text } from '@mantine/core';
import { Link, Outlet, useParams } from 'react-router';
import { EventCard } from '../components/EventCard';
import { HolidayButton } from '../components/HolidayButton';
import { useAdvance, useEvent, useGame, useInbox } from '../lib/api';

export function GameLayout() {
  const { slug = '' } = useParams();
  const game = useGame(slug);
  const advance = useAdvance(slug);
  const inbox = useInbox(slug);
  const unread = (inbox.data ?? []).filter((i) => !i.read).length;
  const ended = game.data !== undefined && game.data.game_state !== 'active';
  // PT-M6: a critical event blocks Continue until it is answered (spec 15).
  const blockingId = game.data?.blocking_event_id ?? null;
  const blocking = useEvent(slug, blockingId);

  return (
    <AppShell header={{ height: 52 }} navbar={{ width: 200, breakpoint: 'sm' }} padding="md">
      <AppShell.Header>
        <Group h="100%" px="md" justify="space-between">
          <Text fw={600}>{game.data?.firm_name ?? 'Partner Track'}</Text>
          <Group>
            <Text data-testid="date">{game.data?.date_label ?? ''}</Text>
            <HolidayButton slug={slug} disabled={ended || !game.data || blockingId !== null} />
            <Button
              onClick={() => advance.mutate()}
              loading={advance.isPending}
              disabled={ended || !game.data || blockingId !== null}
              title={blockingId !== null ? 'Answer the critical decision first' : undefined}
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
        <NavLink component={Link} to={`/game/${slug}/matters`} label="Matters" />
        <NavLink component={Link} to={`/game/${slug}/clients`} label="Clients" />
        <NavLink component={Link} to={`/game/${slug}/practices`} label="Practices" />
        <NavLink component={Link} to={`/game/${slug}/recruitment`} label="Recruitment" />
        <NavLink component={Link} to={`/game/${slug}/org`} label="Org" />
        <NavLink component={Link} to={`/game/${slug}/automation`} label="Automation" />
        <NavLink component={Link} to={`/game/${slug}/technology`} label="Technology" />
        <NavLink component={Link} to={`/game/${slug}/finance`} label="Finance" />
        <NavLink component={Link} to={`/game/${slug}/market`} label="Market" />
        <NavLink component={Link} to={`/game/${slug}/rankings`} label="Rankings" />
        <NavLink component={Link} to={`/game/${slug}/press`} label="Press" />
        <NavLink component={Link} to={`/game/${slug}/partnership`} label="Partnership" />
        <NavLink component={Link} to={`/game/${slug}/history`} label="History" />
        <NavLink component={Link} to={`/game/${slug}/founder`} label="Founder" />
        <NavLink component={Link} to={`/game/${slug}/family`} label="Family" />
        <NavLink component={Link} to="/" label="Main menu" />
      </AppShell.Navbar>
      <AppShell.Main>
        <Outlet />
      </AppShell.Main>
      <Modal
        opened={blockingId !== null && blocking.data !== undefined}
        onClose={() => undefined}
        withCloseButton={false}
        closeOnClickOutside={false}
        closeOnEscape={false}
        size="lg"
        title="A critical decision waits"
        data-testid="critical-modal"
      >
        {blocking.data && <EventCard slug={slug} event={blocking.data} />}
      </Modal>
    </AppShell>
  );
}
