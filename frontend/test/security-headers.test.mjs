import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { apiOrigin, securityHeaders, buildSecurity } from '../scripts/build-security.mjs';
import { mkdtemp, writeFile, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

const template = await readFile(new URL('../public/_headers', import.meta.url), 'utf8');
const api = 'https://astro-api.example/api/v1';

test('default CSP is report-only, keeps exact API origin and permits required fonts and previews', () => {
  const headers = securityHeaders(template, api);
  assert.match(headers, /Content-Security-Policy-Report-Only:/);
  assert.doesNotMatch(headers, /Content-Security-Policy:/);
  assert.match(headers, /connect-src 'self' https:\/\/astro-api\.example;/);
  assert.match(headers, /script-src 'self';/);
  assert.match(headers, /style-src 'self' 'unsafe-inline' https:\/\/fonts\.googleapis\.com;/);
  assert.match(headers, /font-src 'self' https:\/\/fonts\.gstatic\.com;/);
  assert.match(headers, /img-src 'self' blob: data:;/);
  assert.match(headers, /frame-ancestors 'none';/);
  assert.match(headers, /object-src 'none';/);
  assert.doesNotMatch(headers, /unsafe-eval/);
});

test('all SEO noindex rules and global security headers survive generation', () => {
  const headers = securityHeaders(template, api);
  assert.equal(headers.replace(/^  Content-Security-Policy-Report-Only:.*\n/m, ''), template);
  for (const name of ['X-Content-Type-Options', 'X-Frame-Options', 'Referrer-Policy', 'Permissions-Policy']) {
    assert.ok(headers.includes(name + ':'));
  }
  assert.equal((headers.match(/X-Robots-Tag: noindex, nofollow/g) || []).length, 10);
});

test('explicit enforcement switches only the CSP header name', () => {
  const report = securityHeaders(template, api);
  const enforced = securityHeaders(template, api, true, 'https://astro.example');
  assert.equal(enforced, report.replace('Content-Security-Policy-Report-Only:', 'Content-Security-Policy:'));
});

test('missing API origin is safe in report-only mode but cannot be enforced', () => {
  assert.match(securityHeaders(template, ''), /connect-src 'self';/);
  assert.throws(() => securityHeaders(template, '', true));
  assert.throws(() => securityHeaders(template, 'http://localhost:8000/api/v1', true, 'https://astro.example'));
});

test('API origin excludes path and rejects unsafe or ambiguous URLs', () => {
  assert.equal(apiOrigin(api), 'https://astro-api.example');
  assert.equal(apiOrigin('http://127.0.0.1:8000/api/v1'), 'http://127.0.0.1:8000');
  for (const bad of ['http://example.com', 'https://user@example.com', 'https://example.com/?key=abc', 'https://example.com/#fragment', 'javascript:alert(1)']) {
    assert.throws(() => apiOrigin(bad));
  }
});

test('postbuild writes the selected CSP to the deployable _headers file', async () => {
  const dir = await mkdtemp(join(tmpdir(), 'astroai-security-'));
  try {
    await writeFile(join(dir, '_headers'), template);
    await buildSecurity(dir, { VITE_API_BASE_URL: api, VITE_CSP_ENFORCE: 'true' });
    assert.equal(await readFile(join(dir, '_headers'), 'utf8'), securityHeaders(template, api, true));
  } finally { await rm(dir, { recursive: true, force: true }); }
});
