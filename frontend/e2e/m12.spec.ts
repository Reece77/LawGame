import { expect, test } from '@playwright/test';
import { advanceMonths, answerBlocking } from './helpers.js';

// PT-M12: the Practices screen shows twenty practices with their cycle filter and the
// firm's position; enter international arbitration with a lateral partner (the recruiter's
// search, then the offer on the Partnership screen) and see the firm practise it.
test('enter international arbitration with a lateral partner', async ({ page }) => {
  test.setTimeout(300_000);
  const made = await page.request.post('/api/saves', {
    data: { slug: 'm12', firm_name: 'Twenty LLP', seed: 1, scenario_id: 'biglaw_spinout' },
  });
  expect(made.ok()).toBeTruthy();
  await page.goto('/game/m12/practices');
  await expect(page.getByTestId('practice-row')).toHaveCount(20, { timeout: 60_000 });
  await page.getByTestId('filter-cycle').click();
  await page.getByRole('option', { name: 'Counter cyclical' }).click();
  await expect(page.getByTestId('practice-row')).toHaveCount(2); // restructuring, employment
  await page.getByTestId('filter-cycle').click();
  await page.getByRole('option', { name: 'Counter cyclical' }).click(); // deselect
  await expect(page.getByTestId('practice-row')).toHaveCount(20);

  await page.getByTestId('enter-practice-select').click();
  await page.getByRole('option', { name: 'International arbitration' }).click();
  await page.getByTestId('enter-practice-go').click();
  await expect(page.getByTestId('enter-practice-done')).toBeVisible();

  // the recruiter's candidates are on the Partnership screen: offer the first one its ask
  await page.goto('/game/m12/partnership');
  const laterals = page.getByTestId('laterals');
  await expect(laterals).toContainText('International arbitration', { timeout: 60_000 });
  await laterals.getByRole('button', { name: 'Offer the ask' }).first().click();
  await expect(laterals).toContainText('offered');

  // the offer resolves in phase 1; wait on the state (the practice held), not on time
  for (let i = 0; i < 6; i += 1) {
    await advanceMonths(page, 'm12', 1);
    const rows = await (await page.request.get('/api/saves/m12/practices/screen')).json();
    if (rows.find((p: { key: string }) => p.key === 'international_arbitration').practised) break;
  }
  await page.goto('/game/m12/practices');
  const arb = page.getByTestId('practice-row').filter({ hasText: 'International arbitration' });
  await expect(arb.getByTestId('practice-practised')).toBeVisible({ timeout: 60_000 });
});

// PT-M12 (ADR PT-0018): in the 2022 practice save, enter plaintiff mass torts with a lateral
// team, play until the firm has a contingency case, and take a litigation funder's offer on it.
test('fund a mass-tort case', async ({ page }) => {
  test.setTimeout(600_000);
  const made = await page.request.post('/api/practice/pt-2022');
  expect([200, 409]).toContain(made.status());
  await answerBlocking(page, 'pt-2022');
  const entered = await page.request.post('/api/saves/pt-2022/practices/mass_torts/enter', {
    data: { route: 'team', person_id: null },
  });
  expect([200, 409, 422]).toContain(entered.status()); // a rerun finds it entered already
  let matterId: number | null = null;
  for (let i = 0; i < 24 && matterId === null; i += 1) {
    const matters = await (await page.request.get('/api/saves/pt-2022/matters')).json();
    for (const m of matters as { id: number; practice: string }[]) {
      if (m.practice !== 'mass_torts') continue;
      const detail = await (await page.request.get(`/api/saves/pt-2022/matters/${m.id}`)).json();
      if (detail.billing_model === 'contingency' && (detail.funding_offer_bp || detail.funded)) {
        matterId = m.id;
        break;
      }
    }
    if (matterId === null) await advanceMonths(page, 'pt-2022', 1);
  }
  expect(matterId).not.toBeNull();
  await answerBlocking(page, 'pt-2022');
  await page.goto(`/game/pt-2022/matters/${matterId}`);
  const panel = page.getByTestId('contingency');
  await expect(panel).toBeVisible({ timeout: 60_000 });
  if (await panel.getByTestId('accept-funding').isVisible()) {
    await expect(panel.getByTestId('funding-offer')).toBeVisible();
    await panel.getByTestId('accept-funding').click();
  }
  await expect(panel.getByTestId('funding-terms')).toContainText('non-recourse');
});
