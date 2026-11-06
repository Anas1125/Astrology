import assert from 'node:assert/strict';
import { after, before, test } from 'node:test';
import { readFile } from 'node:fs/promises';
import { createServer } from 'vite';

let vite, api;
before(async () => {
  vite = await createServer({ root: new URL('..', import.meta.url).pathname, configFile: new URL('../vite.config.ts', import.meta.url).pathname, appType: 'custom', logLevel: 'silent', server: { middlewareMode: true } });
  api = await vite.ssrLoadModule('/src/auth/api.ts');
});
after(async () => { await vite?.close(); });

const originalFetch = globalThis.fetch;
test('forgot and reset API requests use the backend contracts without exposing returned tokens', async () => {
  const calls = [];
  globalThis.fetch = async (url, init) => {
    calls.push({ url: String(url), init });
    return new Response(JSON.stringify({ message: 'If the address is registered and delivery is available, instructions will be sent.' }), { status: 202 });
  };
  try {
    await api.requestPasswordReset('member@example.com');
    await api.resetPassword('opaque-reset-token-value-123456789012345', 'a-strong-password-123');
    assert.equal(calls[0].url, 'http://localhost:8000/api/v1/auth/forgot-password');
    assert.deepEqual(JSON.parse(calls[0].init.body), { email: 'member@example.com' });
    assert.equal(calls[0].init.headers.Authorization, undefined);
    assert.equal(calls[1].url, 'http://localhost:8000/api/v1/auth/reset-password');
    assert.deepEqual(JSON.parse(calls[1].init.body), { token: 'opaque-reset-token-value-123456789012345', new_password: 'a-strong-password-123' });
  } finally { globalThis.fetch = originalFetch; }
});

test('recovery pages have complete English and Tamil content with neutral account wording', async () => {
  const [forgot, reset] = await Promise.all([
    readFile(new URL('../src/pages/ForgotPasswordPage.tsx', import.meta.url), 'utf8'),
    readFile(new URL('../src/pages/ResetPasswordPage.tsx', import.meta.url), 'utf8'),
  ]);
  for (const [source, tamilIndicator] of [[forgot, 'பதிவு செய்யப்பட்டு'], [reset, 'கடவுச்சொல்லைப் புதுப்பி']]) {
    assert.match(source, /en:\s*\{/); assert.match(source, /ta:\s*\{/); assert.ok(source.includes(tamilIndicator));
  }
  assert.match(forgot, /If the address is registered/);
  assert.match(reset, /12 characters/);
  assert.match(reset, /minLength=\{12\}/);
  assert.match(reset, /Confirm new password/);
  assert.match(reset, /type=\{showPassword \? 'text' : 'password'\}/);
});

test('chat UI has no daily message counter or quota-based send lock', async () => {
  const [page, apiSource] = await Promise.all([
    readFile(new URL('../src/astrology/AIChatPage.tsx', import.meta.url), 'utf8'),
    readFile(new URL('../src/auth/api.ts', import.meta.url), 'utf8'),
  ]);
  assert.doesNotMatch(page, /messages remaining today|இன்றைய மீதமுள்ள செய்திகள்|usage\.remaining/);
  assert.match(apiSource, /export type AIChatResponse = \{ message: AIMessage \}/);
  assert.doesNotMatch(apiSource, /daily_limit: number/);
});
