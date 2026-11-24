import test from 'node:test';
import assert from 'node:assert/strict';
import { onRequest } from '../functions/api/[[path]].js';

const origin = 'https://astroai.example';
const env = { ASTRO_API_ORIGIN: 'https://backend.example', ASTRO_FRONTEND_ORIGIN: origin,
  SESSION_PROXY_SECRET: 'fixture-only-' + '0123456789abcdef'.repeat(3) };
const call = (path, init = {}, config = env) => onRequest({request: new Request(origin + path, init), env: config});

test('proxy rejects missing configuration, wrong origin and missing CSRF', async () => {
  assert.equal((await call('/api/v1/auth/me', {}, {})).status, 503);
  assert.equal((await call('/api/v1/auth/session/login', {method: 'POST'})).status, 403);
  assert.equal((await call('/api/v1/profiles', {method: 'POST', headers: {
    Origin: 'https://evil.example', 'X-Astro-CSRF': '1',
  }})).status, 403);
  assert.equal((await call('/api/other')).status, 404);
  assert.equal((await call('/api/v1/profiles', {headers: {
    Cookie: '__Host-astroai-session=one; __Host-astroai-session=two',
  }})).status, 400);
});

test('proxy forwards only trusted headers and session cookie, preserves streams and set-cookie', async () => {
  const original = globalThis.fetch;
  const body = new ReadableStream({start(controller) {
    controller.enqueue(new TextEncoder().encode('event: done\n\ndata: {}\n\n'));
    controller.close();
  }});
  globalThis.fetch = async (url, init) => {
    assert.equal(String(url), 'https://backend.example/api/v1/ai/conversations/id/messages/stream');
    assert.equal(init.headers.get('Cookie'), '__Host-astroai-session=fixture');
    assert.equal(init.headers.get('Authorization'), null);
    assert.equal(init.headers.get('X-Astro-Proxy-Secret'), env.SESSION_PROXY_SECRET);
    assert.equal(init.headers.get('X-Astro-Client-IP'), '203.0.113.9');
    assert.equal(init.headers.get('X-Forwarded-For'), null);
    assert.equal(init.headers.get('Idempotency-Key'), 'fixture-request');
    assert.equal(init.redirect, 'manual');
    return new Response(body, {headers: {'Content-Type': 'text/event-stream',
      'Set-Cookie': '__Host-astroai-session=fixture; Secure; HttpOnly; Path=/'}});
  };
  try {
    const result = await call('/api/v1/ai/conversations/id/messages/stream', {
      method: 'POST', body: '{}', headers: {
        Origin: origin, 'X-Astro-CSRF': '1', Authorization: 'Bearer ignored',
        Cookie: 'other=ignored; __Host-astroai-session=fixture',
        'X-Astro-Proxy-Secret': 'spoofed', 'X-Forwarded-For': '198.51.100.1',
        'CF-Connecting-IP': '203.0.113.9', 'Idempotency-Key': 'fixture-request',
      },
    });
    assert.equal(result.status, 200);
    assert.equal(result.headers.get('Cache-Control'), 'no-store');
    assert.match(result.headers.get('Set-Cookie'), /HttpOnly/);
    assert.match(await result.text(), /event: done/);
  } finally { globalThis.fetch = original; }
});

test('proxy never follows upstream redirects', async () => {
  const original = globalThis.fetch;
  globalThis.fetch = async () => new Response(null, {status: 307, headers: {Location: 'https://evil.example'}});
  try { assert.equal((await call('/api/v1/auth/me')).status, 502); }
  finally { globalThis.fetch = original; }
});
