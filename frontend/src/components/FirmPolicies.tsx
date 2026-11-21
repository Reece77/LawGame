import { Alert, Button, Group, NumberInput, Stack, Switch, Text } from '@mantine/core';
import { useState } from 'react';
import { formatBpPercent, formatWhole } from '../lib/format';
import { useFirmPolicies, usePolicyAction, type FirmPolicies as Policies } from '../lib/api';

// PT-M7a: the firm's policies on the Org screen: the pro bono credit (spec 7.8) and each
// January's rate rise. The engine owns every rule and number; this only sends the choice.
export function FirmPolicies({ slug }: { slug: string }) {
  const policies = useFirmPolicies(slug);
  const p = policies.data;
  if (!p) return <Text c="dimmed">Loading…</Text>;
  // the form restarts from the engine's values whenever they change
  const key = `${p.pro_bono_credit_hours}/${p.rate_rise_bp ?? 'market'}`;
  return <PolicyForm key={key} slug={slug} p={p} />;
}

function PolicyForm({ slug, p }: { slug: string; p: Policies }) {
  const action = usePolicyAction(slug);
  const [credit, setCredit] = useState<number | string>(p.pro_bono_credit_hours);
  const [rise, setRise] = useState<number | string>((p.rate_rise_bp ?? p.market_rise_bp) / 100);
  const [market, setMarket] = useState(p.rate_rise_bp === null);
  return (
    <div className="tst-panel" data-testid="firm-policies">
      <h3 className="tst-ptitle">Firm policies</h3>
      {action.error && (
        <Alert color="red" withCloseButton onClose={() => action.reset()}>
          {action.error.message}
        </Alert>
      )}
      <Stack gap="sm">
        <Group align="end">
          <NumberInput
            label="Pro bono hours credited a year"
            min={0}
            max={p.pro_bono_credit_max_hours}
            value={credit}
            onChange={setCredit}
            data-testid="pro-bono-credit"
            w={220}
          />
          <Button
            size="xs"
            loading={action.isPending}
            onClick={() => action.mutate({ kind: 'pro_bono', hours: Number(credit) })}
            data-testid="pro-bono-save"
          >
            Set
          </Button>
        </Group>
        <Text size="sm" c="dimmed" data-testid="pro-bono-current">
          Credit {formatWhole(p.pro_bono_credit_hours)} h a year; the firm does about{' '}
          {formatWhole(p.pro_bono_hours_per_lawyer)} h a lawyer a year.
        </Text>
        <Group align="end">
          <Switch
            label="Follow the market's rise"
            checked={market}
            onChange={(e) => setMarket(e.currentTarget.checked)}
            data-testid="rate-market"
          />
          <NumberInput
            label="January rate rise, %"
            min={p.rate_rise_min_bp / 100}
            max={p.rate_rise_max_bp / 100}
            step={0.5}
            decimalScale={1}
            disabled={market}
            value={rise}
            onChange={setRise}
            data-testid="rate-rise"
            w={180}
          />
          <Button
            size="xs"
            loading={action.isPending}
            onClick={() =>
              action.mutate({
                kind: 'rates',
                riseBp: market ? null : Math.round(Number(rise) * 100),
              })
            }
            data-testid="rate-save"
          >
            Set
          </Button>
        </Group>
        <Text size="sm" c="dimmed" data-testid="rate-current">
          {p.rate_rise_bp === null
            ? `Following the market (${formatBpPercent(p.market_rise_bp)} a year).`
            : `${formatBpPercent(p.rate_rise_bp)} each January (market ${formatBpPercent(p.market_rise_bp)}).`}{' '}
          Card {formatBpPercent(p.rate_index_bp)} of 2005's; market{' '}
          {formatBpPercent(p.market_index_bp)}.
        </Text>
      </Stack>
    </div>
  );
}
