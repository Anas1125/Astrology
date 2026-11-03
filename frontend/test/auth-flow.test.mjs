import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';

const read = path => readFile(new URL(path, import.meta.url), 'utf8');

test('auth API follows backend JSON registration and OAuth form login contracts', async () => {
  const source = await read('../src/auth/api.ts');
  assert.match(source, /JSON\.stringify\(\{ email, password \}\)/);
  assert.match(source, /URLSearchParams\(\{ username: email, password \}\)/);
  assert.match(source, /application\/x-www-form-urlencoded/);
  assert.match(source, /access_token/);
});

test('protected dashboard and reload restoration use the API verified session token', async () => {
  const routes = await read('../src/main.tsx');
  const provider = await read('../src/auth/AuthContext.tsx');
  const guard = await read('../src/auth/ProtectedRoute.tsx');
  assert.match(routes, /ProtectedRoute/);
  assert.match(routes, /path="\/app\/\*"/);
  assert.match(provider, /sessionStorage\.getItem\(TOKEN_KEY\)/);
  assert.match(provider, /getAccount\(saved\)/);
  assert.match(guard, /Navigate to="\/login"/);
});

test('dashboard uses authenticated account and exposes logout', async () => {
  const source = await read('../src/pages/App.tsx');
  assert.match(source, /account\?\.email/);
  assert.match(source, /logout\(\)/);
  assert.doesNotMatch(source, /AstroAI Member/);
});
