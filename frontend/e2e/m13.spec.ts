import { expect, test, type Page } from '@playwright/test';
import { advanceMonths, answerBlocking } from './helpers.js';

// PT-M13: mergers and the verein, on copies of the practice save (a 60-lawyer firm in June
// 2008; its own slugs, so the other specs' pt-2008 is untouched). The paths are the seeded
// world's: in the merger the firms are approached in turn until one talks (PT-M12's twenty
// practices moved which one), and in the verein the first declines and the second talks.

// a firm's rival key: names can repeat among generated firms (the first in the API's order)
async function keyOf(page: Page, slug: string, firm: string): Promise<string> {
  const view = await (await page.request.get(`/api/saves/${slug}/mergers`)).json();
  type T = { key: string; name: string; fair_share_pct: number };
  const all = (view.targets as T[]).filter((t) => t.name === firm);
  all.sort((a, b) => b.fair_share_pct - a.fair_share_pct); // the search's order
  return all[0].key;
}

async function approach(
  page: Page,
  slug: string,
  firm: string,
  form: 'Merger' | 'Verein',
): Promise<void> {
  const key = await keyOf(page, slug, firm);
  const panel = page.getByTestId('targets');
  await panel.getByTestId('approach-firm').click();
  await page.locator(`[role="option"][value="${key}"]`).click();
  await panel.getByText(form, { exact: true }).click();
  await panel.getByTestId('approach').click();
}

async function practiceCopy(page: Page, slug: string): Promise<void> {
  const made = await page.request.post(`/api/practice/pt-2008?slug=${slug}`);
  expect(made.ok()).toBeTruthy();
  await answerBlocking(page, slug);
}

test('merge with a generated firm through both votes and clearance', async ({ page }) => {
  test.setTimeout(900_000);
  const slug = 'm13-merger';
  await practiceCopy(page, slug);
  await advanceMonths(page, slug, 31); // June 2008 to January 2011
  await answerBlocking(page, slug);
  await page.goto(`/game/${slug}/mergers`);
  await expect(page.getByTestId('date')).toHaveText('Jan 2011');

  // approach until a firm talks; one that declines is recorded and the next is tried next month
  const deal = page.getByTestId('deal');
  let firm = '';
  for (const name of ['Murphy Cook', 'Murphy LLP']) {
    await approach(page, slug, name, 'Merger');
    const talks = deal.getByTestId('deal-stage').filter({ hasText: 'Talks' });
    const declined = page.getByTestId('past-deals').filter({ hasText: 'declined to talk' });
    await expect(talks.or(declined)).toBeVisible();
    if (await talks.isVisible()) {
      firm = name;
      break;
    }
    await advanceMonths(page, slug, 1);
    await answerBlocking(page, slug);
    await page.reload();
  }
  expect(firm).not.toBe('');
  await expect(deal.getByTestId('deal-stage')).toHaveText('Talks');
  await expect(deal.getByTestId('diligence')).toContainText('Partners'); // ranges, not values

  const view = await (await page.request.get(`/api/saves/${slug}/mergers`)).json();
  const key = await keyOf(page, slug, firm);
  const fair = view.targets.find((t: { key: string }) => t.key === key).fair_share_pct;
  await deal.getByTestId('terms-share').fill(String(fair));
  await deal.getByTestId('put-terms').click();
  await expect(deal.getByTestId('deal-stage')).toHaveText('Terms');

  // their partners counter; the MP has won the partners round (a test-only route) and accepts
  await advanceMonths(page, slug, 1);
  await answerBlocking(page, slug);
  await page.reload();
  await expect(page.getByTestId('counter')).toBeVisible();
  const lobbied = await page.request.post(`/api/saves/${slug}/debug/candidate`, { data: {} });
  expect(lobbied.ok()).toBeTruthy();
  await answerBlocking(page, slug);
  await page.reload();
  // answer the counter a little more generously than asked, so their partners' noisy count
  // (centred on the counter's margin) passes on this world's draws
  const open = (await (await page.request.get(`/api/saves/${slug}/mergers`)).json()).deals.find(
    (d: { stage: string }) => d.stage === 'countered',
  );
  await page.getByTestId('terms-share').fill(String(open.counter_share_pct - 4));
  await page.getByTestId('put-terms').click();
  await expect(page.getByTestId('deal-stage')).toHaveText('Terms'); // saved before Continue

  // both partnerships vote: conflicts are cleared, and it closes the next month
  await advanceMonths(page, slug, 1);
  await answerBlocking(page, slug);
  await page.reload();
  await expect(page.getByTestId('deal-stage')).toHaveText('Clearance');
  await expect(page.getByTestId('conflicts')).toBeVisible();
  await advanceMonths(page, slug, 1);
  await answerBlocking(page, slug);
  await page.reload();
  await expect(page.getByTestId('integration')).toContainText(`Integration of ${firm}`);
  await expect(page.getByTestId('partners-lost')).toContainText('of');
});

test('form a verein with a London firm', async ({ page }) => {
  test.setTimeout(600_000);
  const slug = 'm13-verein';
  await practiceCopy(page, slug);
  await page.goto(`/game/${slug}/mergers`);
  await approach(page, slug, 'Eversheds', 'Verein');
  await expect(page.getByTestId('past-deals')).toContainText('declined to talk');
  await advanceMonths(page, slug, 1);
  await answerBlocking(page, slug);
  await page.reload();
  await approach(page, slug, 'Lovells', 'Verein');
  await expect(page.getByTestId('deal-stage')).toHaveText('Talks');
  await page.getByTestId('put-terms').click();
  await expect(page.getByTestId('deal-stage')).toHaveText('Terms'); // saved before Continue
  await advanceMonths(page, slug, 2); // both partnerships vote, then it closes
  await answerBlocking(page, slug);
  await page.goto(`/game/${slug}`);
  await expect(page.getByTestId('verein-member')).toContainText('Lovells');
  await expect(page.getByTestId('verein-member')).toContainText('London');
});
