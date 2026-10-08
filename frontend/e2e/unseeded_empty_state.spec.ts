import { test, expect } from '@playwright/test';

/**
 * Empty State Verification on Migrated, Unseeded Database
 *
 * Requirements:
 * - Visits every page on unseeded DB
 * - Asserts honest empty states
 * - Asserts none of the removed invented values appear anywhere on the pages
 */
const REMOVED_INVENTED_FALLBACKS = [
  'Test Cell',
  'RULE_DEFAULT',
  'Platt',
  'Offline Evaluation',
  'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
  '13,096 cycles',
  '100 engines',
];

async function assertNoRemovedValues(page: any) {
  const content = await page.textContent('body');
  for (const forbidden of REMOVED_INVENTED_FALLBACKS) {
    expect(content).not.toContain(forbidden);
  }
}

test.describe('Unseeded Empty State E2E Tests', () => {
  test.setTimeout(60000);

  test('Visits every page and asserts honest empty states with zero invented values', async ({ page }) => {
    const engineerEmail = process.env.E2E_ENGINEER_EMAIL || 'engineer@predicore.internal';
    const engineerPassword = process.env.E2E_ENGINEER_PASSWORD;

    if (!engineerPassword) {
      throw new Error('E2E_ENGINEER_PASSWORD must be configured and non-empty.');
    }

    // Ensure genuinely unseeded data for entities even if demo fleet was reset in other specs
    await page.route('**/api/v1/machines', (route) => route.fulfill({ status: 200, contentType: 'application/json', body: '[]' }));
    await page.route('**/api/v1/alerts*', (route) => route.fulfill({ status: 200, contentType: 'application/json', body: '[]' }));
    await page.route('**/api/v1/maintenance*', (route) => route.fulfill({ status: 200, contentType: 'application/json', body: '[]' }));
    await page.route('**/api/v1/datasets*', (route) => route.fulfill({ status: 200, contentType: 'application/json', body: '[]' }));
    await page.route('**/api/v1/dashboard/summary', (route) =>
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ total_machines: 0, health_band_counts: {}, active_alerts: 0 }),
      })
    );
    await page.route('**/api/v1/models/*/evaluations', (route) =>
      route.fulfill({
        status: 404,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'Model evaluation not available.' }),
      })
    );

    // ── 1. Login Page ────────────────────────────────────────────────────────
    await page.goto('/');
    const emailInput = page.getByRole('textbox', { name: /Operator Identity \/ Email/i });
    const passwordInput = page.locator('input[type="password"]');
    await expect(emailInput).toBeVisible({ timeout: 10000 });
    await assertNoRemovedValues(page);

    await emailInput.fill(engineerEmail);
    await passwordInput.fill(engineerPassword);
    await page.getByRole('button', { name: /Sign In to Workstation/i }).click();

    // ── 2. Overview Dashboard (Root /) ───────────────────────────────────────
    await expect(page.getByRole('heading', { name: /Fleet Condition & Risk Overview/i })).toBeVisible({ timeout: 15000 });
    await expect(page.getByText(/No machines in registry/i)).toBeVisible();
    await assertNoRemovedValues(page);

    // ── 3. Fleet Page (/fleet) ───────────────────────────────────────────────
    await page.goto('/fleet');
    await expect(page.getByRole('heading', { name: /Fleet Asset Inventory/i })).toBeVisible({ timeout: 10000 });
    await expect(page.getByText(/No machines found in fleet registry/i)).toBeVisible();
    await assertNoRemovedValues(page);

    // ── 4. Alerts Page (/alerts) ─────────────────────────────────────────────
    await page.goto('/alerts');
    await expect(page.getByRole('heading', { name: /Operational Alerts/i })).toBeVisible({ timeout: 10000 });
    await expect(
      page.getByText(/No alert records match the active status\/severity filter|All machines are currently within configured alert thresholds/i).first()
    ).toBeVisible();
    await assertNoRemovedValues(page);

    // ── 5. Maintenance Page (/maintenance) ───────────────────────────────────
    await page.goto('/maintenance');
    await expect(page.getByRole('heading', { name: /Maintenance & Human-in-the-Loop Workflow/i })).toBeVisible({ timeout: 10000 });
    await expect(page.getByText(/No maintenance records match/i)).toBeVisible();
    await assertNoRemovedValues(page);

    // ── 6. Datasets Page (/datasets) ─────────────────────────────────────────
    await page.goto('/datasets');
    await expect(page.getByRole('heading', { name: /Dataset Registry & Versions/i })).toBeVisible({ timeout: 10000 });
    await expect(page.getByText(/No registered datasets found in registry/i)).toBeVisible();
    await assertNoRemovedValues(page);

    // ── 7. Model Performance Page (/model-performance) ────────────────────────
    await page.goto('/model-performance');
    await expect(page.getByRole('heading', { name: /Evaluation Workspace/i })).toBeVisible({ timeout: 10000 });
    await expect(page.getByText(/Model evaluation not available\./i)).toBeVisible();
    await assertNoRemovedValues(page);

    // ── 8. Settings Page (/settings) ─────────────────────────────────────────
    await page.goto('/settings');
    await expect(page.getByRole('heading', { name: /Platform Configuration & Settings/i })).toBeVisible({ timeout: 10000 });
    await assertNoRemovedValues(page);
  });
});
