import { test, expect } from '@playwright/test';

import { loginViaApi, loginViaToken } from './helpers/auth';
import { readSeedManifest } from './helpers/seed';

/**
 * Executing a payment, invoice-first.
 *
 * This is the flow that broke in production: the supplier lookup only ran on the
 * order path, so invoice-first payments failed with a missing-supplier error. A
 * regression test is the least this deserves.
 *
 * Needs ../seed_data.py (an order with a payment schedule).
 */

async function seededPurchaseOrder() {
  const manifest = readSeedManifest();
  if (!manifest) return null;
  return { id: manifest.po_id, po_number: manifest.po_number };
}

/**
 * Put the instalment back to "planned".
 *
 * Executing it is the whole point of the spec, so the spec itself consumes the data
 * it needs — the second run would otherwise find nothing left to execute. The first
 * version of this test only worked once, which is not a test.
 */
async function resetInstalment(page: Parameters<typeof loginViaApi>[0], poId: string) {
  const token = await loginViaApi(page, 'alice');
  const headers = { Authorization: `Bearer ${token}` };
  const due = new Date(Date.now() + 10 * 24 * 3600 * 1000).toISOString().slice(0, 10);
  // Replacing the schedule is a POST with the items wrapped; PUT updates a single
  // instalment by number and silently did nothing here.
  const response = await page.request.post(
    `/api/v1/purchase-orders/${poId}/payment-schedule`,
    {
      headers,
      data: {
        items: [
          { installment_no: 1, label: '预付款', planned_amount: '400', planned_date: due },
        ],
      },
    },
  );
  expect(response.ok(), `schedule reset failed: ${response.status()}`).toBeTruthy();
}

test.describe('Executing a payment', () => {
  // The order page deliberately lists its contracts' instalments as well
  // (see _list_schedules_for_summary), so the dialog may target a contract-owned
  // instalment. Execution has to follow the instalment's owner; this spec is what
  // caught that it did not.
  test('invoice-first files the invoice and closes the dialog', async ({ page }) => {
    const order = await seededPurchaseOrder();
    test.skip(!order, 'seed data missing (run e2e/seed_data.py)');

    await resetInstalment(page, order!.id);
    await loginViaToken(page, 'alice');

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

    // A fixed number makes the second run collide with the first (invoice numbers are
    // unique; the endpoint answers 409), which is what kept this spec red.
    const invoiceNumber = `E2E-${Date.now()}`;
    const textInputs = dialog.locator('input.ant-input:not([type="file"])');
    if (await textInputs.count()) await textInputs.nth(0).fill(invoiceNumber);
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
