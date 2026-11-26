import { expect, test } from '@playwright/test';

// PT-M3c: staff a new named matter on the board (drag, hours, the engine's refusal), read its
// outlook as a band, see it billed with its realisation, then introduce a colleague to the
// client. Group lift, seed 18 (PT-M16: seed 3's first month no longer brings one): the first
// month brings an M&A matter.
test('staff a named matter, bill it, see realisation, introduce a colleague', async ({ page }) => {
  const made = await page.request.post('/api/saves', {
    data: { slug: 'm3c', firm_name: 'Screens LLP', seed: 18, scenario_id: 'group_lift' },
  });
  expect(made.ok()).toBeTruthy();
  await page.goto('/game/m3c');
  await expect(page.getByTestId('date')).toHaveText('Jan 2005');
  await page.getByRole('button', { name: 'Continue' }).click();
  await expect(page.getByTestId('date')).toHaveText('Feb 2005');

  await page.getByRole('link', { name: 'Matters', exact: true }).click();
  const link = page.getByTestId('matter-link').first();
  await expect(link).toBeVisible();
  await link.click();
  const board = page.getByTestId('staffing-board');
  await expect(board).toBeVisible();

  // Drag the first available colleague onto the team at 20 hours a month (once the board has
  // settled, so the list does not reorder under the pointer).
  await page.waitForLoadState('networkidle');
  const name = (await board.getByTestId('board-person').first().getAttribute('data-person')) ?? '';
  const card = board.locator(`[data-testid="board-person"][data-person="${name}"]`);
  await board.getByLabel('Hours a month', { exact: true }).fill('20');
  await card.dragTo(board.getByTestId('team-drop'), { targetPosition: { x: 40, y: 12 } });
  const member = board.locator(`[data-testid="team-member"][data-person="${name}"]`);
  await expect(member).toBeVisible();
  await expect(member.getByLabel(`Hours a month for ${name}`)).toHaveValue('20 h');

  // Asking for more than they can carry: the engine refuses and says how much fits.
  await member.getByLabel(`Hours a month for ${name}`).fill('400');
  await member.getByRole('button', { name: 'Set' }).click();
  await expect(page.getByTestId('matter-error')).toContainText('at most');
  await expect(member.getByLabel(`Hours a month for ${name}`)).toHaveValue('400 h');
  await page.reload();
  await expect(member.getByLabel(`Hours a month for ${name}`)).toHaveValue('20 h');

  // The outlook is a band, never a number.
  await page.getByRole('button', { name: 'Explain the outlook' }).click();
  const panel = page.getByTestId('explain-panel');
  await expect(panel).toContainText('Team craft, as you see it');
  await expect(panel).not.toContainText('%');
  await page.keyboard.press('Escape');

  // A month on, the matter has hours from the new member.
  await page.getByRole('button', { name: 'Continue' }).click();
  await expect(page.getByTestId('date')).toHaveText('Mar 2005');
  await expect(member).toContainText('h last month');

  // The matter has been billed: billed value, realisation and the bill itself.
  const bills = page.getByTestId('bills');
  await expect(bills.getByTestId('matter-billed')).not.toHaveText('$0');
  await expect(page.getByTestId('matter-realisation')).toHaveText(/^\d+\.\d%$/);
  await expect(bills.getByTestId('matter-bill').first()).toBeVisible();
  await page.getByRole('button', { name: 'Explain realisation' }).click();
  await expect(page.getByTestId('explain-panel')).toContainText('Billed');
  await page.keyboard.press('Escape');
  // A partner writes the next bill down; the API echoes it.
  await bills.getByLabel('Write the next bill down').fill('10');
  await bills.getByRole('button', { name: 'Set write-down' }).click();
  await expect(bills).toContainText('10.0%');
  await page.getByRole('link', { name: 'Matters', exact: true }).click();
  await expect(page.getByTestId('realisation').first()).toHaveText(/%$/);
  await page.getByTestId('matter-link').first().click();

  // Introduce a colleague to the client in a practice it does not use yet.
  await page.getByTestId('matter-name').waitFor();
  await page.locator('a[href*="/clients/"]').first().click();
  await expect(page.getByTestId('client-name')).toBeVisible();
  const row = page
    .getByTestId('cross-sell-row')
    .filter({ has: page.getByRole('button', { name: /^Introduce for / }) })
    .first();
  await row.getByRole('combobox').click();
  await page.getByRole('option').first().click();
  await row.getByRole('button', { name: /^Introduce for / }).click();
  await expect(page.getByTestId('introduce-done')).toBeVisible();
});

test('practices and clients tables keep a saved view', async ({ page }) => {
  const made = await page.request.post('/api/saves', {
    data: { slug: 'm3c-views', firm_name: 'Views LLP', seed: 3, scenario_id: 'group_lift' },
  });
  expect(made.ok()).toBeTruthy();
  await page.goto('/game/m3c-views/practices');
  await expect(page.getByTestId('practice-row')).toHaveCount(20); // PT-M12: twenty practices
  await page.getByRole('button', { name: "Explain the firm's utilisation" }).click();
  await expect(page.getByTestId('explain-panel')).toContainText('Capacity this month');
  await page.keyboard.press('Escape');

  await page.getByRole('link', { name: 'Clients', exact: true }).click();
  await expect(page.getByTestId('client-row').first()).toBeVisible();
  await page.getByTestId('views-clients').click();
  await page.getByTestId('column-sector').click();
  await page.getByTestId('view-save-as').click();
  await page.getByTestId('view-name').fill('Lean');
  await page.getByTestId('view-save').click();
  await expect(page.getByTestId('views-clients')).toHaveText(/View: Lean/);
  await page.reload();
  await expect(page.getByTestId('views-clients')).toHaveText(/View: Lean/);
  await expect(page.getByRole('columnheader', { name: 'Sector' })).toHaveCount(0);
});
