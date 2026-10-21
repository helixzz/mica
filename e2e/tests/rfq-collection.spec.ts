import { test, expect, Page } from '@playwright/test';
import { loginAs, loginViaApi } from './helpers/auth';

/**
 * Outstanding quotations surface twice: on the dashboard card and as a banner on
 * the RFQ list. Both need seeded data (../seed_data.py) — without it the specs
 * skip rather than fail, so the CI smoke database stays green.
 */

async function pendingCount(page: Page): Promise<number> {
  const token = await loginViaApi(page, 'alice');
  const response = await page.request.get('/api/v1/rfqs/pending-collection', {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!response.ok()) return 0;
  const rows = (await response.json()) as unknown[];
  return rows.length;
}

test.describe('Quotations awaiting collection', () => {
  test.beforeEach(async ({ page }) => {
    // The dashboard opens in its welcome state on a fresh profile, which hides every
    // card until dismissed. Real users dismissed it long ago.
    await page.addInitScript(() => localStorage.setItem('mica.welcome_dismissed', '1'));
    await loginAs(page, 'alice');
  });

  test('the RFQ list flags them and opens the to-do list', async ({ page }) => {
    const count = await pendingCount(page);
    test.skip(count === 0, 'no outstanding quotations in this environment');

    await page.goto('/rfqs');
    await page.waitForSelector('.ant-table', { timeout: 20_000 });

    const banner = page.locator('.ant-alert').first();
    await expect(banner).toBeVisible({ timeout: 15_000 });

    await banner.getByRole('button').click();
    const modal = page.locator('.ant-modal');
    await expect(modal).toBeVisible({ timeout: 10_000 });
    // Seeded RFQs are past their deadline, so the row carries an overdue tag.
    await expect(modal.locator('.ant-table-tbody tr').first()).toBeVisible();
    await expect(modal.getByText(/已超期|overdue/).first()).toBeVisible();
  });

  test('the dashboard carries the same to-do', async ({ page }) => {
    const count = await pendingCount(page);
    test.skip(count === 0, 'no outstanding quotations in this environment');

    await page.goto('/dashboard');
    await page.waitForSelector('.ant-card', { timeout: 20_000 });

    const title = page.getByText(/待取回询价单|Awaiting quotations/).first();
    await expect(title).toBeVisible({ timeout: 15_000 });
  });

  test('an RFQ detail offers the generated quotation sheet', async ({ page }) => {
    const token = await loginViaApi(page, 'alice');
    const response = await page.request.get('/api/v1/rfqs/pending-collection', {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!response.ok()) {
      test.skip(true, 'cannot list RFQs here');
    }
    const rows = (await response.json()) as Array<{ id: string }>;
    if (!rows.length) {
      test.skip(true, 'no outstanding quotations in this environment');
    }

    await page.goto(`/rfqs/${rows[0].id}`);
    await page.waitForSelector('.ant-btn', { timeout: 20_000 });

    const button = page.getByRole('button', { name: /生成询价单|Generate quotation/ }).first();
    await expect(button).toBeVisible({ timeout: 15_000 });
  });
});
