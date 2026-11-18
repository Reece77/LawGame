import { expect, test } from '@playwright/test';

test('found a firm, press Continue, reload the save', async ({ page }) => {
  await page.goto('/');
  await page.getByRole('link', { name: 'New game' }).click();
  await page.getByLabel('Firm name').fill('Smoke Test LLP');
  await page.getByRole('button', { name: 'Found the firm' }).click();
  await expect(page.getByTestId('date')).toHaveText('Jan 2005');
  await expect(page.getByTestId('cash')).toHaveText('$600,000.00');
  await page.getByRole('button', { name: 'Continue' }).click();
  await expect(page.getByTestId('date')).toHaveText('Feb 2005');
  await page.reload();
  await expect(page.getByTestId('date')).toHaveText('Feb 2005');
  await page.goto('/saves');
  await expect(page.getByRole('link', { name: 'Smoke Test LLP' })).toBeVisible();
});
