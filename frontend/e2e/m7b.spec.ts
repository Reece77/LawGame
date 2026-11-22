import { expect, test } from '@playwright/test';

// PT-M7b: the Practices screen's card by practice (a new firm's share of the top card, and
// the share its reputation earns), the Org screen's hours policy, and the revolver card's
// forecast line on Finance (shown only while the trend breaks a covenant).
test('a new firm card, the hours policy and the finance revolver', async ({ page }) => {
  test.setTimeout(120_000);
  const made = await page.request.post('/api/saves', {
    data: { slug: 'pressure-test', firm_name: 'Pressure Test LLP', seed: 5 },
  });
  expect(made.ok()).toBeTruthy();

  await page.goto('/game/pressure-test/practices');
  await expect(page.getByRole('columnheader', { name: 'Our card (earned)' })).toBeVisible();
  await expect(page.getByTestId('practice-card').first()).toContainText('%');
  await expect(page.getByRole('columnheader', { name: 'Our card', exact: true })).toBeVisible();

  await page.goto('/game/pressure-test/org');
  await expect(page.getByTestId('firm-policies')).toBeVisible();
  await expect(page.getByTestId('hours-current')).toContainText("Each level's target");
  await page.getByTestId('hours-levels').click();
  await page.getByTestId('hours-target').fill('2400');
  await page.getByTestId('hours-save').click();
  await expect(page.getByTestId('hours-current')).toContainText('2400 h a year');

  await page.goto('/game/pressure-test/finance');
  await expect(page.getByTestId('revolver')).toBeVisible();
});
