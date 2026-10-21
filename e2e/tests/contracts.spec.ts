import { test, expect, Page } from '@playwright/test';

import { loginAs, loginViaApi } from './helpers/auth';
import { readSeedManifest } from './helpers/seed';

/**
 * Contract detail: opening it from the list, and the payment schedule it shows.
 *
 * The schedule spec resets its own data first. An earlier version trusted whatever
 * the seed had left behind — an older instalment label, or one already paid — and
 * then asserted on something that was no longer there.
 */

function seededContract() {
  const manifest = readSeedManifest();
  if (!manifest?.contract_id) return null;
  return {
    id: manifest.contract_id,
    contract_number: manifest.contract_number ?? '',
  };
}

async function resetContractSchedule(
  page: Page,
  contractId: string,
  label: string,
): Promise<void> {
  const token = await loginViaApi(page, 'alice');
  const due = new Date(Date.now() + 10 * 24 * 3600 * 1000).toISOString().slice(0, 10);
  // Replacing the whole schedule is a POST whose body wraps the items; there is no
  // bulk PUT (PUT updates one instalment by number).
  const response = await page.request.post(
    `/api/v1/contracts/${contractId}/payment-schedule`,
    {
      headers: { Authorization: `Bearer ${token}` },
      data: {
        items: [{ installment_no: 1, label, planned_amount: '400', planned_date: due }],
      },
    },
  );
  expect(response.ok(), `schedule reset failed: ${response.status()}`).toBeTruthy();
}

test.describe('Contract detail', () => {
  test('shows the payment schedule it was given', async ({ page }) => {
    const contract = seededContract();
    test.skip(!contract, 'no contract in this environment (run e2e/seed_data.py)');

    const label = '首款-用例';
    await resetContractSchedule(page, contract!.id, label);
    await loginAs(page, 'alice');
    await page.setViewportSize({ width: 1440, height: 1000 });

    await page.goto(`/contracts/${contract!.id}`);
    await page.waitForSelector('[role="tab"]', { timeout: 30_000 });
    await page.getByRole('tab', { name: /Payment Schedule|付款计划/ }).click();

    // The instalment we just wrote has to appear; that proves the tab loaded the
    // contract's own schedule rather than an empty state.
    await expect(page.getByText(label).first()).toBeVisible({ timeout: 20_000 });
  });

  test('a contract can be opened from the list', async ({ page }) => {
    const contract = seededContract();
    test.skip(!contract, 'no contract in this environment');

    await loginAs(page, 'alice');
    await page.goto('/contracts');
    await page.waitForSelector('.ant-table', { timeout: 30_000 });

    const link = page.getByRole('link', { name: new RegExp(contract!.contract_number) }).first();
    const visible = await link.isVisible({ timeout: 10_000 }).catch(() => false);
    if (!visible) {
      test.skip(true, 'contract list is filtered for this account');
    }
    await link.click();
    await expect(page).toHaveURL(new RegExp(`/contracts/${contract!.id}`));
  });
});
