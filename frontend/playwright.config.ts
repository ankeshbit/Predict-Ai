import { defineConfig, devices } from '@playwright/test';

// Credentials sourced from environment variables (provided by CI or local test runner)
process.env.E2E_ADMIN_EMAIL = process.env.E2E_ADMIN_EMAIL || 'admin@predicore.internal';
process.env.E2E_ENGINEER_EMAIL = process.env.E2E_ENGINEER_EMAIL || 'engineer@predicore.internal';

export default defineConfig({
  testDir: './e2e',
  timeout: 60 * 1000,
  expect: {
    timeout: 8000,
  },
  fullyParallel: false,
  retries: 0,
  workers: 1,
  use: {
    baseURL: 'http://localhost:5173',
    extraHTTPHeaders: {
      'x-e2e-test': '1',
    },
    trace: 'on-first-retry',
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
  webServer: {
    command: 'npm run dev',
    url: 'http://localhost:5173',
    reuseExistingServer: !process.env.CI,
    timeout: 60 * 1000,
  },
});
