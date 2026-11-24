import { readFile, writeFile, mkdir, rm } from 'node:fs/promises';
import { join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { loadEnv } from 'vite';

export const privatePages = {
  login: 'Sign in',
  register: 'Create account',
  'forgot-password': 'Forgot password',
  'reset-password': 'Reset password',
  app: 'Private dashboard',
};

export function siteOrigin(value) {
  if (!value?.trim()) return null;
  const url = new URL(value.trim());
  if (url.protocol !== 'https:' || url.username || url.password ||
      url.pathname !== '/' || url.search || url.hash ||
      ['localhost', '127.0.0.1', '[::1]'].includes(url.hostname)) {
    throw new Error('VITE_SITE_URL must be the public HTTPS frontend origin, without a path, query or fragment.');
  }
  return url.origin;
}

const escape = value => value.replaceAll('&', '&amp;').replaceAll('"', '&quot;').replaceAll('<', '&lt;').replaceAll('>', '&gt;');

export function seoFiles(html, origin) {
  const marker = '<!-- astroai:site-origin -->';
  if (!html.includes(marker)) throw new Error('Missing SEO marker in built index.html');
  const home = origin ? origin + '/' : null;
  const schema = home ? JSON.stringify({
    '@context': 'https://schema.org', '@type': 'WebSite', name: 'AstroAI', url: home,
    inLanguage: ['en', 'ta'],
    description: 'A bilingual space for exploring Vedic and Western astrology and managing birth profiles.',
  }).replaceAll('<', '\\u003c') : '';
  const tags = home ? [
    '<link rel="canonical" href="' + escape(home) + '"/>',
    '<meta property="og:url" content="' + escape(home) + '"/>',
    '<script id="astroai-website-schema" type="application/ld+json">' + schema + '</script>',
  ].join('\n') : '';
  const root = html.replace(marker, tags).replace(
    'content="noindex, nofollow"', home ? 'content="index, follow"' : 'content="noindex, nofollow"'
  );
  const routes = Object.fromEntries(Object.entries(privatePages).map(([path, title]) => [
    path, html.replace(marker, '').replace(/<title>[^<]*<\/title>/, '<title>' + title + ' | AstroAI</title>')
      .replace(/<meta\s+(?:property="og:[^"]+"|name="twitter:[^"]+")[^>]*>/g, '')
      .replace(/<meta\s+name="description"[^>]*>/, ''),
  ]));
  // Crawlers must be able to fetch pages carrying noindex. Robots is not access control.
  const robots = home
    ? 'User-agent: *\nAllow: /\nSitemap: ' + home + 'sitemap.xml\n'
    : 'User-agent: *\nDisallow: /\n';
  const sitemap = home ? '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"><url><loc>' + escape(home) + '</loc></url></urlset>\n' : null;
  return { root, routes, robots, sitemap };
}

export async function buildSEO(directory, origin) {
  const files = seoFiles(await readFile(join(directory, 'index.html'), 'utf8'), origin);
  await writeFile(join(directory, 'index.html'), files.root);
  await writeFile(join(directory, 'robots.txt'), files.robots);
  if (files.sitemap) await writeFile(join(directory, 'sitemap.xml'), files.sitemap);
  else await rm(join(directory, 'sitemap.xml'), { force: true });
  for (const [route, html] of Object.entries(files.routes)) {
    await mkdir(join(directory, route), { recursive: true });
    await writeFile(join(directory, route, 'index.html'), html);
  }
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const env = loadEnv('production', process.cwd(), 'VITE_');
  const origin = siteOrigin(env.VITE_SITE_URL);
  await buildSEO(resolve('dist'), origin);
  if (!origin) console.warn('SEO: VITE_SITE_URL is unset; indexing is disabled and sitemap omitted.');
  else console.log('SEO: homepage sitemap and private noindex pages generated for ' + origin);
}
