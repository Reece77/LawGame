import { expect, test, type Page } from '@playwright/test';

async function choose(page: Page, label: string, option: string) {
  await page.getByRole('combobox', { name: label, exact: true }).click();
  await page.getByRole('option', { name: option, exact: true }).click();
}

test('create a practice group, set a leader, open a plan', async ({ page }) => {
  await page.goto('/new');
  await page.getByLabel('Firm name').fill('Org Test LLP');
  await choose(page, 'Scenario', 'Group lift');
  await page.getByRole('button', { name: 'Found the firm' }).click();
  await expect(page.getByTestId('date')).toHaveText('Jan 2005');

  await page.getByRole('link', { name: 'Org' }).click();
  await expect(page.getByTestId('unlock-note')).toContainText('10 lawyers');
  await choose(page, 'Practice', 'Commercial litigation');
  await page.getByRole('button', { name: 'Create practice group' }).click();
  const units = page.getByTestId('org-units');
  await expect(units).toContainText('Commercial litigation');
  await expect(units).toContainText('Nobody here yet.');

  // Move the first associate at the firm root into the group, then make them its leader.
  const firstMove = page.getByRole('combobox', { name: /^Move / }).first();
  const label = (await firstMove.getAttribute('aria-label')) ?? '';
  const name = label.replace(/^Move /, '');
  await firstMove.click();
  await page.getByRole('option', { name: 'Commercial litigation', exact: true }).click();
  await expect(units).toContainText(name);
  await choose(page, 'Leader of Commercial litigation', name);
  await expect(units.getByText('leader', { exact: true })).toBeVisible();

  // The leader runs a hiring plan for the group.
  await choose(page, 'Delegate', name);
  await choose(page, 'Role', 'Commercial litigator');
  await page.getByRole('combobox', { name: 'Joins', exact: true }).click();
  await page.getByRole('option', { name: 'Commercial litigation', exact: true }).click();
  await page.getByRole('textbox', { name: 'Hires', exact: true }).fill('2');
  await page.getByRole('button', { name: 'Open plan' }).click();
  const plans = page.getByTestId('plans-table');
  await expect(plans).toContainText(name);
  await expect(plans).toContainText('0 / 2');
  await expect(plans).toContainText('Active');

  // The month passes; the org and the plan are still there, and the leader's profile shows it.
  await page.getByRole('button', { name: 'Continue' }).click();
  await expect(page.getByTestId('date')).toHaveText('Feb 2005');
  await expect(plans).toContainText(name);
  await page.getByRole('link', { name: 'People' }).click();
  await page.getByRole('link', { name, exact: true }).click();
  const panel = page.getByTestId('person-org');
  await expect(panel).toContainText('Commercial litigation');
  await expect(panel).toContainText('Hiring plans run');
});
