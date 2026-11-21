import { expect, test, type Page } from '@playwright/test';

// PT-M4: hold a December vote and admit a partner; survive a lateral departure. Test-only
// routes (PTK_DEBUG_ROUTES=1) set up a strong candidate and a rival's approach, so the
// outcome does not hang on seed luck.

// PT-M7: a fixed seed (5). With overhead per lawyer an untouched group lift founded on a
// random seed can dissolve before December (4 of 12 seeds do within two years), which made
// this test time out by seed luck; seed 5's firm lives.
async function found(page: Page, name: string): Promise<string> {
  const slug = name
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/-+$/, '');
  const made = await page.request.post('/api/saves', {
    data: { slug, firm_name: name, seed: 5, scenario_id: 'group_lift' },
  });
  expect(made.ok()).toBeTruthy();
  await page.goto(`/game/${slug}`);
  await expect(page.getByTestId('date')).toHaveText('Jan 2005');
  return slug;
}

async function advanceTo(page: Page, label: string) {
  for (let i = 0; i < 24; i++) {
    if ((await page.getByTestId('date').textContent()) === label) return;
    const before = await page.getByTestId('date').textContent();
    await page.getByRole('button', { name: 'Continue' }).click();
    await expect(page.getByTestId('date')).not.toHaveText(before ?? '');
  }
  await expect(page.getByTestId('date')).toHaveText(label);
}

test('hold a December vote and admit a partner', async ({ page }) => {
  test.setTimeout(180_000);
  const slug = await found(page, 'Vote Test LLP');
  await advanceTo(page, 'Dec 2005');
  const made = await page.request.post(`/api/saves/${slug}/debug/candidate`, { data: {} });
  expect(made.ok()).toBeTruthy();

  await page.getByRole('link', { name: 'Partnership' }).click();
  await expect(page.getByRole('heading', { name: 'Partnership' })).toBeVisible();
  await expect(page.getByTestId('partners-table')).toBeVisible();
  const propose = page.locator('[data-testid^="propose-"][data-testid$="-equity"]').first();
  await propose.click();
  await expect(page.getByTestId('vote-admission')).toContainText('open');

  await page.getByRole('button', { name: 'Continue' }).click();
  await expect(page.getByTestId('date')).toHaveText('Jan 2006');
  await expect(page.getByTestId('vote-admission')).toContainText('passed');
  await expect(page.getByTestId('partners-table')).toContainText('equity');
  const rows = page.getByTestId('partners-table').locator('tbody tr');
  await expect(rows).toHaveCount(4);
});

test('survive a lateral departure', async ({ page }) => {
  test.setTimeout(120_000);
  const slug = await found(page, 'Flight Test LLP');
  await page.getByRole('button', { name: 'Continue' }).click();
  await expect(page.getByTestId('date')).toHaveText('Feb 2005');

  const approached = await page.request.post(`/api/saves/${slug}/debug/approach`, { data: {} });
  expect(approached.ok()).toBeTruthy();
  await page.getByRole('link', { name: 'Partnership' }).click();
  const approaches = page.getByTestId('approaches');
  await expect(approaches).toContainText('offers');
  await approaches.locator('[data-testid^="counter-"]').first().click();
  await expect(approaches).toContainText('countered');

  // The partner leaves anyway (a forced departure): clients may follow, capital is repaid.
  const left = await page.request.post(`/api/saves/${slug}/debug/depart`, { data: {} });
  expect(left.ok()).toBeTruthy();
  await page.reload();
  await expect(page.getByTestId('departure').first()).toContainText('left for');
  for (const month of ['Mar 2005', 'Apr 2005', 'May 2005']) {
    await page.getByRole('button', { name: 'Continue' }).click();
    await expect(page.getByTestId('date')).toHaveText(month);
  }
  await expect(page.getByTestId('partners-table').locator('tbody tr')).toHaveCount(2);
  await page.getByRole('link', { name: 'Finance' }).click();
  await expect(page.getByTestId('capital-accounts')).toContainText('Capital owed to partners');
});
