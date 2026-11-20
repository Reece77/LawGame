// Ported from TST frontend/src/lib/explain.ts @ 02fba2aa; changed: Partner Track's units
// (hours, ratio, a revealed range, text) and no signed form.
import type { Schemas } from '../api/client';
import { rangeText } from './attr';
import { formatHours, formatMoneyWhole } from './format';

type Item = Schemas['ExplainItemOut'];
type Unit = Item['unit'];

/** A number as the API sent it, in its unit; display only. */
export function formatUnit(value: number, unit: Unit): string {
  switch (unit) {
    case 'cents':
      return formatMoneyWhole(Math.round(value));
    case 'percent':
      return `${value.toFixed(1)}%`;
    case 'hours':
      return formatHours(value);
    case 'ratio':
      return `${value.toFixed(2)}×`;
    default:
      return String(value);
  }
}

/** One Explain item's value: its amount, range or text. */
export function itemText(item: Item): string {
  if (item.range) return rangeText(item.range);
  if (item.amount !== null && item.amount !== undefined) return formatUnit(item.amount, item.unit);
  return item.text ?? '—';
}
