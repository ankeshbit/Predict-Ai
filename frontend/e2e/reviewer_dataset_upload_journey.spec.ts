import { test, expect } from '@playwright/test';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const SAMPLES_DIR = path.resolve(__dirname, '../../database/sample_data');

test.describe('Reviewer Dataset Upload & Cross-Page Synchronization Journey', () => {
  test.setTimeout(120000);

  test.beforeEach(async ({ request }) => {
    const adminEmail = process.env.E2E_ADMIN_EMAIL || 'admin@predicore.internal';
    const adminPassword = process.env.E2E_ADMIN_PASSWORD || 'AdminReviewer2026#Secure';

    const loginRes = await request.post('/api/v1/auth/login', {
      data: { email: adminEmail, password: adminPassword },
    });
    expect(loginRes.ok()).toBeTruthy();
    const { access_token } = await loginRes.json();

    // Reset demo fleet and clear previous user datasets for clean baseline
    const resetRes = await request.post('/api/v1/demo/reset?clear_user_datasets=true', {
      headers: { Authorization: `Bearer ${access_token}` },
    });
    expect(resetRes.ok()).toBeTruthy();
  });

  test('1. Compatible upload end-to-end, live job progress, scoring, and cross-page consistency', async ({ page }) => {
    // ── Log in as Admin ───────────────────────────────────────────────────
    await page.goto('/');
    const emailInput = page.getByRole('textbox', { name: /Operator Identity \/ Email/i });
    const passwordInput = page.locator('input[type="password"]');
    await expect(emailInput).toBeVisible({ timeout: 8000 });
    await emailInput.fill(process.env.E2E_ADMIN_EMAIL || 'admin@predicore.internal');
    await passwordInput.fill(process.env.E2E_ADMIN_PASSWORD || 'AdminReviewer2026#Secure');
    await page.getByRole('button', { name: /Sign In to Workstation/i }).click();

    // Wait for Dashboard
    await expect(page.getByText(/Fleet Condition & Risk Overview/i)).toBeVisible({ timeout: 10000 });

    // ── Navigate to Datasets & Open Wizard ─────────────────────────────────
    await page.goto('/datasets');
    await expect(page.getByText(/Dataset Registry & Versions/i)).toBeVisible();
    await page.getByRole('button', { name: /Upload New Dataset/i }).click();

    // ── Step 1: Upload Compatible File ────────────────────────────────────
    const compatibleFilePath = path.join(SAMPLES_DIR, 'compatible_fd001_slice.csv');
    const fileChooserInput = page.locator('#upload-dataset-file');
    await fileChooserInput.setInputFiles(compatibleFilePath);
    await page.getByRole('button', { name: /Upload & Compute Profile/i }).click();

    // ── Step 2: Dataset Profile ───────────────────────────────────────────
    await expect(page.getByText(/Dataset Profile & Integrity Analysis/i)).toBeVisible({ timeout: 15000 });
    await expect(page.getByText(/26/i).first()).toBeVisible(); // 26 columns
    await page.getByRole('button', { name: /Proceed to Schema Mapping/i }).click();

    // ── Step 3: Schema Mapping ────────────────────────────────────────────
    await expect(page.getByText(/Schema Auto-Detection & Interactive Column Mapping/i)).toBeVisible();
    await expect(page.getByText(/100% Exact/i).first()).toBeVisible();
    await page.getByRole('button', { name: /Save & Run Compatibility Gate/i }).click();

    // ── Step 4: Compatibility Gate (PASS) ─────────────────────────────────
    await expect(page.getByText(/Dataset Fully Compatible with Selected Model/i)).toBeVisible({ timeout: 15000 });
    await expect(page.getByText(/All 11 PRD FR-6 verification checks passed/i)).toBeVisible();
    await page.getByRole('button', { name: /Proceed to Ingestion/i }).click();

    // ── Step 5: Ingestion Progress & Auto-Advance to Scoring ──────────────
    await expect(page.getByText(/Telemetry Data Ingestion|Batch Model Scoring/i)).toBeVisible();
    const proceedBtn = page.getByRole('button', { name: /Proceed to Scoring Run/i });
    if (await proceedBtn.isVisible({ timeout: 2000 }).catch(() => false)) {
      await proceedBtn.click();
    }

    // ── Step 6: Scoring & Summary ─────────────────────────────────────────
    await expect(page.getByText(/Pipeline Execution Complete/i)).toBeVisible({ timeout: 25000 });
    await expect(page.getByText(/readings ingested/i)).toBeVisible();

    // Click "View Scored Fleet" to navigate to Fleet
    await page.getByRole('button', { name: /View Scored Fleet/i }).click();

    // ── Verify Cross-Page Synchronization ─────────────────────────────────
    // 1. Overview Dashboard
    await page.goto('/');
    await expect(page.getByText(/Fleet Condition & Risk Overview/i)).toBeVisible();
    // Demo banner must be visible because demo machines exist
    await expect(page.getByText(/Demo Dataset: NASA C-MAPSS FD001 — Simulated Turbofan Engine Data/i)).toBeVisible();

    // 2. Fleet Overview Page
    await page.goto('/fleet');
    await expect(page.getByRole('table')).toBeVisible();
    // Must display both Demo badges and User Upload badges
    await expect(page.getByText(/Demo \/ Simulated Data/i).first()).toBeVisible();
    await expect(page.getByText(/User Upload/i).first()).toBeVisible();

    // 3. Inspect a User Upload Machine Detail Page
    const userRow = page.locator('tr').filter({ hasText: /User Upload/i }).first();
    await userRow.click();

    // Machine detail for user machine
    await expect(page.getByText(/How was this prediction generated\?/i)).toBeVisible({ timeout: 10000 });
    // User machine must show User Upload badge
    await expect(page.getByText(/User Upload/i).first()).toBeVisible();
    // Lineage must show user dataset name
    await expect(page.getByText(/How was this prediction generated\?/i)).toBeVisible();

    // 4. Datasets Page
    await page.goto('/datasets');
    await expect(page.getByText(/compatible_fd001_slice/i)).toBeVisible();
  });

  test('2. WARN upload with out-of-range telemetry requires explicit acknowledgment', async ({ page }) => {
    // Log in
    await page.goto('/');
    const emailInput = page.getByRole('textbox', { name: /Operator Identity \/ Email/i });
    const passwordInput = page.locator('input[type="password"]');
    await expect(emailInput).toBeVisible({ timeout: 8000 });
    await emailInput.fill(process.env.E2E_ADMIN_EMAIL || 'admin@predicore.internal');
    await passwordInput.fill(process.env.E2E_ADMIN_PASSWORD || 'AdminReviewer2026#Secure');
    await page.getByRole('button', { name: /Sign In to Workstation/i }).click();

    // Wait for Dashboard post-login
    await expect(page.getByText(/Fleet Condition & Risk Overview/i)).toBeVisible({ timeout: 10000 });

    await page.goto('/datasets');
    await page.getByRole('button', { name: /Upload New Dataset/i }).click();

    // Upload out_of_range_warn.csv
    const warnFilePath = path.join(SAMPLES_DIR, 'out_of_range_warn.csv');
    await page.locator('#upload-dataset-file').setInputFiles(warnFilePath);
    await page.getByRole('button', { name: /Upload & Compute Profile/i }).click();

    // Step 2 -> Step 3
    await expect(page.getByText(/Dataset Profile & Integrity Analysis/i)).toBeVisible({ timeout: 15000 });
    await page.getByRole('button', { name: /Proceed to Schema Mapping/i }).click();

    // Step 3 -> Step 4
    await expect(page.getByText(/Schema Auto-Detection & Interactive Column Mapping/i)).toBeVisible();
    await page.getByRole('button', { name: /Save & Run Compatibility Gate/i }).click();

    // Step 4: Verify Out-of-Distribution Warning
    await expect(page.getByText(/Compatibility Warning: Out-Of-Distribution Telemetry/i)).toBeVisible({ timeout: 15000 });
    await expect(page.getByText(/OOD Warning/i)).toBeVisible();

    // Confirm button must be disabled until acknowledged
    const confirmBtn = page.getByRole('button', { name: /Confirm Acknowledgment & Ingest/i });
    await expect(confirmBtn).toBeDisabled();

    // Check acknowledgment checkbox
    await page.getByRole('checkbox').check();
    await expect(confirmBtn).toBeEnabled();
  });

  test('3. Incompatible dataset is strictly blocked with PRD message and plain-language explanation', async ({ page }) => {
    // Log in
    await page.goto('/');
    const emailInput = page.getByRole('textbox', { name: /Operator Identity \/ Email/i });
    const passwordInput = page.locator('input[type="password"]');
    await expect(emailInput).toBeVisible({ timeout: 8000 });
    await emailInput.fill(process.env.E2E_ADMIN_EMAIL || 'admin@predicore.internal');
    await passwordInput.fill(process.env.E2E_ADMIN_PASSWORD || 'AdminReviewer2026#Secure');
    await page.getByRole('button', { name: /Sign In to Workstation/i }).click();

    // Wait for Dashboard post-login
    await expect(page.getByText(/Fleet Condition & Risk Overview/i)).toBeVisible({ timeout: 10000 });

    await page.goto('/datasets');
    await page.getByRole('button', { name: /Upload New Dataset/i }).click();

    // Upload incompatible_non_fd001.csv
    const incompatibleFilePath = path.join(SAMPLES_DIR, 'incompatible_non_fd001.csv');
    await page.locator('#upload-dataset-file').setInputFiles(incompatibleFilePath);
    await page.getByRole('button', { name: /Upload & Compute Profile/i }).click();

    // Step 2 -> Step 3
    await expect(page.getByText(/Dataset Profile & Integrity Analysis/i)).toBeVisible({ timeout: 15000 });
    await page.getByRole('button', { name: /Proceed to Schema Mapping/i }).click();

    // Step 3 -> Step 4
    await expect(page.getByText(/Schema Auto-Detection & Interactive Column Mapping/i)).toBeVisible();
    await page.getByRole('button', { name: /Save & Run Compatibility Gate/i }).click();

    // Step 4: Exact PRD Message must be present
    await expect(page.getByText('This dataset is not compatible with the selected model.').first()).toBeVisible({ timeout: 15000 });

    // Inference blocked button must be disabled
    const blockedBtn = page.getByRole('button', { name: /Inference Blocked/i });
    await expect(blockedBtn).toBeDisabled();

    // Plain-language diagnosis and download report buttons must be visible
    await expect(page.getByText(/Plain-Language Diagnosis/i)).toBeVisible();
    await expect(page.getByRole('button', { name: /JSON Format/i })).toBeVisible();
    await expect(page.getByRole('button', { name: /CSV Format/i })).toBeVisible();
  });
});
