import { expect, test } from '@playwright/test';
import { advanceMonths } from './helpers.js';

// PT-M16: a March submission and an October band. A new firm plays to March 2006 (turn 0 is
// January 2005), makes the directory submission on the Rankings screen (a matter and a
// referee), plays on through October 2006, and finds the year's bands with its band history.
// The Press screen shows the firm's credibility.
test('a March submission and an October band', async ({ page }) => {
  test.setTimeout(240_000);
  const slug = 'standing-test';
  const made = await page.request.post('/api/saves', {
    data: { slug, firm_name: 'Standing Test LLP', seed: 5 },
  });
  expect(made.ok()).toBeTruthy();
  await advanceMonths(page, slug, 14);

  await page.goto(`/game/${slug}/rankings`);
  await expect(page.getByTestId('date')).toHaveText('Mar 2006');
  await expect(page.getByTestId('rankings-screen')).toBeVisible();
  await page.getByTestId('tab-submission').click();
  const form = page.getByTestId('submission-form');
  await expect(form).toBeVisible();
  await form
    .getByRole('checkbox', { name: /^Showcase / })
    .first()
    .check();
  await form
    .getByRole('checkbox', { name: /as a referee$/ })
    .first()
    .check();
  await page.getByTestId('submission-submit').click();
  await expect(page.getByTestId('submission-made')).toContainText('strength');
  await expect(page.getByTestId('submission-made')).toContainText('1 matters with 1 referees');

  // March's month end through October's: the directory publishes its 2006 bands
  await advanceMonths(page, slug, 8);
  await page.goto(`/game/${slug}/rankings`);
  await expect(page.getByTestId('date')).toHaveText('Nov 2006');
  await page.getByTestId('tab-bands').click();
  await expect(page.getByTestId('bands-year')).toContainText('2006');
  const rows = page.getByTestId('bands-table').getByTestId('band-row');
  await expect(rows.first()).toBeVisible();
  await expect(
    page.getByTestId('band-history').filter({ hasText: '2006 B' }).first(),
  ).toBeVisible();

  await page.getByRole('link', { name: 'Press' }).click();
  await expect(page.getByTestId('press-screen')).toBeVisible();
  await expect(page.getByTestId('credibility')).toContainText('/ 100');
  await expect(page.getByTestId('claims-table')).toBeVisible();
});
