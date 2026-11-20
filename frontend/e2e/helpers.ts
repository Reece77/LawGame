import { expect, type Page } from '@playwright/test';

// PT-M6: a critical event blocks Continue until it is answered (spec 15). Smoke tests that
// play many months answer one with its first choice, as a player in a hurry would.
export async function continueMonth(page: Page): Promise<void> {
  const cont = page.getByRole('button', { name: 'Continue' });
  if (await cont.isDisabled()) {
    const dialog = page.getByRole('dialog');
    await dialog.getByRole('button', { name: 'Choose A' }).click();
    await expect(cont).toBeEnabled();
  }
  await cont.click();
}
