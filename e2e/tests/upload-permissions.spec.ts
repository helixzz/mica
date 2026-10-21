import { test, expect } from '@playwright/test';

import { loginAs } from './helpers/auth';
import { readSeedManifest } from './helpers/seed';

/**
 * The upload controls follow the API rule.
 *
 * Attaching a document is restricted to admin / procurement_mgr / it_buyer. When the
 * API was tightened and the buttons were not, a department manager saw the button and
 * got a 403 for pressing it — this is the divergence AGENTS.md §5.15 warns about, so
 * it gets a test rather than a note.
 */

const UPLOAD_LABEL = /上传|Upload/i;

test.describe('Upload controls respect roles', () => {
  test('a procurement role sees the order attachment upload', async ({ page }) => {
    const manifest = readSeedManifest();
    test.skip(!manifest, 'seed data missing (run e2e/seed_data.py)');

    await loginAs(page, 'alice'); // it_buyer
    await page.goto(`/purchase-orders/${manifest!.po_id}`);
    await page.waitForSelector('[role="tab"]', { timeout: 30_000 });

    const attachmentsTab = page.getByRole('tab', { name: /附件|Attachment/i }).first();
    if (!(await attachmentsTab.isVisible({ timeout: 8_000 }).catch(() => false))) {
      test.skip(true, 'no attachment tab for this account');
    }
    await attachmentsTab.click();
    await page.waitForTimeout(1200);

    await expect(page.getByRole('button', { name: UPLOAD_LABEL }).first()).toBeVisible({
      timeout: 15_000,
    });
  });

  test('a non-procurement role does not see it', async ({ page }) => {
    const manifest = readSeedManifest();
    test.skip(!manifest, 'seed data missing (run e2e/seed_data.py)');

    await loginAs(page, 'bob'); // dept_manager
    await page.goto(`/purchase-orders/${manifest!.po_id}`);
    await page.waitForSelector('[role="tab"]', { timeout: 30_000 });

    const attachmentsTab = page.getByRole('tab', { name: /附件|Attachment/i }).first();
    if (!(await attachmentsTab.isVisible({ timeout: 8_000 }).catch(() => false))) {
      test.skip(true, 'no attachment tab for this account');
    }
    await attachmentsTab.click();
    await page.waitForTimeout(1200);

    // Absent, not merely disabled: showing it would earn a 403.
    await expect(page.getByRole('button', { name: UPLOAD_LABEL })).toHaveCount(0);
  });
});
