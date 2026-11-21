import { expect, test } from '@playwright/test';

test('found a firm, see its people, open a profile', async ({ page }) => {
  await page.goto('/new');
  await page.getByLabel('Firm name').fill('People Test LLP');
  await page.getByRole('button', { name: 'Found the firm' }).click();
  await expect(page.getByTestId('date')).toHaveText('Jan 2005');
  await page.getByRole('link', { name: 'People' }).click();
  const table = page.getByTestId('people-table');
  await expect(table.locator('tbody tr')).toHaveCount(4);
  await expect(table).toContainText('Equity partner');
  await expect(table).toContainText('Associate 4'); // PT-M7a: the spin-out's fourth-year
  await page.getByRole('button', { name: 'Continue' }).click();
  await expect(page.getByTestId('date')).toHaveText('Feb 2005');
  await table.locator('tbody tr').first().getByRole('link').click();
  await expect(page.getByTestId('person-name')).toBeVisible();
  await expect(page.getByTestId('familiarity-grid').locator('tr')).toHaveCount(10);
  await expect(page.getByTestId('strain').first()).toBeVisible();
  await expect(page.getByTestId('potential')).not.toBeEmpty();
  await expect(page.getByText('Book of business')).toBeVisible();
});
