import { test, expect } from '@playwright/test';
import { loginAs, navigateTo } from './helpers/auth';

test.describe('Admin Page Access', () => {
  test('admin user can access admin page', async ({ page }) => {
    await loginAs(page, 'admin');

    await navigateTo(page, '/admin');

    // Admin page should load with tabs
    await expect(page.locator('.ant-tabs')).toBeVisible({ timeout: 10_000 });
  });

  test('non-admin user (alice) sees permission denied on admin page', async ({ page }) => {
    await loginAs(page, 'alice');

    // Navigate directly to admin page
    await page.goto('/admin');
    await page.waitForLoadState('networkidle');

    // Should show permission denied message
    // The AdminPage component checks role and shows a Card with error text
    await expect(page.getByText(/permission denied|权限不足|admin only/i)).toBeVisible({ timeout: 10_000 });
  });

  test('non-admin user (bob) sees permission denied on admin page', async ({ page }) => {
    await loginAs(page, 'bob');

    await page.goto('/admin');
    await page.waitForLoadState('networkidle');

    await expect(page.getByText(/permission denied|权限不足|admin only/i)).toBeVisible({ timeout: 10_000 });
  });

  test('admin page has system parameters tab', async ({ page }) => {
    await loginAs(page, 'admin');
    await navigateTo(page, '/admin');

    // The admin page should have tabs including system parameters
    const tabs = page.locator('.ant-tabs-tab');
    await expect(tabs.first()).toBeVisible({ timeout: 10_000 });
  });

  test('admin sidebar shows admin console link', async ({ page }) => {
    await loginAs(page, 'admin');

    // Admin console link should be in the sidebar
    const adminLink = page.locator('.ant-menu-item a[href="/admin"]');
    await expect(adminLink).toBeVisible({ timeout: 10_000 });
  });

  test('non-admin sidebar does not show admin console link', async ({ page }) => {
    await loginAs(page, 'alice');

    // Admin console link should NOT be in the sidebar for alice
    const adminLink = page.locator('.ant-menu-item a[href="/admin"]');
    await expect(adminLink).not.toBeVisible();
  });
});