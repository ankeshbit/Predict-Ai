import { test, expect } from '@playwright/test';

/**
 * Live Demo Replay (Simulated Stream) Playwright Test.
 *
 * Verifies admin-only autonomous server-side simulated stream:
 * 1. Admin login via typed credentials from environment variables (no hardcoded credentials).
 * 2. Dashboard displays "Demo replay (simulated stream)" banner.
 * 3. Click "Start Replay" ONCE.
 * 4. Status badge becomes STREAMING.
 * 5. Assert the displayed cycle or health value changes AT LEAST TWICE with NO further clicks
 *    (proving real server-side background worker streaming).
 * 6. Click "Stop Replay".
 * 7. Status badge becomes STOPPED.
 * 8. Assert the value stops changing.
 *
 * Every step uses hard assertions (zero conditionals).
 */
test.describe('Live Demo Replay (Simulated Stream) Workflow', () => {
  test.setTimeout(90000);

  test.beforeEach(async ({ request }) => {
    const adminEmail = process.env.E2E_ADMIN_EMAIL;
    if (!adminEmail) {
      throw new Error('E2E_ADMIN_EMAIL must be configured and non-empty.');
    }
    const adminPassword = process.env.E2E_ADMIN_PASSWORD;
    if (!adminPassword) {
      throw new Error('E2E_ADMIN_PASSWORD must be configured and non-empty.');
    }

    // Reset demo fleet via admin endpoint to ensure pristine baseline
    const loginRes = await request.post('/api/v1/auth/login', {
      data: {
        email: adminEmail,
        password: adminPassword,
      },
    });
    expect(loginRes.ok()).toBeTruthy();
    const { access_token } = await loginRes.json();
    const resetRes = await request.post('/api/v1/demo/reset', {
      headers: { Authorization: `Bearer ${access_token}` },
    });
    expect(resetRes.ok()).toBeTruthy();
  });

  test('Start replay once → stream advances autonomously at least twice → stop → stream stops', async ({ page }) => {
    // 1. Visit root URL → redirects to login page
    await page.goto('/');

    // 2. Sign In as Administrator using typed credentials from environment
    const adminEmail = process.env.E2E_ADMIN_EMAIL;
    if (!adminEmail) {
      throw new Error('E2E_ADMIN_EMAIL must be configured and non-empty.');
    }
    const adminPassword = process.env.E2E_ADMIN_PASSWORD;
    if (!adminPassword) {
      throw new Error('E2E_ADMIN_PASSWORD must be configured and non-empty.');
    }

    const emailInput = page.getByRole('textbox', { name: /Operator Identity \/ Email/i });
    const passwordInput = page.locator('input[type="password"]');
    await expect(emailInput).toBeVisible({ timeout: 8000 });
    await emailInput.fill(adminEmail);
    await passwordInput.fill(adminPassword);
    await page.getByRole('button', { name: /Sign In to Workstation/i }).click();

    // 3. Confirm Fleet Overview loaded and Demo Replay banner is visible
    await expect(page.getByText(/Fleet Condition & Risk Overview/i)).toBeVisible({ timeout: 12000 });
    await expect(page.getByText(/Demo replay \(simulated stream\)/i)).toBeVisible({ timeout: 8000 });

    // 4. Initial state: replay is stopped, start replay button is visible
    const startBtn = page.getByTestId('start-replay-btn');
    await expect(startBtn).toBeVisible({ timeout: 5000 });

    const statusBadge = page.getByTestId('replay-status-badge');
    await expect(statusBadge).toHaveText(/stopped/i, { timeout: 5000 });

    // Read initial cycle from active advancing demo machine (ENGINE-070)
    const machineRow = page.locator('tr').filter({ hasText: 'ENGINE-070' });
    await expect(machineRow).toBeVisible({ timeout: 8000 });
    const cycleCell = machineRow.getByTestId('machine-cycle-cell');
    await expect(cycleCell).toBeVisible({ timeout: 5000 });
    const initialCycle = await cycleCell.innerText();
    expect(initialCycle.length).toBeGreaterThan(0);

    // 5. Click "Start Replay" ONCE (hard assert)
    await startBtn.click();

    // 6. Hard assert: streaming badge is displayed
    await expect(statusBadge).toHaveText(/streaming/i, { timeout: 8000 });
    const stopBtn = page.getByTestId('stop-replay-btn');
    await expect(stopBtn).toBeVisible({ timeout: 8000 });

    // 7. Assert that the displayed cycle value changes AT LEAST TWICE with NO further clicks
    // First advance:
    await expect.poll(async () => await cycleCell.innerText(), {
      timeout: 40000,
      intervals: [1000],
    }).not.toBe(initialCycle);
    const secondCycle = await cycleCell.innerText();
    expect(secondCycle).not.toBe(initialCycle);

    // Second advance:
    await expect.poll(async () => await cycleCell.innerText(), {
      timeout: 40000,
      intervals: [1000],
    }).not.toBe(secondCycle);
    const thirdCycle = await cycleCell.innerText();
    expect(thirdCycle).not.toBe(secondCycle);

    // 8. Stop replay (hard assert)
    await stopBtn.click();

    // 9. Hard assert: status transitions back to stopped
    await expect(statusBadge).toHaveText(/stopped/i, { timeout: 8000 });
    await expect(startBtn).toBeVisible({ timeout: 8000 });

    // 10. Assert cycle value stops changing
    const stoppedCycle = await cycleCell.innerText();
    await page.waitForTimeout(6000);
    const postStopCycle = await cycleCell.innerText();
    expect(postStopCycle).toBe(stoppedCycle);
  });
});
