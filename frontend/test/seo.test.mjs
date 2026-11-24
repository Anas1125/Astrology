import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { seoFiles, siteOrigin } from '../scripts/build-seo.mjs';

const html = await readFile(new URL('../index.html', import.meta.url), 'utf8');

test('configured homepage has a canonical URL, metadata and one sitemap URL', () => {
  const origin = siteOrigin('https://astro.example/');
  const result = seoFiles(html, origin);
  assert.match(result.root, /content="index, follow"/);
  assert.match(result.root, /rel="canonical" href="https:\/\/astro.example\/"/);
  assert.match(result.root, /application\/ld\+json/);
  assert.match(result.root, /og:url/);
  assert.match(result.robots, /Sitemap: https:\/\/astro.example\/sitemap.xml/);
  assert.equal((result.sitemap.match(/<loc>/g) || []).length, 1);
  assert.match(result.sitemap, /<loc>https:\/\/astro.example\/<\/loc>/);
});

test('private entry documents have noindex and no homepage canonical or schema', () => {
  const result = seoFiles(html, 'https://astro.example');
  assert.deepEqual(Object.keys(result.routes), ['login', 'register', 'forgot-password', 'reset-password', 'app']);
  for (const route of Object.values(result.routes)) {
    assert.match(route, /content="noindex, nofollow"/);
    assert.doesNotMatch(route, /rel="canonical"|application\/ld\+json|property="og:/);
  }
});

test('unconfigured builds are not indexable and publish no sitemap', () => {
  const result = seoFiles(html, siteOrigin(''));
  assert.match(result.root, /content="noindex, nofollow"/);
  assert.equal(result.sitemap, null);
  assert.match(result.robots, /Disallow: \//);
});

test('rejects non-origin, insecure and credential-bearing URLs', () => {
  for (const bad of ['http://example.com', 'https://example.com/path', 'https://example.com/?q=1', 'https://user@example.com', 'https://localhost']) {
    assert.throws(() => siteOrigin(bad));
  }
});
