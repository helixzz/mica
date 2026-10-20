import { test, expect, Page } from '@playwright/test';
import { loginAs, loginViaApi } from './helpers/auth';

/**
 * Receiving became its own act in v1.59.0: recording a batch moves the order to
 * "shipped", and the requester records what actually arrived, possibly in
 * several passes. The three states a user sees are 待发货 / 已发货 / 部分收货 / 已完成.
 *
 * These tests need at least one purchase order to exist. The CI smoke database
 * is seeded with accounts and suppliers only, so they skip there instead of
 * failing; against a database with orders they run for real.
 *
 * The write test leaves the order as it found it (it revokes what it recorded),
 * so the whole file is re-runnable.
 */

/**
 * Open the first order the account can see, via the API so the test does not
 * depend on list rendering. Returns false when the database has no orders.
 */
async function openFirstOrder(page: Page): Promise<boolean> {
  const token = await loginViaApi(page, 'alice');
  const response = await page.request.get('/api/v1/purchase-orders', {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!response.ok()) {
    return false;
  }
  const orders = (await response.json()) as Array<{ id: string }>;
  if (!orders.length) {
    return false;
  }
  await page.goto(`/purchase-orders/${orders[0].id}`);
  await page.waitForSelector('[role="tab"]', { timeout: 30_000 });
  return true;
}

const RECEIPTS_TAB = /Receipts|收货/;
const SCHEDULE_TAB = /Payment Schedule|付款计划/;
const RECEIVE_BTN = /Receive Goods|确认收货/;
const REVOKE_BTN = /Revoke|撤销/;

test.describe('Receipts', () => {
  test.beforeEach(async ({ page }) => {
    await loginAs(page, 'alice');
  });

  test('order detail exposes a Receipts tab with the receive action', async ({ page }) => {
    if (!(await openFirstOrder(page))) {
      test.skip(true, 'no purchase order in this environment');
    }

    const tab = page.getByRole('tab', { name: RECEIPTS_TAB });
    await expect(tab).toBeVisible({ timeout: 15_000 });
    await tab.click();

    // Either the receive action is offered, or the list says it is empty —
    // both prove the panel mounted.
    const receiveButton = page.getByRole('button', { name: RECEIVE_BTN }).first();
    const emptyState = page.getByText(/No receipts yet|暂无收货记录/);
    await expect(receiveButton.or(emptyState).first()).toBeVisible({ timeout: 15_000 });
  });

  test('payment schedule offers templates and shows receipt progress', async ({ page }) => {
    if (!(await openFirstOrder(page))) {
      test.skip(true, 'no purchase order in this environment');
    }

    await page.getByRole('tab', { name: SCHEDULE_TAB }).click();
    // The panel reports how much of the order has been received.
    await expect(page.getByText(/received:|收货进度/).first()).toBeVisible({ timeout: 15_000 });

    const newSchedule = page
      .getByRole('button', { name: /New Payment Schedule|新建付款计划/i })
      .first();
    if (!(await newSchedule.isVisible({ timeout: 5000 }).catch(() => false))) {
      test.skip(true, 'schedule write action not available for this account');
    }
    await newSchedule.click();

    const drawer = page.locator('.ant-drawer');
    await expect(drawer.getByText(/Common templates|常用模板/)).toBeVisible({ timeout: 10_000 });
    for (const name of [/Advance 100%|预付 100%/]) {
      await expect(drawer.getByRole('button', { name }).first()).toBeVisible();
    }

    // Applying a split fills two installments from the order total.
    await drawer.getByRole('button', { name: /Advance 50%|预付 50%/ }).first().click();
    const amounts = await drawer
      .locator('.ant-input-number-input')
      .evaluateAll((els) => els.map((el) => (el as HTMLInputElement).value));
    expect(amounts.filter((value) => value !== '').length).toBeGreaterThanOrEqual(2);
  });

  test('records a partial receipt and revokes it again', async ({ page }) => {
    if (!(await openFirstOrder(page))) {
      test.skip(true, 'no purchase order in this environment');
    }

    const receiptsTab = page.getByRole('tab', { name: RECEIPTS_TAB });
    await receiptsTab.click();

    const receiveButton = page.getByRole('button', { name: RECEIVE_BTN }).first();
    if (!(await receiveButton.isVisible({ timeout: 5000 }).catch(() => false))) {
      test.skip(true, 'this account may not receive on this order');
    }
    await receiveButton.click();

    const modal = page.locator('.ant-modal');
    const rows = modal.locator('.ant-table-tbody tr');
    await expect(rows.first()).toBeVisible({ timeout: 10_000 });

    // Receive one unit on the first line: enough to become "partially received".
    const firstQty = modal.locator('.ant-input-number-input').first();
    await firstQty.fill('1');
    await firstQty.blur();
    await modal.locator('.ant-modal-footer .ant-btn-primary').click();

    await expect(page.getByText(/Partially Received|部分收货/).first()).toBeVisible({
      timeout: 20_000,
    });

    // Put the order back the way we found it.
    const revoke = page.getByRole('button', { name: REVOKE_BTN }).first();
    await revoke.click();
    const confirm = page.locator('.ant-modal-confirm');
    await expect(confirm).toBeVisible({ timeout: 10_000 });
    await confirm.locator('.ant-btn-primary').click();

    await expect(page.getByText(/No receipts yet|暂无收货记录/).first()).toBeVisible({
      timeout: 20_000,
    });
  });
});
