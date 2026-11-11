import { expect, test } from '@playwright/test';
import { loginViaToken } from './helpers/auth';

const pendingTask = {
  id: 'task-i18n-1',
  instance_id: 'instance-i18n-1',
  stage_order: 1,
  stage_name: '部门负责人审批',
  assignee_id: 'user-1',
  assignee_role: null,
  status: 'pending',
  action: null,
  comment: null,
  assigned_at: new Date(Date.now() - 2.5 * 3_600_000).toISOString(),
  acted_at: null,
  biz_id: 'pr-i18n-1',
  biz_number: 'PR-2026-I18N',
  biz_title: 'Locale interpolation regression',
  biz_amount: 0,
  submitter_name: 'Dennis Cai',
};

for (const { locale, waitingPattern } of [
  { locale: 'zh-CN', waitingPattern: /^已等待 \d+\.\d 小时$/ },
  { locale: 'en-US', waitingPattern: /^Waiting \d+\.\dh$/ },
]) {
  test(`approval waiting time interpolates in ${locale}`, async ({ page }) => {
    await page.addInitScript((language) => {
      localStorage.setItem('mica.locale', language);
    }, locale);
    await page.route('**/api/v1/approval/pending*', async (route) => {
      await route.fulfill({ json: [pendingTask] });
    });
    await loginViaToken(page, 'admin');

    await page.goto('/approvals?task=task-i18n-1');

    await expect(page.getByRole('dialog')).toBeVisible();
    await expect(page.getByText(waitingPattern)).toBeVisible();
    await expect(page.getByRole('dialog')).not.toContainText('{hours}');
  });
}

test('item list includes the returned total', async ({ page }) => {
  await page.addInitScript(() => {
    localStorage.setItem('mica.locale', 'zh-CN');
  });
  await page.route('**/api/v1/items?*', async (route) => {
    await route.fulfill({
      json: { items: [], total: 37, page: 1, page_size: 50 },
    });
  });
  await loginViaToken(page, 'admin');

  await page.goto('/items');

  await expect(page.getByText('共 37 条', { exact: true })).toBeVisible();
});
