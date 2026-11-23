import { expect, test } from '@playwright/test';
import { advanceMonths, answerBlocking } from './helpers.js';

// PT-M11: open a London office with a team lift and qualify a trainee. A new firm opens London
// on the Offices screen in January 2005 (a partner and two associates lifted from Clifford
// Chance into a five-seat lease: a new firm's capital pays for no more), offers training contracts there (they join in
// September 2007), and plays on until September 2009, when the trainees qualify as solicitors.
test('open a London office with a team lift and qualify a trainee', async ({ page }) => {
  test.setTimeout(600_000);
  const slug = 'offices-test';
  const made = await page.request.post('/api/saves', {
    data: { slug, firm_name: 'Offices Test LLP', seed: 1 },
  });
  expect(made.ok()).toBeTruthy();
  await answerBlocking(page, slug);

  await page.goto(`/game/${slug}/offices`);
  await expect(page.getByTestId('offices-screen')).toBeVisible();
  const form = page.getByTestId('open-office');
  await form.getByTestId('open-city').click();
  await page.getByRole('option', { name: 'London' }).click();
  await form.getByTestId('open-seats').click();
  await page.getByRole('option', { name: '5', exact: true }).click();
  await form.getByTestId('open-practice').click();
  await page
    .getByRole('option', { name: /Corporate/ })
    .first()
    .click();
  await form.getByTestId('open-rival').click();
  await page.getByRole('option', { name: 'Clifford Chance' }).click();
  await form.getByLabel('Partners').fill('1');
  await form.getByLabel('Associates').fill('2');
  await page.getByTestId('open-submit').click();
  const rows = page.getByTestId('offices-table').getByTestId('office-row');
  await expect(rows.filter({ hasText: 'London' })).toBeVisible();
  await expect(rows.filter({ hasText: 'Team lift' })).toBeVisible();
  await expect(page.getByTestId('rules-ew')).toContainText('Solicitors Regulation Authority');

  await page
    .getByTestId('office-actions')
    .getByRole('button', { name: /Offer training/ })
    .click();
  await expect(page.getByTestId('uk-path')).toContainText('training contracts offered');

  // the contracts start in September 2007: the trainees join and rotate their seats
  await advanceMonths(page, slug, 33);
  await page.goto(`/game/${slug}/offices`);
  await expect(page.getByTestId('trainee-row').first()).toBeVisible();

  // two years on, each September: they qualify as solicitors
  await advanceMonths(page, slug, 24);
  const inbox = await (await page.request.get(`/api/saves/${slug}/inbox`)).json();
  const qualified = inbox.filter((i: { template: string }) => i.template === 'trainee_qualified');
  expect(qualified.length).toBeGreaterThan(0);
  await page.goto(`/game/${slug}/people/${qualified[0].link_id}`);
  await expect(
    page.getByTestId('admission-row').filter({ hasText: 'England and Wales' }),
  ).toBeVisible();
  await expect(page.getByTestId('person-office')).toHaveText('London');
});
