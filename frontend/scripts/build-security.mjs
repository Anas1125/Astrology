import { readFile, writeFile } from 'node:fs/promises';
import { join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { loadEnv } from 'vite';

export function apiOrigin(value) {
  if (!value?.trim()) return null;
  const url = new URL(value.trim());
  const loopback = ['localhost', '127.0.0.1', '[::1]'].includes(url.hostname);
  if ((url.protocol !== 'https:' && !(url.protocol === 'http:' && loopback)) ||
      url.username || url.password || url.search || url.hash) {
    throw new Error('VITE_API_BASE_URL must be an HTTPS API URL (HTTP is allowed only for local loopback development), without credentials, query or fragment.');
  }
  return url.origin;
}

export function contentSecurityPolicy(origin) {
  return [
    "default-src 'self'",
    "script-src 'self'",
    // React positions chart cells and Vastu markers using inline styles.
    "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
    "font-src 'self' https://fonts.gstatic.com",
    // Vastu displays a local object URL before uploading the floor plan.
    "img-src 'self' blob: data:",
    "connect-src 'self'" + (origin ? ' ' + origin : ''),
    "object-src 'none'",
    "base-uri 'none'",
    "frame-ancestors 'none'",
    "frame-src 'none'",
    "form-action 'self'",
    "worker-src 'none'",
  ].join('; ') + ';';
}

export function securityHeaders(template, apiBase, enforce = false, siteUrl = '') {
  const origin = apiOrigin(apiBase);
  if (enforce && (!origin || (siteUrl && !origin.startsWith('https://')))) {
    throw new Error('Configure VITE_API_BASE_URL before enforcing CSP; public deployments require HTTPS.');
  }
  if (!template.startsWith('/*\n') || /Content-Security-Policy(?:-Report-Only)?:/i.test(template)) {
    throw new Error('Unexpected _headers template: expected a wildcard block with no existing CSP.');
  }
  const name = enforce ? 'Content-Security-Policy' : 'Content-Security-Policy-Report-Only';
  return template.replace('/*\n', '/*\n  ' + name + ': ' + contentSecurityPolicy(origin) + '\n');
}

export async function buildSecurity(directory, env) {
  const file = join(directory, '_headers');
  const template = await readFile(file, 'utf8');
  const enforce = env.VITE_CSP_ENFORCE === 'true';
  await writeFile(file, securityHeaders(template, env.VITE_API_BASE_URL, enforce, env.VITE_SITE_URL));
  if (!env.VITE_API_BASE_URL) console.warn('CSP: VITE_API_BASE_URL is unset; no external API origin is allowed. Configure it on the deployment.');
  console.log('CSP: ' + (enforce ? 'enforced' : 'report-only') + '; existing SEO headers preserved.');
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  await buildSecurity(resolve('dist'), loadEnv('production', process.cwd(), 'VITE_'));
}
