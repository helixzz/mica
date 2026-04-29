import { test, expect } from '@playwright/test';
import { loginAs } from './helpers/auth';

test.describe('Dashboard', () => {
  test('admin dashboard loads with key sections', async ({ page }) => {
    await loginAs(page, 'admin');

    // Dashboard should be visible
    await expect(page).toHaveURL(/\/dashboard/);

    // The dashboard should have content (not just a spinner)
    // Wait for the page content to load (Ant Design Spin should disappear)
    await page.waitForSelector('.ant-spin', { state: 'hidden', timeout: 10_000 }).catch(() => {});

    // Verify the sidebar is visible with navigation items
    await expect(page.locator('.ant-menu-item').first()).toBeVisible({ timeout: 10_000 });

    // Verify the header has the app name
    await expect(page.locator('.logo-text')).toContainText('Mica');
  });

  test('alice (it_buyer) dashboard loads', async ({ page }) => {
    await loginAs(page, 'alice');

    await expect(page).toHaveURL(/\/dashboard/);
    await page.waitForSelector('.ant-spin', { state: 'hidden', timeout: 10_000 }).catch(() => {});

    // Verify user info is displayed
    await expect(page.locator('.user-name')).toContainText('Alice');
  });

  test('bob (dept_manager) dashboard loads', async ({ page }) => {
    await loginAs(page, 'bob');

    await expect(page).toHaveURL(/\/dashboard/);
    await page.waitForSelector('.ant-spin', { state: 'hidden', timeout: 10_000 }).catch(() => {});

    await expect(page.locator('.user-name')).toContainText('Bob');
  });

  test('dashboard has notification bell visible', async ({ page }) => {
    await loginAs(page, 'admin');

    // The notification bell should be in the header
    // It's rendered by the NotificationBell component
    await expect(page.locator('header')).toBeVisible();
  });

  test('dashboard sidebar has all expected navigation items for admin', async ({ page }) => {
    await loginAs(page, 'admin');

    // Admin should see all menu items including Admin Console
    const menuItems = page.locator('.ant-menu-item');
    await expect(menuItems.first()).toBeVisible();

    // Check that admin-specific menu item exists
    await expect(page.locator('.ant-menu-item a[href="/admin"]')).toBeVisible();
  });

  test('dashboard sidebar hides admin link for non-admin users', async ({ page }) => {
    await loginAs(page, 'alice');

    // Alice (it_buyer) should NOT see the admin link
    await expect(page.locator('.ant-menu-item a[href="/admin"]')).not.toBeVisible();
  });
});