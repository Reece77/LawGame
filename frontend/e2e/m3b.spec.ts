import { expect, test } from '@playwright/test';

test('bills go out and the Finance screen shows the revenue chain', async ({ page }) => {
  await page.goto('/new');
  await page.getByLabel('Firm name').fill('Billing Test LLP');
  await page.getByRole('button', { name: 'Found the firm' }).click();
  await expect(page.getByTestId('date')).toHaveText('Jan 2005');

  // Three months: hours post to WIP, bills issue, the first clients pay.
  for (const month of ['Feb 2005', 'Mar 2005', 'Apr 2005']) {
    await page.getByRole('button', { name: 'Continue' }).click();
    await expect(page.getByTestId('date')).toHaveText(month);
  }

  await page.getByRole('link', { name: 'Finance' }).click();
  await expect(page.getByRole('heading', { name: 'Finance' })).toBeVisible();
  await expect(page.getByTestId('kpi-realisation')).toHaveText(/%$/);
  await expect(page.getByTestId('kpi-revenue')).toHaveText(/^\$/);
  await expect(page.getByTestId('pnl-accrual').first()).toContainText('Fees');
  await page.getByText('Cash', { exact: true }).click();
  await expect(page.getByTestId('pnl-cash').first()).toContainText('Collections');
  await expect(page.getByTestId('ar-ageing')).toContainText('0-30 days');
  await expect(page.getByTestId('bills')).toContainText('Open bills');
});
