import { expect, test } from '@playwright/test';

// PT-M7a: the Org screen's firm policies (pro bono credit, the yearly rate rise), the People
// screen's Pro bono column, and a Holiday from the header that stops with a reason.
test('set the firm policies and take a holiday', async ({ page }) => {
  test.setTimeout(120_000);
  const made = await page.request.post('/api/saves', {
    data: { slug: 'holiday-test', firm_name: 'Holiday Test LLP', seed: 5 },
  });
  expect(made.ok()).toBeTruthy();

  await page.goto('/game/holiday-test/org');
  const policies = page.getByTestId('firm-policies');
  await expect(policies).toBeVisible();
  await expect(page.getByTestId('pro-bono-current')).toContainText('Credit 50 h');
  await page.getByTestId('pro-bono-credit').fill('80');
  await page.getByTestId('pro-bono-save').click();
  await expect(page.getByTestId('pro-bono-current')).toContainText('Credit 80 h');
  await expect(page.getByTestId('rate-current')).toContainText('Following the market');
  await page.getByTestId('rate-market').click();
  await page.getByTestId('rate-rise').fill('5');
  await page.getByTestId('rate-save').click();
  await expect(page.getByTestId('rate-current')).toContainText('5.00% each January');

  await page.getByRole('link', { name: 'People' }).click();
  await expect(page.getByRole('columnheader', { name: 'Pro bono' })).toBeVisible();

  await expect(page.getByTestId('date')).toHaveText('Jan 2005');
  await page.getByTestId('holiday-open').click();
  await page.getByTestId('holiday-months').fill('3');
  await page.getByTestId('holiday-go').click();
  const result = page.getByTestId('holiday-result');
  await expect(result).toContainText('Stopped because');
  await page.keyboard.press('Escape');
  await expect(page.getByTestId('date')).not.toHaveText('Jan 2005');
});
