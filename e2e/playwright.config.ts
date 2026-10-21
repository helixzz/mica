import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './tests',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  // Every spec signs in as the same few accounts and the login endpoint is rate
  // limited, so parallel workers make unrelated specs fail on login timeouts.
  // CI already ran serially; do the same locally so the result means something.
  workers: 1,
  reporter: [
    ['html', { open: 'never' }],
    ['list'],
  ],
  timeout: 60_000,
  expect: {
    timeout: 15_000,
  },
  use: {
    baseURL: process.env.BASE_URL || 'http://localhost:8900',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
});