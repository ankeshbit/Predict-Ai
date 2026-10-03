import { test, expect } from '@playwright/test';

/**
 * PRD 7.1 First-Run Journey — MVP Acceptance Journey
 *
 * This test asserts the complete engineer workflow with NO conditional steps:
 *   login → fleet dashboard → critical machine → alert (open) →
 *   acknowledge (open→acknowledged) → maintenance record (acknowledged→resolved) →
 *   machine returns to 'active'.
 *
 * Every step is a hard assertion. The test FAILS if any step is missing.
 */
test.describe('PRD 7.1 First-Run Journey [MVP Acceptance Journey]', () => {
  test.beforeEach(async ({ request }) => {
    // Reset demo fleet via admin endpoint to ensure pristine baseline for every run
    const loginRes = await request.post('/api/v1/auth/login', {
      data: {
        email: 'admin@predicore.internal',
        password: 'AdminSecret123!',
      },
    });
    if (loginRes.ok()) {
      const { access_token } = await loginRes.json();
      const resetRes = await request.post('/api/v1/demo/reset', {
        headers: { Authorization: `Bearer ${access_token}` },
      });
      expect(resetRes.ok()).toBeTruthy();
    } else {
      throw new Error(`Admin login failed: ${loginRes.status()}`);
    }
  });

  test('Complete first-run journey: login → alert open→acknowledged→resolved → maintenance record → machine active', async ({ page }) => {
    // ── 1. Visit root URL → redirects to login page ────────────────────────
    await page.goto('/');

    // ── 2. Engineer Login ────────────────────────────────────────────────────
    // Use the demo quick-login button; this is the only supported Playwright entry point.
    const quickLoginBtn = page.getByRole('button', { name: /Sign In as Reliability Engineer/i });
    await expect(quickLoginBtn).toBeVisible({ timeout: 8000 });
    await quickLoginBtn.click();

    // ── 3. Fleet Dashboard ───────────────────────────────────────────────────
    await expect(page.getByText(/Fleet Condition & Risk Overview/i)).toBeVisible({ timeout: 12000 });
    // PRD §1.1 mandatory banner
    await expect(page.getByText(/NASA C-MAPSS FD001/i).first()).toBeVisible();

    // ── 4. Select Critical Machine (ENGINE-048) ──────────────────────────────
    const criticalRow = page.locator('tr').filter({ hasText: 'ENGINE-048' });
    await expect(criticalRow).toBeVisible({ timeout: 8000 });
    await criticalRow.click();

    // ── 5. Machine Detail Page loaded ────────────────────────────────────────
    await expect(page.getByText('ENGINE-048').first()).toBeVisible({ timeout: 8000 });

    // ── 6. Sensor Telemetry panel ────────────────────────────────────────────
    await expect(page.getByText(/Time-Series Multivariate Telemetry/i)).toBeVisible();

    // ── 7. Failure Probability & Anomaly Severity panels ────────────────────
    await expect(page.getByText(/Failure Probability \(Calibrated\)/i)).toBeVisible();
    await expect(page.getByText(/Anomaly Severity/i)).toBeVisible();

    // ── 8. SHAP / Explainability panel ───────────────────────────────────────
    await expect(page.getByText(/AI Engineering Analysis & Explainability/i)).toBeVisible();

    // ── 9. AI Recommendation panel with mandatory disclaimer ─────────────────
    await expect(page.getByText(/AI Recommendation \(Decision Support\)/i)).toBeVisible();
    await expect(page.getByText(/AI-generated recommendation, not a confirmed diagnosis/i)).toBeVisible();

    // ── 10. Alert must be OPEN (hard assert — test fails if alert never fires) ─
    const openAlertBadge = page.getByTestId('alert-status-open');
    await expect(openAlertBadge).toBeVisible({ timeout: 8000 });
    const ackBtn = page.getByRole('button', { name: /Acknowledge Alert/i });
    await expect(ackBtn).toBeVisible({ timeout: 8000 });

    // ── 11. Acknowledge → status transitions to 'acknowledged' ───────────────
    await ackBtn.click();
    const ackAlertBadge = page.getByTestId('alert-status-acknowledged');
    await expect(ackAlertBadge).toBeVisible({ timeout: 8000 });
    await expect(page.getByText(/Acknowledged by/i)).toBeVisible({ timeout: 8000 });
    await expect(ackBtn).not.toBeVisible({ timeout: 4000 });

    // ── 12. Record Maintenance Action ────────────────────────────────────────
    const recordBtn = page.getByTestId('record-work-btn');
    await expect(recordBtn).toBeVisible({ timeout: 8000 });
    await recordBtn.click();

    // Modal must open.
    await expect(page.getByText(/Record Engineer Intervention/i)).toBeVisible({ timeout: 6000 });

    // ── 13. Submit maintenance record (resolve) — hard assert, NO conditionals ─
    const outcomeSelect = page.getByTestId('outcome-select');
    await expect(outcomeSelect).toBeVisible({ timeout: 5000 });
    await outcomeSelect.selectOption('resolved');

    const submitBtn = page.getByTestId('save-maintenance-btn');
    await expect(submitBtn).toBeVisible({ timeout: 4000 });
    await submitBtn.click();

    // ── 14. Hard assert: maintenance record logged ───────────────────────────
    await expect(page.getByText(/Engineer Decision & Maintenance Action/i)).toBeVisible({ timeout: 8000 });
    await expect(page.getByText(/Records Logged/i)).toBeVisible({ timeout: 8000 });

    // ── 15. Alert status is now 'resolved' (hard assert) ─────────────────────
    const resolvedAlertBadge = page.getByTestId('alert-status-resolved');
    await expect(resolvedAlertBadge).toBeVisible({ timeout: 8000 });

    // ── 16. Machine operational status returns to 'active' ───────────────────
    // Navigate back to fleet dashboard and confirm the machine row shows 'active'.
    await page.goto('/');
    await expect(page.getByText(/Fleet Condition & Risk Overview/i)).toBeVisible({ timeout: 10000 });
    // After completing maintenance with outcome 'resolved', the machine must be active.
    const machineRow = page.locator('tr').filter({ hasText: 'ENGINE-048' });
    await expect(machineRow).toBeVisible({ timeout: 8000 });
    await expect(machineRow.getByText(/active/i)).toBeVisible({ timeout: 8000 });
  });
});

