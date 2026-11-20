import { expect, test } from '@playwright/test';
import { continueMonth } from './helpers.js';

// PT-M6: events arrive in the inbox, written by the mock adapter (the e2e API runs with
// PTK_LLM_ADAPTER=mock); one is answered on its card; the settings show the budget meter and
// offline mode. Seed 7 has two open events in April 2005 (a month may bring none).
test('answer an event in the inbox and see the story budget', async ({ page }) => {
  test.setTimeout(120_000);
  const made = await page.request.post('/api/saves', {
    data: { slug: 'events-test', firm_name: 'Events Test LLP', seed: 7 },
  });
  expect(made.ok()).toBeTruthy();
  await page.goto('/game/events-test');
  await expect(page.getByTestId('date')).toHaveText('Jan 2005');

  const date = page.getByTestId('date');
  for (const month of ['Feb', 'Mar', 'Apr']) {
    await continueMonth(page);
    await expect(date).toHaveText(`${month} 2005`);
  }
  await expect(page.getByTestId('legal-news')).toBeVisible();
  await page.getByRole('link', { name: /Inbox/ }).click();
  const cards = page.getByTestId('event-card');
  await expect(cards.first()).toBeVisible();
  await expect(cards.first()).toContainText('[mock]');

  // Answer the first open event with its second choice.
  const open = cards.filter({ has: page.getByRole('button', { name: 'Choose B' }) }).first();
  const id = await open.getAttribute('data-event-id');
  await open.getByRole('button', { name: 'Choose B' }).click();
  const answered = page.locator(`[data-event-id="${id}"]`);
  await expect(answered.getByText('(chosen)')).toBeVisible();
  await expect(answered.getByRole('button', { name: 'Choose A' })).toHaveCount(0);

  await page.goto('/settings');
  await expect(page.getByTestId('budget-meter')).toContainText('$10.00');
  await expect(page.getByTestId('writer-in-use')).toContainText('mock');
  await page.getByTestId('offline-switch').click();
  await expect(page.getByTestId('offline-switch')).toBeChecked();
});
