import { test, expect } from '@playwright/test';

test.describe('PRD 7.1 First-Run Journey [MVP Acceptance Journey]', () => {
  test('Complete first-run journey from login through alert acknowledgement and maintenance record', async ({ page }) => {
    // 1. Visit root URL -> redirects to login page
    await page.goto('/');

    // 2. Perform Engineer Login
    // Expect login title or direct button
    const directLoginBtn = page.getByRole('button', { name: /Sign In as Reliability Engineer/i });
    if (await directLoginBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
      await directLoginBtn.click();
    } else {
      await page.fill('input[type="email"]', 'engineer@predicore.internal');
      await page.fill('input[type="password"]', 'EngineerSecurePass123!');
      await page.getByRole('button', { name: /Sign In to Workstation/i }).click();
    }

    // 3. Verify Arrival at Fleet Dashboard
    await expect(page.getByText(/Fleet Condition & Risk Overview/i)).toBeVisible({ timeout: 10000 });
    await expect(page.getByText(/NASA C-MAPSS FD001/i).first()).toBeVisible();

    // 4. Select the Critical Machine (ENGINE-048) from the ranking table
    const criticalRow = page.locator('tr').filter({ hasText: 'ENGINE-048' });
    await expect(criticalRow).toBeVisible();
    await criticalRow.click();

    // 5. Verify Machine Detail Page loaded
    await expect(page.getByText('ENGINE-048')).toBeVisible({ timeout: 5000 });

    // 6. Step: View Sensor History (Multivariate Telemetry)
    await expect(page.getByText(/Time-Series Multivariate Telemetry/i)).toBeVisible();

    // 7. Step: View Failure Risk & Anomaly Severity
    await expect(page.getByText(/Failure Probability \(Calibrated\)/i)).toBeVisible();
    await expect(page.getByText(/Anomaly Severity/i)).toBeVisible();

    // 8. Step: View Explanation (Tree SHAP)
    await expect(page.getByText(/AI Engineering Analysis & Explainability/i)).toBeVisible();

    // 9. Step: View Alert & Maintenance Recommendation
    await expect(page.getByText(/AI Recommendation \(Decision Support\)/i)).toBeVisible();
    await expect(page.getByText(/AI-generated recommendation, not a confirmed diagnosis/i)).toBeVisible();

    // 10. Step: Acknowledge Alert (open -> acknowledged)
    const ackBtn = page.getByRole('button', { name: /Acknowledge Alert/i });
    await expect(ackBtn).toBeVisible();
    await ackBtn.click();

    // Verify acknowledgement transition
    await expect(page.getByText(/Acknowledged by/i)).toBeVisible({ timeout: 5000 });

    // 11. Step: Record Maintenance Action
    const recordBtn = page.getByRole('button', { name: /Record Work/i }).or(
      page.getByRole('button', { name: /Record Maintenance Action/i })
    ).first();
    await expect(recordBtn).toBeVisible();
    await recordBtn.click();

    // Verify Modal opens
    await expect(page.getByText(/Log Physical Maintenance Action/i).or(page.getByRole('dialog'))).toBeVisible();

    // Fill and submit maintenance action
    const submitBtn = page.getByRole('button', { name: /Commit & Log Maintenance Action/i }).or(
      page.getByRole('button', { name: /Submit/i })
    );
    await submitBtn.click();

    // 12. Verify Modal closes and Maintenance Action is logged
    await expect(page.getByText(/Engineer Decision & Maintenance Action/i)).toBeVisible();
    await expect(page.getByText(/Records Logged/i)).toBeVisible();
  });
});
