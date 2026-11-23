import { expect, test } from '@playwright/test';
import { continueMonth } from './helpers.js';

// PT-M5: the Market screen lists the real rivals at their 2005 size; a rival's page shows
// its key people (real notables among them); approaching them makes them the firm's
// candidates; a month on, the market has news.
test('see the rivals, open a rival, approach its people, read the news', async ({ page }) => {
  const made = await page.request.post('/api/saves', {
    data: { slug: 'm5', firm_name: 'Rivals LLP', seed: 5 },
  });
  expect(made.ok()).toBeTruthy();
  await page.goto('/game/m5');
  await expect(page.getByTestId('date')).toHaveText('Jan 2005');

  await page.getByRole('link', { name: 'Market', exact: true }).click();
  const skadden = page.getByTestId('rival-link').filter({ hasText: 'Skadden' });
  await expect(skadden).toBeVisible();
  // PT-M11: Clifford Chance (FY2004/05, $1.7B) now heads the table; Skadden keeps its 2005 size
  await expect(page.getByTestId('rival-row').filter({ hasText: 'Skadden' }).first()).toContainText(
    '$1.6B',
  );

  await skadden.click();
  await expect(page.getByTestId('rival-name')).toContainText('Skadden');
  await expect(page.getByTestId('key-person').first()).toBeVisible();
  await expect(page.getByText('Joseph H. Flom')).toBeVisible();

  await page.getByTestId('approach-rival').click();
  await expect(page.getByTestId('approach-done')).toBeVisible();
  // Approached partners are lateral partner candidates (PT-M7a: the old check matched the
  // rival page before the Recruitment screen loaded, where they never were).
  await page.getByRole('link', { name: 'Partnership screen' }).click();
  await expect(page.getByRole('heading', { name: 'Partnership', level: 2 })).toBeVisible();
  await expect(page.getByTestId('laterals')).toContainText('Robert C. Sheehan');

  await continueMonth(page);
  await expect(page.getByTestId('date')).toHaveText('Feb 2005');
  await page.getByRole('link', { name: 'Market', exact: true }).click();
  await expect(page.getByTestId('market-news')).toBeVisible();
});
