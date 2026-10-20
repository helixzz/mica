import { test, expect } from '@playwright/test';
import { loginAs } from './helpers/auth';

/**
 * The header carries a release-history button so people notice that the system
 * is changing without anyone sending an email about it.
 */
test.describe("What's new", () => {
  test.beforeEach(async ({ page }) => {
    await loginAs(page, 'alice');
  });

  test('header button opens the release history', async ({ page }) => {
    const trigger = page.getByRole('button', { name: /See what changed|查看 Mica 的版本更新/ });
    await expect(trigger).toBeVisible({ timeout: 15_000 });
    await trigger.click();

    const drawer = page.locator('.ant-drawer');
    await expect(drawer).toBeVisible({ timeout: 10_000 });

    // Version headings and the category tags that make the list scannable.
    await expect(drawer.getByText(/^v\d+\.\d+\.\d+/).first()).toBeVisible();
    await expect(drawer.getByText(/^(New|新增)$/).first()).toBeVisible();
  });
});
