import { expect, test } from '@playwright/test';
import { continueMonth } from './helpers';

// PT-M17: retire the founder at 65 with a successor elected, and play on as the successor.
// A test-only route (PTK_DEBUG_ROUTES=1) makes the founder turn 65 in the first month, so
// the test does not play fifteen years; the succession flow is the player's: choose a
// successor, see the predicted vote, confirm, and the partnership votes at month end.
test('retire the founder at 65 and play on as the successor', async ({ page }) => {
  test.setTimeout(180_000);
  const slug = 'succession-test';
  const made = await page.request.post('/api/saves', {
    data: { slug, firm_name: 'Succession Test LLP', seed: 5, scenario_id: 'group_lift' },
  });
  expect(made.ok()).toBeTruthy();
  const aged = await page.request.post(`/api/saves/${slug}/debug/founder-age`, {
    data: { years: 65, months: 0 },
  });
  expect(aged.ok()).toBeTruthy();
  const founder = (await aged.json()).name as string;

  await page.goto(`/game/${slug}`);
  await expect(page.getByTestId('date')).toHaveText('Jan 2005');
  await page.getByRole('link', { name: 'Founder' }).click();
  await expect(page.getByRole('heading', { name: 'Founder' })).toBeVisible();
  await expect(page.getByTestId('founder-name')).toContainText(founder);
  await expect(page.getByTestId('retirement-age')).toContainText('at 65');

  // the month the founder turns 65 ends: the agreement asks for a successor
  await continueMonth(page);
  await expect(page.getByTestId('date')).toHaveText('Feb 2005');
  await expect(page.getByTestId('succession-due')).toBeVisible();

  await page.getByRole('combobox', { name: 'Successor (an equity partner)' }).click();
  await page.getByRole('option').first().click();
  await expect(page.getByTestId('predicted-vote')).toContainText('Predicted vote');
  const label = await page
    .getByRole('combobox', { name: 'Successor (an equity partner)' })
    .inputValue();
  const successor = label.split(' (')[0];
  await page.getByTestId('hand-over').click();
  await page.getByTestId('confirm-hand-over').click();
  await expect(page.getByTestId('succession-open')).toBeVisible();

  await continueMonth(page);
  await expect(page.getByTestId('date')).toHaveText('Mar 2005');
  await expect(page.getByTestId('founder-name')).toContainText(successor);
  await expect(page.getByTestId('founder-name')).toContainText('Managing partner');
  await expect(page.getByTestId('played')).toContainText(founder);
  await expect(page.getByTestId('played')).toContainText('Retired');

  // play on as the successor
  await continueMonth(page);
  await expect(page.getByTestId('date')).toHaveText('Apr 2005');
  await expect(page.getByTestId('founder-name')).toContainText(successor);
  await page.getByRole('link', { name: 'Family' }).click();
  await expect(page.getByTestId('no-family')).toBeVisible();
});
