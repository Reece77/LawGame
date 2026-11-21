import {
  Alert,
  Button,
  Group,
  Modal,
  NumberInput,
  SegmentedControl,
  Stack,
  Text,
} from '@mantine/core';
import { useState } from 'react';
import { useHoliday, type HolidayResult } from '../lib/api';

// PT-M7a (spec 4.2): Holiday for some months, or continue until a month. The engine plays one
// Continue a month and stops for what needs the player; this shows why it stopped.
export function HolidayButton({ slug, disabled }: { slug: string; disabled: boolean }) {
  const holiday = useHoliday(slug);
  const [opened, setOpened] = useState(false);
  const [mode, setMode] = useState<'months' | 'until'>('months');
  const [months, setMonths] = useState<number | string>(6);
  const [year, setYear] = useState<number | string>('');
  const [month, setMonth] = useState<number | string>(12);
  const [result, setResult] = useState<HolidayResult | null>(null);
  const go = () =>
    holiday.mutate(
      mode === 'months'
        ? { months: Number(months) }
        : { until_year: Number(year), until_month: Number(month) },
      { onSuccess: (r) => setResult(r) },
    );
  return (
    <>
      <Button
        variant="default"
        disabled={disabled}
        onClick={() => {
          setResult(null);
          holiday.reset();
          setOpened(true);
        }}
        data-testid="holiday-open"
      >
        Holiday
      </Button>
      <Modal opened={opened} onClose={() => setOpened(false)} title="Holiday" size="md">
        <Stack gap="sm">
          <SegmentedControl
            value={mode}
            onChange={(v) => setMode(v as 'months' | 'until')}
            data={[
              { value: 'months', label: 'For some months' },
              { value: 'until', label: 'Continue until' },
            ]}
          />
          {mode === 'months' ? (
            <NumberInput
              label="Months"
              min={1}
              value={months}
              onChange={setMonths}
              data-testid="holiday-months"
            />
          ) : (
            <Group grow>
              <NumberInput
                label="Year"
                value={year}
                onChange={setYear}
                data-testid="holiday-year"
              />
              <NumberInput
                label="Month"
                min={1}
                max={12}
                value={month}
                onChange={setMonth}
                data-testid="holiday-month"
              />
            </Group>
          )}
          <Text size="xs" c="dimmed">
            Stops for critical decisions, December votes, settlement offers and approaches to your
            partners.
          </Text>
          {holiday.error && <Alert color="red">{holiday.error.message}</Alert>}
          {result && (
            <Alert color="blue" data-testid="holiday-result">
              {result.months_played} month{result.months_played === 1 ? '' : 's'},{' '}
              {result.from_label} to {result.to_label}. Stopped because {result.reason_text}.
            </Alert>
          )}
          <Group justify="end">
            <Button onClick={go} loading={holiday.isPending} data-testid="holiday-go">
              Go
            </Button>
          </Group>
        </Stack>
      </Modal>
    </>
  );
}
