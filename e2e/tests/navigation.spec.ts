import { test, expect } from '@playwright/test';
import { loginAs } from './helpers/auth';

test.describe('Navigation', () => {
  test.beforeEach(async ({ page }) => {
    await loginAs(page, 'admin');
  });

  test('navigate to Dashboard via sidebar', async ({ page }) => {
    await page.locator('.ant-menu-item a[href="/dashboard"]').click();
    await expect(page).toHaveURL(/\/dashboard/, { timeout: 10_000 });
  });

  test('navigate to Approvals via sidebar', async ({ page }) => {
    await page.locator('.ant-menu-item a[href="/approvals"]').click();
    await expect(page).toHaveURL(/\/approvals/, { timeout: 10_000 });
    await page.waitForLoadState('networkidle');
  });

  test('navigate to Purchase Requisitions via sidebar', async ({ page }) => {
    await page.locator('.ant-menu-item a[href="/purchase-requisitions"]').click();
    await expect(page).toHaveURL(/\/purchase-requisitions/, { timeout: 10_000 });
    await page.waitForLoadState('networkidle');
  });

  test('navigate to Purchase Orders via sidebar', async ({ page }) => {
    await page.locator('.ant-menu-item a[href="/purchase-orders"]').click();
    await expect(page).toHaveURL(/\/purchase-orders/, { timeout: 10_000 });
    await page.waitForLoadState('networkidle');
  });

  test('navigate to Contracts via sidebar', async ({ page }) => {
    await page.locator('.ant-menu-item a[href="/contracts"]').click();
    await expect(page).toHaveURL(/\/contracts/, { timeout: 10_000 });
    await page.waitForLoadState('networkidle');
  });

  test('navigate to SKU via sidebar', async ({ page }) => {
    await page.locator('.ant-menu-item a[href="/sku"]').click();
    await expect(page).toHaveURL(/\/sku/, { timeout: 10_000 });
    await page.waitForLoadState('networkidle');
  });

  test('navigate to Suppliers via sidebar', async ({ page }) => {
    await page.locator('.ant-menu-item a[href="/suppliers"]').click();
    await expect(page).toHaveURL(/\/suppliers/, { timeout: 10_000 });
    await page.waitForLoadState('networkidle');
  });

  test('navigate to Items via sidebar', async ({ page }) => {
    await page.locator('.ant-menu-item a[href="/items"]').click();
    await expect(page).toHaveURL(/\/items/, { timeout: 10_000 });
    await page.waitForLoadState('networkidle');
  });

  test('navigate to RFQs via sidebar', async ({ page }) => {
    await page.locator('.ant-menu-item a[href="/rfqs"]').click();
    await expect(page).toHaveURL(/\/rfqs/, { timeout: 10_000 });
    await page.waitForLoadState('networkidle');
  });

  test('navigate to Invoices via sidebar', async ({ page }) => {
    await page.locator('.ant-menu-item a[href="/invoices"]').click();
    await expect(page).toHaveURL(/\/invoices/, { timeout: 10_000 });
    await page.waitForLoadState('networkidle');
  });

  test('navigate to Shipments via sidebar', async ({ page }) => {
    await page.locator('.ant-menu-item a[href="/shipments"]').click();
    await expect(page).toHaveURL(/\/shipments/, { timeout: 10_000 });
    await page.waitForLoadState('networkidle');
  });

  test('navigate to Payments via sidebar', async ({ page }) => {
    await page.locator('.ant-menu-item a[href="/payments"]').click();
    await expect(page).toHaveURL(/\/payments/, { timeout: 10_000 });
    await page.waitForLoadState('networkidle');
  });

  test('logo click navigates to dashboard', async ({ page }) => {
    // Navigate to some other page first
    await page.locator('.ant-menu-item a[href="/purchase-orders"]').click();
    await page.waitForURL(/\/purchase-orders/, { timeout: 10_000 });

    // Click the logo
    await page.locator('.header-logo a').click();

    // Should navigate back to dashboard
    await expect(page).toHaveURL(/\/dashboard/, { timeout: 10_000 });
  });

  test('footer shows version info', async ({ page }) => {
    // Footer should be visible with version info
    const footer = page.locator('footer');
    await expect(footer).toBeVisible({ timeout: 10_000 });
    await expect(footer).toContainText('Mica');
  });
});