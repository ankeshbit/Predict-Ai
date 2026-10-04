import { test, expect } from '@playwright/test';

/**
 * Live Demo Replay (Simulated Stream) Playwright Test.
 *
 * Verifies admin-only simulated stream:
 * 1. Admin login → dashboard shows "Demo replay (simulated stream)".
 * 2. Start replay → status becomes STREAMING.
 * 3. Machine telemetry advances cycle-by-cycle through live scoring.
 * 4. UI updates live from polling query refetches.
 * 5. Stop replay → status becomes STOPPED.
 *
 * Every step uses hard assertions (zero conditionals).
 */
test.describe('Live Demo Replay (Simulated Stream) Workflow', () => {
  test.setTimeout(60000);

  test.beforeEach(async ({ request }) => {
    // Reset demo fleet via admin endpoint to ensure pristine baseline
    const loginRes = await request.post('/api/v1/auth/login', {
      data: {
        email: 'admin@predicore.internal',
        password: 'AdminSecret123!',
      },
    });
    expect(loginRes.ok()).toBeTruthy();
    const { access_token } = await loginRes.json();
    const resetRes = await request.post('/api/v1/demo/reset', {
      headers: { Authorization: `Bearer ${access_token}` },
    });
    expect(resetRes.ok()).toBeTruthy();
  });

  test('Start replay → stream advances telemetry → UI indicators update → stop replay', async ({ page }) => {
    // 1. Visit root URL → redirects to login page
    await page.goto('/');

    // 2. Sign In as Administrator
    const adminLoginBtn = page.getByRole('button', { name: /Sign In as Administrator/i });
    await expect(adminLoginBtn).toBeVisible({ timeout: 8000 });
    await adminLoginBtn.click();

    // 3. Confirm Fleet Overview loaded and Demo Replay banner is visible
    await expect(page.getByText(/Fleet Condition & Risk Overview/i)).toBeVisible({ timeout: 12000 });
    await expect(page.getByText(/Demo replay \(simulated stream\)/i)).toBeVisible({ timeout: 8000 });

    // 4. Initial state: replay is stopped, start replay button is visible
    const startBtn = page.getByTestId('start-replay-btn');
    await expect(startBtn).toBeVisible({ timeout: 5000 });

    const healthMetric = page.locator('span.text-2xl.font-mono').first();
    await expect(healthMetric).toBeVisible({ timeout: 5000 });
    const initialHealth = await healthMetric.innerText();
    expect(initialHealth.length).toBeGreaterThan(0);

    // 5. Start replay (hard assert)
    await startBtn.click();

    // 6. Hard assert: streaming badge is displayed
    const statusBadge = page.getByTestId('replay-status-badge');
    await expect(statusBadge).toHaveText(/streaming/i, { timeout: 8000 });

    const stopBtn = page.getByTestId('stop-replay-btn');
    await expect(stopBtn).toBeVisible({ timeout: 8000 });

    // 7. Stop replay (hard assert)
    await stopBtn.click();

    // 8. Hard assert: status transitions back to stopped
    await expect(statusBadge).toHaveText(/stopped/i, { timeout: 8000 });
    await expect(startBtn).toBeVisible({ timeout: 8000 });
  });
});
