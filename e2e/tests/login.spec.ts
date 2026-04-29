import { test, expect } from '@playwright/test';
import { loginAs, TEST_ACCOUNTS } from './helpers/auth';

test.describe('Login Flow', () => {
  test('successful login with valid credentials redirects to dashboard', async ({ page }) => {
    await loginAs(page, 'admin');

    // Verify we are on the dashboard
    await expect(page).toHaveURL(/\/dashboard/);

    // Verify the header shows the user is logged in
    await expect(page.locator('.user-name')).toContainText('管理员 Admin');
  });

  test('successful login as alice (it_buyer)', async ({ page }) => {
    await loginAs(page, 'alice');

    await expect(page).toHaveURL(/\/dashboard/);
    await expect(page.locator('.user-name')).toContainText('Alice');
  });

  test('successful login as bob (dept_manager)', async ({ page }) => {
    await loginAs(page, 'bob');

    await expect(page).toHaveURL(/\/dashboard/);
    await expect(page.locator('.user-name')).toContainText('Bob');
  });

  test('login failure with invalid password shows error', async ({ page }) => {
    await page.goto('/login');
    await page.waitForLoadState('networkidle');

    // If SSO screen is shown, switch to local login
    const localLoginLink = page.getByText(/local account|本地账号/i);
    if (await localLoginLink.isVisible({ timeout: 2000 }).catch(() => false)) {
      await localLoginLink.click();
      await page.waitForTimeout(500);
    }

    // Fill with wrong password
    await page.getByLabel(/username|用户名/i).fill('admin');
    await page.getByLabel(/password|密码/i).fill('WrongPassword123!');

    // Submit
    await page.getByRole('button', { name: /submit|提交|sign in|登录/i }).click();

    // Should show an error alert (Ant Design Alert component)
    await expect(page.locator('.ant-alert-error')).toBeVisible({ timeout: 10_000 });

    // Should still be on the login page
    await expect(page).toHaveURL(/\/login/);
  });

  test('login failure with non-existent user shows error', async ({ page }) => {
    await page.goto('/login');
    await page.waitForLoadState('networkidle');

    const localLoginLink = page.getByText(/local account|本地账号/i);
    if (await localLoginLink.isVisible({ timeout: 2000 }).catch(() => false)) {
      await localLoginLink.click();
      await page.waitForTimeout(500);
    }

    await page.getByLabel(/username|用户名/i).fill('nonexistent_user');
    await page.getByLabel(/password|密码/i).fill(TEST_ACCOUNTS.admin.password);

    await page.getByRole('button', { name: /submit|提交|sign in|登录/i }).click();

    await expect(page.locator('.ant-alert-error')).toBeVisible({ timeout: 10_000 });
    await expect(page).toHaveURL(/\/login/);
  });

  test('logout redirects to login page', async ({ page }) => {
    await loginAs(page, 'admin');

    await page.locator('.user-dropdown').click();
    await page.waitForSelector('.ant-dropdown-menu', { timeout: 5_000 });
    await page.locator('.ant-dropdown-menu-item').filter({ hasText: /log out|退出登录/i }).click();

    await expect(page).toHaveURL(/\/login/, { timeout: 10_000 });
  });

  test('protected routes redirect to login when not authenticated', async ({ page }) => {
    await page.goto('/dashboard');
    await page.waitForLoadState('networkidle');

    // Should be redirected to login
    await expect(page).toHaveURL(/\/login/);
  });
});