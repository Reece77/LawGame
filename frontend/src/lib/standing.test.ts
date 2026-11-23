import { describe, expect, it } from 'vitest';
import { bandHistoryText, bandText, claimProblem, signedDelta, toggleId } from './standing';

const ctx = { lawyers: 40, claimMonths: [6, 36] as [number, number], claimsOpen: 0, claimsMax: 3 };
const none = { kind: null, practice: null, target: null, months: null };

describe('rankings display', () => {
  it('shows a band or not ranked', () => {
    expect(bandText(2)).toBe('Band 2');
    expect(bandText(null)).toBe('Not ranked');
  });
  it('shows a band history oldest first', () => {
    expect(
      bandHistoryText([
        { year: 2005, band: 3 },
        { year: 2006, band: 2 },
      ]),
    ).toBe('2005 B3 · 2006 B2');
    expect(bandHistoryText([])).toBe('—');
  });
  it('signs a delta', () => {
    expect(signedDelta(1.24)).toBe('+1.2');
    expect(signedDelta(-0.5)).toBe('−0.5');
    expect(signedDelta(0)).toBe('0.0');
  });
  it('caps a checkbox selection', () => {
    expect(toggleId([1, 2], 3, 3)).toEqual([1, 2, 3]);
    expect(toggleId([1, 2, 3], 4, 3)).toEqual([1, 2, 3]);
    expect(toggleId([1, 2, 3], 2, 3)).toEqual([1, 3]);
  });
});

describe('press claim form', () => {
  it('needs nothing without a claim', () => {
    expect(claimProblem(none, 'deflect', ctx)).toBeNull();
  });
  it('needs a bold or measured tone', () => {
    expect(claimProblem({ ...none, kind: 'no_layoffs' }, 'deflect', ctx)).toMatch(/bold/);
    expect(claimProblem({ ...none, kind: 'no_layoffs' }, 'measured', ctx)).toBeNull();
  });
  it('checks a headcount target and its months', () => {
    const d = { ...none, kind: 'headcount', target: 40, months: 12 };
    expect(claimProblem(d, 'bold', ctx)).toMatch(/above/);
    expect(claimProblem({ ...d, target: 60, months: 3 }, 'bold', ctx)).toMatch(/Months/);
    expect(claimProblem({ ...d, target: 60 }, 'bold', ctx)).toBeNull();
  });
  it('checks a band claim', () => {
    const d = { ...none, kind: 'band', target: 2, months: 12 };
    expect(claimProblem(d, 'bold', ctx)).toMatch(/practice/);
    expect(claimProblem({ ...d, practice: 'ma', target: 7 }, 'bold', ctx)).toMatch(/1-6/);
    expect(claimProblem({ ...d, practice: 'ma' }, 'bold', ctx)).toBeNull();
  });
  it('respects the open-claims cap', () => {
    expect(
      claimProblem({ ...none, kind: 'match_scale' }, 'bold', { ...ctx, claimsOpen: 3 }),
    ).toMatch(/At most/);
  });
});
