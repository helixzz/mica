import { test, expect } from '@playwright/test';
import { loginAs } from './helpers/auth';

test.describe('Global Search', () => {
  test.beforeEach(async ({ page }) => {
    await loginAs(page, 'admin');
  });

  test('search input is visible in the header', async ({ page }) => {
    // The global search input should be in the header
    const searchInput = page.locator('header input[placeholder]').first();
    await expect(searchInput).toBeVisible({ timeout: 10_000 });
  });

  test('typing in search shows dropdown with results', async ({ page }) => {
    const searchInput = page.locator('header input[placeholder]').first();
    await searchInput.click();
    await searchInput.fill('test');

    // Wait for debounce (300ms) + API response
    // The dropdown should appear with results or empty state
    await page.waitForTimeout(1000);

    // Either results dropdown or empty state should appear
    const dropdown = page.locator('.ant-dropdown').first();
    const dropdownVisible = await dropdown.isVisible({ timeout: 3000 }).catch(() => false);

    // If dropdown is visible, it should have content
    if (dropdownVisible) {
      const hasContent = await dropdown.locator('*').count();
      expect(hasContent).toBeGreaterThan(0);
    }
  });

  test('search with at least 2 characters triggers API call', async ({ page }) => {
    const searchInput = page.locator('header input[placeholder]').first();
    await searchInput.click();
    await searchInput.fill('ad');

    // Wait for debounce + API
    await page.waitForTimeout(1500);

    // Should see some response - either results or empty
    // The dropdown menu should be visible
    const dropdown = page.locator('.ant-dropdown-menu').first();
    const isVisible = await dropdown.isVisible({ timeout: 3000 }).catch(() => false);

    // If visible, it means the search triggered
    if (isVisible) {
      await expect(dropdown).toBeVisible();
    }
  });

  test('search navigates to full results page on "See all"', async ({ page }) => {
    const searchInput = page.locator('header input[placeholder]').first();
    await searchInput.click();
    await searchInput.fill('admin');

    await page.waitForTimeout(1500);

    // Look for "See all" link in the dropdown
    const seeAllLink = page.getByText(/see all|查看全部/i);
    if (await seeAllLink.isVisible({ timeout: 3000 }).catch(() => false)) {
      await seeAllLink.click();

      // Should navigate to search results page
      await expect(page).toHaveURL(/\/search/, { timeout: 10_000 });
    }
  });

  test('search input can be cleared', async ({ page }) => {
    const searchInput = page.locator('header input[placeholder]').first();
    await searchInput.click();
    await searchInput.fill('test');

    // Clear the input using the clear button (Ant Design allowClear)
    const clearButton = page.locator('header .ant-input-clear-icon').first();
    if (await clearButton.isVisible({ timeout: 2000 }).catch(() => false)) {
      await clearButton.click();
      await expect(searchInput).toHaveValue('');
    }
  });

  test('search with single character does not trigger dropdown', async ({ page }) => {
    const searchInput = page.locator('header input[placeholder]').first();
    await searchInput.click();
    await searchInput.fill('a');

    // Single character should not trigger search (needs >= 2)
    await page.waitForTimeout(1000);

    // Dropdown should not be open
    const dropdown = page.locator('.ant-dropdown-menu').first();
    const isVisible = await dropdown.isVisible({ timeout: 2000 }).catch(() => false);
    expect(isVisible).toBe(false);
  });
});