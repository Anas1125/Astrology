import { defineConfig } from '@playwright/test';
import { tmpdir } from 'node:os';
import { join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const frontendDir = fileURLToPath(new URL('.', import.meta.url));
const repositoryDir = resolve(frontendDir, '..');
const backendDir = resolve(repositoryDir, 'backend');
const databasePath = process.env.ASTROAI_E2E_DATABASE_PATH || join(tmpdir(), 'astroai-phase3-playwright.sqlite3');
const passwordResetFile = join(tmpdir(), 'astroai-e2e-password-reset-link.txt');
const databaseUrl = `sqlite:///${databasePath}`;
const python = resolve(backendDir, '.venv/bin/python');
const frontendPort = Number(process.env.ASTROAI_E2E_FRONTEND_PORT || 5173);
const apiPort = Number(process.env.ASTROAI_E2E_API_PORT || 8000);
if (!Number.isInteger(frontendPort) || frontendPort < 1024 || frontendPort > 65535) {
  throw new Error('ASTROAI_E2E_FRONTEND_PORT must be a valid unprivileged TCP port');
}
if (!Number.isInteger(apiPort) || apiPort < 1024 || apiPort > 65535) {
  throw new Error('ASTROAI_E2E_API_PORT must be a valid unprivileged TCP port');
}
const frontendUrl = `http://127.0.0.1:${frontendPort}`;
const apiUrl = `http://127.0.0.1:${apiPort}`;
const localCalculations = process.env.ASTROAI_E2E_LOCAL_CALCULATIONS === 'true';

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
      command: `${JSON.stringify(python)} -m uvicorn app.main:app --host 127.0.0.1 --port ${apiPort}`,
      cwd: backendDir,
      url: `${apiUrl}/health`,
      reuseExistingServer: false,
      timeout: 30_000,
      env: {
        APP_ENV: 'development',
        DATABASE_URL: databaseUrl,
        SECRET_KEY: 'astroai-e2e-only-secret-key',
        CORS_ORIGINS: frontendUrl,
        ASTROLOGY_CALCULATIONS_ENABLED: 'false',
        SWISSEPH_LICENSE_CONFIRMED: 'false',
        ASTROLOGY_LOCAL_AGPL_DEVELOPMENT_ENABLED: localCalculations ? 'true' : 'false',
        SWISSEPH_EPHE_PATH: process.env.SWISSEPH_EPHE_PATH || '',
        PASSWORD_RESET_DEV_TOKEN_FILE: passwordResetFile,
        PASSWORD_RESET_FRONTEND_URL: frontendUrl,
      },
    },
    {
      command: `npm run dev -- --host 127.0.0.1 --port ${frontendPort}`,
      cwd: frontendDir,
      url: frontendUrl,
      reuseExistingServer: false,
      timeout: 30_000,
      env: { VITE_API_BASE_URL: `${apiUrl}/api/v1` },
    },
  ],
});
