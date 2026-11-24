import { expect, test } from '@playwright/test';
import { advanceMonths, answerBlocking } from './helpers.js';

// PT-M14: in the 2022 practice save, play into January 2023, adopt generative AI on the
// Technology screen (invest, roll it out to the partners, set the training programme), play
// a month and see adoption rise, then launch a fixed-fee product.
test('adopt generative AI in 2023 and launch a fixed-fee product', async ({ page }) => {
  test.setTimeout(300_000);
  const made = await page.request.post('/api/practice/pt-2022');
  expect([200, 409]).toContain(made.status());
  await answerBlocking(page, 'pt-2022');
  await advanceMonths(page, 'pt-2022', 1); // January 2023
  await answerBlocking(page, 'pt-2022');

  await page.goto('/game/pt-2022/technology');
  await expect(page.getByRole('heading', { name: 'Technology' })).toBeVisible({ timeout: 60_000 });
  await expect(page.getByTestId('era-row')).toHaveCount(6);
  await expect(page.getByTestId('adoption-genai')).toContainText('0%');
  await page.getByTestId('invest-genai').click();
  await expect(page.getByTestId('stop-genai')).toBeVisible();
  await expect(page.getByTestId('adoption-genai')).toContainText('pilot');
  await page.getByTestId('rollout-genai').click();
  await expect(page.getByTestId('rollout-genai')).toBeHidden();
  await page.getByTestId('training-hours').fill('40');
  await page.getByTestId('set-training').click();
  await expect(page.getByTestId('training')).toContainText('40 hours a lawyer a year');

  await advanceMonths(page, 'pt-2022', 1);
  await page.reload();
  await expect(page.getByTestId('adoption-genai')).not.toContainText(/^0%/);
  await expect(page.getByTestId('task-row')).toHaveCount(8); // hours by task: 2023's tools are young

  await page.getByTestId('product-kind').click();
  await page.getByRole('option').first().click();
  await page.getByTestId('launch-product').click();
  await expect(page.getByTestId('product-row')).toHaveCount(1);
  await expect(page.getByTestId('product-error')).toHaveCount(0);
});
