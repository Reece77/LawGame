import { describe, expect, it } from 'vitest';
import { formatMoney } from './format';

describe('formatMoney', () => {
  it('formats integer cents', () => {
    expect(formatMoney(60_000_000)).toBe('$600,000.00');
    expect(formatMoney(-150)).toBe('-$1.50');
  });
  it('refuses non-integers', () => {
    expect(() => formatMoney(1.5)).toThrow(RangeError);
  });
});
