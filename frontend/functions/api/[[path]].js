// Same-origin API proxy. Runtime-only configuration; never expose the proxy secret to Vite.
const cookieName = '__Host-astroai-session';
const methods = new Set(['GET', 'HEAD', 'POST', 'PUT', 'PATCH', 'DELETE']);
const error = (status, detail) => Response.json({ detail }, { status, headers: { 'Cache-Control': 'no-store' } });

export async function onRequest({ request, env }) {
  const url = new URL(request.url);
  let upstream;
  try { upstream = new URL(env.ASTRO_API_ORIGIN); } catch { return error(503, 'API proxy not configured'); }
  if (upstream.protocol !== 'https:' || upstream.username || upstream.password ||
      upstream.pathname !== '/' || upstream.search || upstream.hash ||
      !env.SESSION_PROXY_SECRET || env.SESSION_PROXY_SECRET.length < 32 ||
      url.origin !== env.ASTRO_FRONTEND_ORIGIN) return error(503, 'API proxy not configured');
  if (!methods.has(request.method)) return error(405, 'Method not allowed');
  if (!url.pathname.startsWith('/api/v1/') || /%2f|%5c|%2e/i.test(url.pathname)) return error(404, 'Not found');
  const safe = request.method === 'GET' || request.method === 'HEAD';
  if (!safe && (request.headers.get('Origin') !== url.origin ||
      request.headers.get('X-Astro-CSRF') !== '1')) return error(403, 'Cross-origin session request denied');
  const headers = new Headers();
  for (const name of ['Content-Type', 'Accept', 'Idempotency-Key', 'Origin', 'X-Astro-CSRF']) {
    const value = request.headers.get(name);
    if (value !== null) headers.set(name, value);
  }
  // Never forward browser-supplied Authorization or arbitrary cookies / forwarding headers.
  const cookies = (request.headers.get('Cookie') || '').split(';').map(value => value.trim());
  const sessionCookies = cookies.filter(value => value.startsWith(cookieName + '='));
  if (sessionCookies.length > 1) return error(400, 'Invalid session cookie');
  if (sessionCookies.length) headers.set('Cookie', sessionCookies[0]);
  headers.set('X-Astro-Proxy-Secret', env.SESSION_PROXY_SECRET);
  headers.set('X-Astro-Proxy-Origin', url.origin);
  const clientIp = request.headers.get('CF-Connecting-IP');
  if (clientIp) headers.set('X-Astro-Client-IP', clientIp);
  const target = new URL(upstream.origin);
  target.pathname = url.pathname;
  target.search = url.search;
  try {
    const response = await fetch(target, {
      method: request.method, headers, body: safe ? undefined : request.body,
      redirect: 'manual',
    });
    if (response.status >= 300 && response.status < 400) return error(502, 'Unexpected upstream redirect');
    const outgoing = new Headers(response.headers);
    outgoing.delete('Access-Control-Allow-Origin');
    outgoing.delete('Access-Control-Allow-Credentials');
    outgoing.delete('Content-Length');
    outgoing.delete('Content-Encoding');
    outgoing.set('Cache-Control', 'no-store');
    return new Response(response.body, { status: response.status, headers: outgoing });
  } catch {
    return error(502, 'API temporarily unavailable');
  }
}
