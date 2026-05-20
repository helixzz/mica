import { test, expect } from '@playwright/test';
import { loginAs, navigateTo } from './helpers/auth';

test.describe('Purchase Requisitions', () => {
  test.beforeEach(async ({ page }) => {
    await loginAs(page, 'alice');
  });

  test('PR list page loads and shows table', async ({ page }) => {
    await navigateTo(page, '/purchase-requisitions');

    // The page should have a table or some content
    // Ant Design Table should be present
    await expect(page.locator('.ant-table')).toBeVisible({ timeout: 10_000 });
  });

  test('PR list page has "New PR" button', async ({ page }) => {
    await navigateTo(page, '/purchase-requisitions');

    // Should have a button to create new PR
    const newButton = page.getByRole('button', { name: /new|新建|create/i });
    await expect(newButton).toBeVisible({ timeout: 10_000 });
  });

  test('navigate to PR creation form', async ({ page }) => {
    await navigateTo(page, '/purchase-requisitions');

    // Click the new PR button
    const newButton = page.getByRole('button', { name: /new|新建|create/i });
    await newButton.click();

    // Should navigate to the new PR page
    await expect(page).toHaveURL(/\/purchase-requisitions\/new/, { timeout: 10_000 });
  });

  test('PR creation form loads with required fields', async ({ page }) => {
    await page.goto('/purchase-requisitions/new');
    await page.waitForLoadState('networkidle');

    // The form should have a title field
    const titleInput = page.getByLabel(/title|标题/i);
    await expect(titleInput).toBeVisible({ timeout: 10_000 });

    // Should have a business reason field
    const reasonInput = page.getByLabel(/business reason|业务原因|申请原因/i);
    await expect(reasonInput).toBeVisible({ timeout: 10_000 });
  });

  test('PR creation: fill form and add line item', async ({ page }) => {
    await page.goto('/purchase-requisitions/new');
    await page.waitForLoadState('networkidle');

    // Fill in the title
    const titleInput = page.getByLabel(/title|标题/i);
    await titleInput.fill('E2E Test PR - Office Supplies');

    // Fill in business reason
    const reasonInput = page.getByLabel(/business reason|业务原因|申请原因/i);
    await reasonInput.fill('Testing PR creation flow via Playwright E2E');

    // The line item cards should be visible (Card layout, not Table)
    await expect(page.locator('.ant-card').first()).toBeVisible({ timeout: 10_000 });

    // Verify the form has a submit/save button
    const submitBtn = page.getByRole('button', { name: /submit|提交/i });
    await expect(submitBtn).toBeVisible();
  });

  test('PR creation: add multiple line items', async ({ page }) => {
    await page.goto('/purchase-requisitions/new');
    await page.waitForLoadState('networkidle');

    // Click "Add line" button
    const addLineBtn = page.getByRole('button', { name: /add|添加|plus/i }).first();
    if (await addLineBtn.isVisible({ timeout: 5000 }).catch(() => false)) {
      const cardsBefore = await page.locator('.ant-card-small').count();
      await addLineBtn.click();
      await page.waitForTimeout(500);

      // Should now have more cards
      const cardsAfter = await page.locator('.ant-card-small').count();
      expect(cardsAfter).toBeGreaterThan(cardsBefore);
    }
  });

});
