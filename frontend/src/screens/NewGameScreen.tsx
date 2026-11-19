import { Alert, Button, Select, Stack, TextInput, Title } from '@mantine/core';
import { useState } from 'react';
import { useNavigate } from 'react-router';
import { useMeta, useNewGame } from '../lib/api';

function slugify(name: string): string {
  return name
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
    .slice(0, 63);
}

export function NewGameScreen() {
  const meta = useMeta();
  const create = useNewGame();
  const navigate = useNavigate();
  const [firmName, setFirmName] = useState('Founders LLP');
  const [scenario, setScenario] = useState<string | null>('biglaw_spinout');
  const [difficulty, setDifficulty] = useState<string | null>('standard');
  const [background, setBackground] = useState<string | null>(null); // null: the scenario's
  const slug = slugify(firmName) || 'firm';

  const start = () =>
    create.mutate(
      {
        slug,
        firm_name: firmName,
        scenario_id: scenario ?? undefined,
        difficulty: difficulty ?? undefined,
        background: background ?? undefined,
      },
      { onSuccess: (game) => navigate(`/game/${game.slug}`) },
    );

  return (
    <Stack maw={480} mx="auto" mt={80} gap="md">
      <Title order={2}>New game</Title>
      <TextInput
        label="Firm name"
        value={firmName}
        onChange={(e) => setFirmName(e.currentTarget.value)}
      />
      <Select
        label="Scenario"
        data={(meta.data?.scenarios ?? []).map((s) => ({ value: s.id, label: s.name }))}
        value={scenario}
        onChange={setScenario}
      />
      <Select
        label="Difficulty"
        data={(meta.data?.difficulties ?? []).map((d) => ({ value: d.id, label: d.name }))}
        value={difficulty}
        onChange={setDifficulty}
      />
      <Select
        label="Your background"
        placeholder="The scenario's founding partner"
        clearable
        data={(meta.data?.backgrounds ?? []).map((b) => ({ value: b.key, label: b.label }))}
        value={background}
        onChange={setBackground}
        description={meta.data?.backgrounds.find((b) => b.key === background)?.description}
      />
      {create.error && <Alert color="warn">{create.error.message}</Alert>}
      <Button onClick={start} loading={create.isPending} disabled={!firmName.trim()}>
        Found the firm
      </Button>
    </Stack>
  );
}
