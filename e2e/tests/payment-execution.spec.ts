import { test, expect } from '@playwright/test';

import { loginAs, loginViaApi } from './helpers/auth';

/**
 * Executing a payment, invoice-first.
 *
 * This is the flow that broke in production: the supplier lookup only ran on the
 * order path, so invoice-first payments failed with a missing-supplier error. A
 * regression test is the least this deserves.
 *
 * Needs ../seed_data.py (an order with a payment schedule).
 */

async function seededPurchaseOrder(page: Parameters<typeof loginViaApi>[0]) {
  const token = await loginViaApi(page, 'alice');
  const response = await page.request.get('/api/v1/purchase-orders?page_size=50', {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!response.ok()) return null;
  const body = (await response.json()) as {
    items?: Array<{ id: string; po_number: string; currency?: string }>;
  };
  const rows = body.items ?? (body as unknown as Array<{ id: string; po_number: string }>);
  return rows.find((row) => row.po_number === 'PO-2026-0005') ?? null;
}

test.describe('Executing a payment', () => {
  test('invoice-first files the invoice and closes the dialog', async ({ page }) => {
    await loginAs(page, 'alice');
    const order = await seededPurchaseOrder(page);
    test.skip(!order, 'seed data missing (run e2e/seed_data.py)');

    await page.goto(`/purchase-orders/${order!.id}`);
    await page.waitForSelector('[role="tab"]', { timeout: 30_000 });
    await page.getByRole('tab', { name: /Payment Schedule|付款计划/ }).click();
    await page.waitForTimeout(1200);

    const execute = page.getByRole('button', { name: /Execute|执行/ }).first();
    test.skip(
      !(await execute.isVisible({ timeout: 8_000 }).catch(() => false)),
      'no pending instalment to execute',
    );
    await execute.click();

    const dialog = page.locator('.ant-modal');
    await expect(dialog).toBeVisible({ timeout: 15_000 });

    // Invoice first, then attach the document and its number.
    await dialog.locator('.ant-radio-button-wrapper', { hasText: /先票|Invoice first/ }).click();
    await dialog.locator('input[type="file"]').setInputFiles('/tmp/e2e-invoice.png');
    await page.waitForTimeout(800);

    const textInputs = dialog.locator('input.ant-input:not([type="file"])');
    if (await textInputs.count()) await textInputs.nth(0).fill('E2E-INV-0001');
    const numberInputs = dialog.locator('.ant-input-number-input');
    if (await numberInputs.count()) await numberInputs.nth(0).fill('400');

    await dialog.locator('.ant-modal-footer .ant-btn-primary').click();
    await page.waitForTimeout(6000);

    // The regression showed a supplier error; make that explicit rather than relying
    // on the dialog merely disappearing.
    const bodyText = await page.locator('body').innerText();
    expect(bodyText).not.toMatch(/缺少供应商|supplier_missing/);
    await expect(dialog).toBeHidden({ timeout: 20_000 });
  });
});
