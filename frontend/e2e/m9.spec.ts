import { expect, test } from '@playwright/test';
import { advanceMonths } from './helpers.js';

// PT-M9: in the practice save, give billing to the CFO on the Automation screen, set its
// limit, play a month, open the digest from the inbox, see "Run by" on Finance and take over.
test('automate billing, read the digest, take over', async ({ page }) => {
  test.setTimeout(240_000);
  const made = await page.request.post('/api/practice/pt-2008');
  expect([200, 409]).toContain(made.status()); // an earlier spec may have opened it

  const lead = await (await page.request.get('/api/saves/pt-2008/leadership')).json();
  const cfo = lead.seats.find((s: { key: string }) => s.key === 'cfo').slots[0];
  if (cfo.holder === null) {
    const appointed = await page.request.post('/api/saves/pt-2008/leadership/appoint', {
      data: { seat: 'cfo', slot: 0, person_id: cfo.candidates[0].person_id },
    });
    expect(appointed.ok()).toBeTruthy();
  }

  await page.goto('/game/pt-2008/automation');
  await expect(page.getByTestId('automation-screen')).toBeVisible({ timeout: 60_000 });
  await page.getByTestId('owner-pick-billing:0').click();
  await page.getByRole('option').first().click();
  await page.getByTestId('give-billing:0').click();
  await expect(page.getByTestId('take-over-billing:0')).toBeVisible();
  await page.getByTestId('settings-billing:0').click();
  await page.getByTestId('limit-input').fill('100000');
  await page.getByTestId('save-settings').click();
  await expect(page.getByText('$100,000 /')).toBeVisible();

  await advanceMonths(page, 'pt-2008', 1);
  await page.getByRole('link', { name: 'Inbox' }).click();
  await page
    .getByRole('link', { name: /Your month:/ })
    .first()
    .click();
  await expect(page.getByTestId('digest')).toContainText('Billing and collections');

  await page.getByRole('link', { name: 'Finance' }).click();
  await expect(page.getByTestId('run-by-billing')).toContainText('run by');
  await page.getByTestId('take-over-billing').click();
  await expect(page.getByTestId('run-by-billing')).toContainText('you run it');
});
