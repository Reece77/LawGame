import { describe, expect, it } from 'vitest';
import { attributeTier, byStrength, rangeText, strainBand } from './attr';

describe('attribute display', () => {
  it('labels a range or a known value', () => {
    expect(rangeText({ lo: 14, hi: 17 })).toBe('14–17');
    expect(rangeText({ lo: 12, hi: 12 })).toBe('12');
  });
  it('colors by midpoint', () => {
    expect(attributeTier({ lo: 1, hi: 5 })).toBe(1);
    expect(attributeTier({ lo: 8, hi: 12 })).toBe(2);
    expect(attributeTier({ lo: 14, hi: 17 })).toBe(3);
    expect(attributeTier({ lo: 16, hi: 18 })).toBe(4);
  });
  it('bands strain', () => {
    expect(strainBand(20)).toBe('ok');
    expect(strainBand(65)).toBe('high');
    expect(strainBand(80)).toBe('burnout');
  });
  it('sorts strongest first', () => {
    const a = { label: 'a', lo: 10, hi: 12 };
    const b = { label: 'b', lo: 14, hi: 16 };
    expect([a, b].sort(byStrength)[0]).toBe(b);
  });
});
