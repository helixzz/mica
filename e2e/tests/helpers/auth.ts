import { Page, expect } from '@playwright/test';

/**
 * Test account credentials.
 * All seed accounts use the same password: MicaDev2026!
 */
export const TEST_ACCOUNTS = {
  admin: { username: 'admin', password: 'MicaDev2026!', role: 'admin' },
  alice: { username: 'alice', password: 'MicaDev2026!', role: 'it_buyer' },
  bob: { username: 'bob', password: 'MicaDev2026!', role: 'dept_manager' },
  carol: { username: 'carol', password: 'MicaDev2026!', role: 'finance_auditor' },
  dave: { username: 'dave', password: 'MicaDev2026!', role: 'procurement_mgr' },
} as const;

export type TestAccountKey = keyof typeof TEST_ACCOUNTS;

/**
 * Login via the UI login form.
 * Navigates to /login, fills the form, submits, and waits for redirect to /dashboard.
 */
export async function loginAs(page: Page, account: TestAccountKey): Promise<void> {
  const { username, password } = TEST_ACCOUNTS[account];

  await page.goto('/login');
  await page.waitForLoadState('networkidle');

  // The login page may show SSO options first. If local login form is not visible,
  // click the "use local account" link.
  const localLoginLink = page.getByText(/local account|本地账号/i);
  if (await localLoginLink.isVisible({ timeout: 2000 }).catch(() => false)) {
    await localLoginLink.click();
    await page.waitForTimeout(500);
  }

  // Fill in the login form. Ant Design Form.Item labels are used for field identification.
  // The form has label="Username" / "用户名" for username and label="Password" / "密码" for password.
  const usernameInput = page.getByLabel(/username|用户名/i);
  const passwordInput = page.getByLabel(/password|密码/i);

  await usernameInput.fill(username);
  await passwordInput.fill(password);

  // Click the submit button
  const submitButton = page.getByRole('button', { name: /submit|提交|sign in|登录/i });
  await submitButton.click();

  // Wait for navigation to dashboard after successful login
  await page.waitForURL(/\/dashboard/, { timeout: 15_000 });
  await page.waitForLoadState('networkidle');
}

/**
 * Login via the API directly (faster, bypasses UI).
 * Returns the access token.
 */
export async function loginViaApi(page: Page, account: TestAccountKey): Promise<string> {
  const { username, password } = TEST_ACCOUNTS[account];

  const response = await page.request.post('/api/v1/auth/login', {
    form: { username, password },
  });

  expect(response.status()).toBe(200);
  const body = await response.json();
  expect(body.access_token).toBeDefined();

  return body.access_token;
}

/**
 * Set the auth token in localStorage and navigate to a page.
 * This bypasses the login UI for faster test setup.
 */
export async function loginViaToken(page: Page, account: TestAccountKey): Promise<void> {
  const token = await loginViaApi(page, account);

  // Navigate to the app first to set the origin, then inject the token
  await page.goto('/');
  await page.evaluate((t) => {
    localStorage.setItem('auth_token', t);
  }, token);

  // Reload to pick up the token
  await page.goto('/dashboard');
  await page.waitForLoadState('networkidle');
}

/**
 * Logout by clicking the user dropdown and selecting logout.
 */
export async function logout(page: Page): Promise<void> {
  // Click the user dropdown in the header
  const userDropdown = page.locator('.user-dropdown');
  await userDropdown.click();

  // Click logout menu item
  const logoutItem = page.getByText(/logout|退出登录/i);
  await logoutItem.click();

  // Wait for redirect to login page
  await page.waitForURL(/\/login/, { timeout: 10_000 });
}

/**
 * Navigate to a section via the sidebar menu link.
 */
export async function navigateTo(page: Page, path: string): Promise<void> {
  // Click the sidebar link matching the path
  const link = page.locator(`.ant-menu-item a[href="${path}"]`);
  await link.click();
  await page.waitForURL(new RegExp(path.replace('/', '\\/')), { timeout: 10_000 });
  await page.waitForLoadState('networkidle');
}