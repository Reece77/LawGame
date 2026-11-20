import { afterEach, describe, expect, it } from 'vitest';
import { readAll, STORAGE_KEY, writeTable, sortSummary } from '../hooks/useTableViews';
import { formatUnit, itemText } from './explain';
import { formatBpShort, formatHours } from './format';
import { sparkPoints } from './spark';

class MemoryStorage {
  data = new Map<string, string>();
  getItem(k: string) {
    return this.data.get(k) ?? null;
  }
  setItem(k: string, v: string) {
    this.data.set(k, v);
  }
}

describe('saved table views in localStorage', () => {
  afterEach(() => {
    Reflect.deleteProperty(globalThis, 'localStorage');
  });
  it('round-trips a table and keeps the others', () => {
    const store = new MemoryStorage();
    Object.defineProperty(globalThis, 'localStorage', { value: store, configurable: true });
    writeTable('matters', {
      views: [{ name: 'Big', sort: [{ id: 'wip', desc: true }] }],
      current: 'Big',
    });
    writeTable('clients', { views: [], current: 'Default' });
    const all = readAll();
    expect(all.matters.current).toBe('Big');
    expect(all.clients.current).toBe('Default');
    expect(sortSummary((all.matters.views ?? [])[0], (id) => id.toUpperCase())).toBe('WIP ↓');
  });
  it('treats unreadable storage as empty', () => {
    const store = new MemoryStorage();
    store.setItem(STORAGE_KEY, '{not json');
    Object.defineProperty(globalThis, 'localStorage', { value: store, configurable: true });
    expect(readAll()).toEqual({});
  });
});

describe('explain and screen formatting', () => {
  it('formats each unit as sent', () => {
    expect(formatUnit(7015000, 'cents')).toBe('$70,150');
    expect(formatUnit(66, 'percent')).toBe('66.0%');
    expect(formatUnit(122.5, 'hours')).toBe('122.5 h');
    expect(formatUnit(3, 'ratio')).toBe('3.00×');
  });
  it('shows a range, an amount or the text', () => {
    expect(itemText({ label: 'a', amount: null, unit: 'range', range: { lo: 8, hi: 14 } })).toBe(
      '8–14',
    );
    expect(itemText({ label: 'b', amount: 1118, unit: 'hours' })).toBe('1,118 h');
    expect(itemText({ label: 'c', amount: null, unit: 'text', text: 'Unknown' })).toBe('Unknown');
  });
  it('formats hours and basis points', () => {
    expect(formatHours(1499.9)).toBe('1,499.9 h');
    expect(formatHours(0)).toBe('0 h');
    expect(formatBpShort(7685)).toBe('76.8%');
  });
  it('scales a sparkline into its box', () => {
    expect(sparkPoints([1, 2, 3])).toBe('0.0,22.0 50.0,12.0 100.0,2.0');
    expect(sparkPoints([5, 5])).toBe('0.0,22.0 100.0,22.0');
  });
});
