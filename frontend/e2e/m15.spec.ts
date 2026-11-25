import { expect, test } from '@playwright/test';
import { advanceMonths } from './helpers.js';

// PT-M15: in the risk practice save (June 2008), a claim from an escaped error has been through
// notice, investigation and defence to the claimant's offer: settle it on the Risk screen and
// see the policy pay its part. The month's reconciliation found a client-account shortfall:
// the next month raises the critical event, and a second claim surfaces.
test('a claim settles under the policy and a trust shortfall raises a critical event', async ({
  page,
}) => {
  test.setTimeout(300_000);
  const made = await page.request.post('/api/practice/pt-risk');
  expect([200, 409]).toContain(made.status());

  await page.goto('/game/pt-risk/risk');
  await expect(page.getByRole('heading', { name: 'Risk' })).toBeVisible({ timeout: 60_000 });
  await expect(page.getByTestId('policy')).toContainText('premium');
  await expect(page.getByTestId('claim-row')).toHaveCount(1);
  const settle = page.locator('[data-testid^="settle-claim-"]');
  await expect(settle).toBeVisible();
  await settle.click();
  await expect(page.locator('[data-testid^="claim-stage-"]')).toContainText('Settled');
  await expect(page.locator('[data-testid^="claim-paid-"]')).toContainText('/');
  await expect(page.getByTestId('trust')).toContainText('made good');

  await advanceMonths(page, 'pt-risk', 1);
  const game = await (await page.request.get('/api/saves/pt-risk/game')).json();
  expect(game.blocking_event_id).not.toBeNull();
  await page.goto('/game/pt-risk');
  await expect(page.getByRole('dialog')).toContainText('A shortfall in the client account', {
    timeout: 60_000,
  });
  await page.getByRole('dialog').getByRole('button', { name: 'Choose A' }).click();

  await page.goto('/game/pt-risk/risk');
  await expect(page.getByTestId('claim-row')).toHaveCount(2);
});
