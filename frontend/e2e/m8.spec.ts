import { expect, test } from '@playwright/test';
import { answerBlocking } from './helpers.js';

// PT-M8: in the practice save (a 60-lawyer firm at stage 2), appoint a CFO on the Org
// screen's Leadership panel, give the seat authority, then receive the CFO's pitch in the
// inbox (the quarterly draw forced by a test-only route) and approve it.
test('appoint a CFO, receive and approve a pitch', async ({ page }) => {
  test.setTimeout(180_000);
  const made = await page.request.post('/api/practice/pt-2008');
  expect([200, 409]).toContain(made.status()); // m7's spec may have opened it already
  await answerBlocking(page, 'pt-2008'); // PT-M16: a critical event may be waiting

  await page.goto('/game/pt-2008/org');
  const panel = page.getByTestId('leadership-panel');
  await expect(panel).toBeVisible({ timeout: 60_000 });
  const cfo = page.getByTestId('seat-cfo-0');
  await expect(cfo).toContainText('vacant');
  await cfo.getByTestId('seat-candidates').click();
  await page.getByRole('option').first().click();
  await cfo.getByTestId('seat-appoint').click();
  await expect(cfo.getByTestId('seat-holder')).toBeVisible();
  await expect(cfo.getByTestId('seat-fit')).toContainText('fit');
  await cfo.getByTestId('seat-authority').click();
  await expect(cfo.getByTestId('seat-authority')).toBeChecked();

  const pitched = await page.request.post('/api/saves/pt-2008/debug/pitch');
  expect(pitched.ok()).toBeTruthy();
  await page.getByRole('link', { name: 'Inbox' }).click();
  const card = page.getByTestId('pitch-card').first();
  await expect(card).toBeVisible();
  await expect(card.getByTestId('pitch-status')).toHaveText('pending');
  await card.getByTestId('pitch-approve').click();
  await expect(card.getByTestId('pitch-status')).toHaveText('approved');
});
