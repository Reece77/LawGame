import { Anchor, Stack, Table, Text, Title } from '@mantine/core';
import { Link } from 'react-router';
import { useSaves } from '../lib/api';

export function SavesScreen() {
  const saves = useSaves();
  return (
    <Stack maw={720} mx="auto" mt={80} gap="md">
      <Title order={2}>Saves</Title>
      {saves.data?.length === 0 && <Text c="dimmed">No saves yet.</Text>}
      <Table striped highlightOnHover>
        <Table.Thead>
          <Table.Tr>
            <Table.Th>Firm</Table.Th>
            <Table.Th>Date</Table.Th>
            <Table.Th>State</Table.Th>
          </Table.Tr>
        </Table.Thead>
        <Table.Tbody>
          {(saves.data ?? []).map((s) => (
            <Table.Tr key={s.slug}>
              <Table.Td>
                <Anchor component={Link} to={`/game/${s.slug}`}>
                  {s.firm_name}
                </Anchor>
              </Table.Td>
              <Table.Td>{s.date_label}</Table.Td>
              <Table.Td>{s.game_state.replace('_', ' ')}</Table.Td>
            </Table.Tr>
          ))}
        </Table.Tbody>
      </Table>
      <Anchor component={Link} to="/">
        Back
      </Anchor>
    </Stack>
  );
}
