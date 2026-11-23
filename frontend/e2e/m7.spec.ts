import { expect, test } from '@playwright/test';
import { advanceMonths, answerBlocking } from './helpers.js';

// PT-M7: the Overview's What next and Getting started (the guided first year: a step ticks
// from state, the checklist dismisses), and the History screen's years and timeline.
test('the guided first year and the firm history', async ({ page }) => {
  test.setTimeout(180_000);
  const made = await page.request.post('/api/saves', {
    data: { slug: 'history-test', firm_name: 'History Test LLP', seed: 5 },
  });
  expect(made.ok()).toBeTruthy();

  await page.goto('/game/history-test');
  await expect(page.getByTestId('what-next')).toBeVisible();
  const checklist = page.getByTestId('getting-started');
  await expect(checklist).toBeVisible();
  await expect(page.getByTestId('step-policy')).not.toBeChecked();

  // set a policy on Org; the step ticks
  await page.goto('/game/history-test/org');
  await page.getByTestId('rate-market').click();
  await page.getByTestId('rate-rise').fill('4');
  await page.getByTestId('rate-save').click();
  await expect(page.getByTestId('rate-current')).toContainText('4.00% each January');
  await page.getByRole('link', { name: 'Overview' }).click();
  await expect(page.getByTestId('step-policy')).toBeChecked();

  // a year played, then the History screen ranks the firm's first year
  await advanceMonths(page, 'history-test', 13);
  await page.getByRole('link', { name: 'History' }).click();
  await expect(page.getByRole('heading', { name: 'History' })).toBeVisible();
  await expect(page.getByTestId('history-year').first()).toBeVisible();
  await expect(page.getByTestId('history-rank').first()).toContainText(' of ');
  await page.getByRole('tab', { name: 'Timeline' }).click();
  await expect(page.getByTestId('history-line').first()).toBeVisible();

  // the checklist dismisses
  await page.getByRole('link', { name: 'Overview' }).click();
  await page.getByTestId('getting-started').getByRole('button', { name: 'Dismiss' }).click();
  await expect(page.getByTestId('getting-started')).toHaveCount(0);
});

// PT-M7: the practice save opens from the Main menu in June 2008.
test('the practice save opens in June 2008', async ({ page }) => {
  test.setTimeout(120_000);
  await page.goto('/');
  await page.getByTestId('practice-2008').click();
  await expect(page.getByTestId('date')).toHaveText('Jun 2008', { timeout: 60_000 });
  await answerBlocking(page, 'pt-2008'); // PT-M16: a critical event may be waiting
  await page.reload();
  await page.getByRole('link', { name: 'People' }).click();
  await expect(page.getByRole('heading', { name: 'People' })).toBeVisible();
});
