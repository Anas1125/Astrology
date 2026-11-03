import { defineConfig } from '@playwright/test';
import { tmpdir } from 'node:os';
import { join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const frontendDir = fileURLToPath(new URL('.', import.meta.url));
const repositoryDir = resolve(frontendDir, '..');
const backendDir = resolve(repositoryDir, 'backend');
const databasePath = join(tmpdir(), 'astroai-phase3-playwright.sqlite3');
const databaseUrl = `sqlite:///${databasePath}`;
const python = resolve(backendDir, '.venv/bin/python');
const frontendPort = Number(process.env.ASTROAI_E2E_FRONTEND_PORT || 5173);
if (!Number.isInteger(frontendPort) || frontendPort < 1024 || frontendPort > 65535) {
  throw new Error('ASTROAI_E2E_FRONTEND_PORT must be a valid unprivileged TCP port');
}
const frontendUrl = `http://127.0.0.1:${frontendPort}`;

export default defineConfig({
  testDir: './e2e',
  fullyParallel: false,
  workers: 1,
  timeout: 60_000,
  reporter: 'list',
  globalSetup: './e2e/global-setup.mjs',
  use: { baseURL: frontendUrl, browserName: 'chromium', headless: true, trace: 'retain-on-failure' },
  webServer: [
    {
      command: `${JSON.stringify(python)} -m uvicorn app.main:app --host 127.0.0.1 --port 8000`,
      cwd: backendDir,
      url: 'http://127.0.0.1:8000/health',
      reuseExistingServer: false,
      timeout: 30_000,
      env: {
        DATABASE_URL: databaseUrl,
        SECRET_KEY: 'astroai-e2e-only-secret-key',
        CORS_ORIGINS: frontendUrl,
        ASTROLOGY_CALCULATIONS_ENABLED: 'false',
        SWISSEPH_LICENSE_CONFIRMED: 'false',
      },
    },
    {
      command: `npm run dev -- --host 127.0.0.1 --port ${frontendPort}`,
      cwd: frontendDir,
      url: frontendUrl,
      reuseExistingServer: false,
      timeout: 30_000,
      env: { VITE_API_BASE_URL: 'http://127.0.0.1:8000/api/v1' },
    },
  ],
});
