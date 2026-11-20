/** Chart geometry only: values scaled into a 100 x 24 box (display, not game logic). */
export function sparkPoints(values: readonly number[]): string {
  const lo = Math.min(...values);
  const hi = Math.max(...values);
  const span = hi - lo || 1;
  const step = values.length > 1 ? 100 / (values.length - 1) : 0;
  return values
    .map((v, i) => `${(i * step).toFixed(1)},${(22 - ((v - lo) / span) * 20).toFixed(1)}`)
    .join(' ');
}
