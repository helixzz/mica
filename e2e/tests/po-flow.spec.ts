import { test, expect } from '@playwright/test';
import { loginAs, navigateTo } from './helpers/auth';

test.describe('Purchase Orders', () => {
  test.beforeEach(async ({ page }) => {
    await loginAs(page, 'alice');
  });

  test('PO list page loads and shows table', async ({ page }) => {
    await navigateTo(page, '/purchase-orders');

    // The page should have a table
    await expect(page.locator('.ant-table')).toBeVisible({ timeout: 10_000 });
  });

  test('PO list page has page header', async ({ page }) => {
    await navigateTo(page, '/purchase-orders');

    // Should have some heading or title
    const heading = page.getByRole('heading').first();
    await expect(heading).toBeVisible({ timeout: 10_000 });
  });

  test('navigate to PO detail if any PO exists', async ({ page }) => {
    await navigateTo(page, '/purchase-orders');

    // Wait for table to load
    await page.waitForSelector('.ant-table', { timeout: 10_000 });

    // Try to click on the first row to navigate to detail
    const firstRow = page.locator('.ant-table-tbody tr').first();
    if (await firstRow.isVisible({ timeout: 3000 }).catch(() => false)) {
      // Click on a link in the first row
      const firstLink = firstRow.locator('a').first();
      if (await firstLink.isVisible({ timeout: 2000 }).catch(() => false)) {
        await firstLink.click();
        await page.waitForLoadState('networkidle');

        // Should be on a PO detail page
        await expect(page).toHaveURL(/\/purchase-orders\/[a-f0-9-]+/, { timeout: 10_000 });
      }
    }
  });

  test('PO list is accessible from sidebar navigation', async ({ page }) => {
    // Click the PO link in the sidebar
    await page.locator('.ant-menu-item a[href="/purchase-orders"]').click();

    await expect(page).toHaveURL(/\/purchase-orders/, { timeout: 10_000 });
    await page.waitForLoadState('networkidle');
  });
});