import { expect, test } from '@playwright/test';

// PT-M1b: hire a first-year class through the campus cycle (spec 5.7). Register in January,
// the summer associates arrive in May, offers go out in August, the class starts the
// September after, on that year's scale.
test('hire a first-year class through the campus cycle', async ({ page }) => {
  test.setTimeout(120_000);
  await page.goto('/new');
  await page.getByLabel('Firm name').fill('Campus Test LLP');
  await page.getByRole('button', { name: 'Found the firm' }).click();
  await expect(page.getByTestId('date')).toHaveText('Jan 2005');
  await expect(page.getByTestId('payroll-total')).toBeVisible();

  await page.getByRole('link', { name: 'Recruitment' }).click();
  await expect(page.getByTestId('campus-status')).toContainText('Registration is open');
  await page.getByRole('button', { name: 'Open search' }).click();
  await expect(page.getByTestId('campus-panel')).toContainText('Registered: Corporate and M&A');
  await expect(page.getByTestId('energy')).toHaveText('Energy 55 / 60');

  const cont = page.getByRole('button', { name: 'Continue' });
  const date = page.getByTestId('date');
  for (const month of ['Feb', 'Mar', 'Apr', 'May']) {
    await cont.click();
    await expect(date).toHaveText(`${month} 2005`);
  }
  await expect(page.getByTestId('campus-status')).toContainText('summer programme is running');
  const rows = page.getByTestId('candidate-row');
  await expect(rows).toHaveCount(11);
  await expect(rows.first().getByRole('button', { name: 'Make offer' })).toBeDisabled();

  for (const month of ['Jun', 'Jul', 'Aug']) {
    await cont.click();
    await expect(date).toHaveText(`${month} 2005`);
  }
  await expect(page.getByTestId('campus-status')).toContainText('Offer month');
  // Interview and offer to the first five summer associates, at 1.3x their ask.
  for (let i = 0; i < 5; i++) {
    const row = rows.nth(i);
    await row.getByRole('button', { name: 'Interview' }).click();
    await expect(row.getByRole('button', { name: 'Make offer' })).toBeEnabled();
    await row.getByRole('button', { name: 'Make offer' }).click();
    const salary = page.getByLabel('Salary (dollars a year)');
    const ask = Number((await salary.inputValue()).replace(/,/g, ''));
    await salary.fill(String(Math.round(ask * 1.3)));
    await expect(page.getByTestId('offer-hint')).toBeVisible();
    await page.getByRole('button', { name: 'Send offer' }).click();
    await expect(row.getByText('Offer pending')).toBeVisible();
  }
  await expect(page.getByTestId('offers-table').locator('tr')).toHaveCount(5);

  await cont.click();
  await expect(date).toHaveText('Sep 2005');
  await expect(page.getByTestId('signed').first()).toContainText('starts Sep 2006');
  const signed = await page.getByTestId('signed').count();
  expect(signed).toBeGreaterThan(0);
  await page.getByRole('link', { name: /Inbox/ }).click();
  await expect(page.getByTestId('inbox-item').first()).toBeVisible();
  await expect(page.getByText(/accepted a place in the class of 2006/).first()).toBeVisible();

  // On to September 2006: the class starts on the 2006 scale ($145,000).
  for (const label of [
    'Oct 2005',
    'Nov 2005',
    'Dec 2005',
    'Jan 2006',
    'Feb 2006',
    'Mar 2006',
    'Apr 2006',
    'May 2006',
    'Jun 2006',
    'Jul 2006',
    'Aug 2006',
    'Sep 2006',
    'Oct 2006',
  ]) {
    await cont.click();
    await expect(date).toHaveText(label);
  }
  await expect(page.getByText(/starts today/).first()).toBeVisible();
  await page.getByRole('link', { name: 'People' }).click();
  const people = page.getByTestId('people-table');
  // The class is on the books as first-years (one may have resigned already: the market).
  await expect(people).toContainText('Associate 1');
  await expect(people).toContainText('Equity partner');
});
