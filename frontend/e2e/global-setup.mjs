import { spawnSync } from 'node:child_process';
import { tmpdir } from 'node:os';
import { join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const frontendDir = fileURLToPath(new URL('..', import.meta.url));
const backendDir = resolve(frontendDir, '..', 'backend');
const python = resolve(backendDir, '.venv/bin/python');
const databasePath = join(tmpdir(), 'astroai-phase3-playwright.sqlite3');
const databaseUrl = `sqlite:///${databasePath}`;
export default async function globalSetup() {
  const result = spawnSync(python, ['tests/e2e_reset_db.py'], {
    cwd: backendDir,
    encoding: 'utf8',
    env: { ...process.env, DATABASE_URL: databaseUrl },
  });
  if (result.status !== 0) {
    throw new Error(`Could not initialize isolated Playwright database:\n${result.stdout}\n${result.stderr}`);
  }
}
