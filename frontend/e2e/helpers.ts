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

// PT-M7: play months through the API, answering a blocking critical event with choice A.
export async function advanceMonths(page: Page, slug: string, months: number): Promise<void> {
  for (let i = 0; i < months; i += 1) {
    const game = await (await page.request.get(`/api/saves/${slug}/game`)).json();
    if (game.blocking_event_id !== null) {
      const chose = await page.request.post(
        `/api/saves/${slug}/events/${game.blocking_event_id}/choose`,
        { data: { choice: 'A' } },
      );
      expect(chose.ok()).toBeTruthy();
    }
    const r = await page.request.post(`/api/saves/${slug}/advance`);
    expect(r.ok()).toBeTruthy();
  }
}
