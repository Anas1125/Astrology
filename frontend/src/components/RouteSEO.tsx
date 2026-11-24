import { useLayoutEffect } from 'react';
import { useLocation } from 'react-router-dom';

const title = 'AstroAI — Vedic & Western Astrology in English and Tamil';
const description = 'Explore Vedic and Western astrology in English and Tamil, manage birth profiles, and discover chart features in your private AstroAI space.';
const socialDescription = 'Explore two astrology traditions and manage birth profiles in a private, bilingual space.';
const routeTitles: Record<string, string> = {
  '/login': 'Sign in', '/register': 'Create account',
  '/forgot-password': 'Forgot password', '/reset-password': 'Reset password',
};

function meta(attribute: 'name' | 'property', key: string, value: string | null) {
  const existing = document.head.querySelector<HTMLMetaElement>('meta[' + attribute + '="' + key + '"]');
  if (value === null) { existing?.remove(); return; }
  const element = existing ?? document.createElement('meta');
  element.setAttribute(attribute, key);
  element.content = value;
  if (!existing) document.head.append(element);
}

function publicOrigin(): string | null {
  try {
    const url = new URL(import.meta.env.VITE_SITE_URL || '');
    return url.protocol === 'https:' && url.origin === window.location.origin &&
      url.pathname === '/' && !url.search && !url.hash && !url.username && !url.password
      ? url.origin : null;
  } catch { return null; }
}

export default function RouteSEO() {
  const { pathname } = useLocation();
  useLayoutEffect(() => {
    const path = pathname.replace(/\/+$/, '') || '/';
    const home = path === '/';
    const origin = publicOrigin();
    const indexable = home && !!origin;
    document.title = home ? title : (routeTitles[path] ?? 'Private dashboard') + ' | AstroAI';
    meta('name', 'robots', indexable ? 'index, follow' : 'noindex, nofollow');
    meta('name', 'description', home ? description : null);
    for (const [key, value] of Object.entries({
      'og:type': 'website', 'og:site_name': 'AstroAI', 'og:title': title,
      'og:description': socialDescription, 'og:url': origin ? origin + '/' : null,
    })) meta('property', key, home ? value : null);
    for (const [key, value] of Object.entries({
      'twitter:card': 'summary', 'twitter:title': title, 'twitter:description': socialDescription,
    })) meta('name', key, home ? value : null);
    const canonical = document.head.querySelector<HTMLLinkElement>('link[rel="canonical"]');
    if (indexable) {
      const link = canonical ?? document.createElement('link');
      link.rel = 'canonical'; link.href = origin + '/';
      if (!canonical) document.head.append(link);
    } else canonical?.remove();
    const existing = document.getElementById('astroai-website-schema');
    if (indexable) {
      const schema = existing ?? document.createElement('script');
      schema.id = 'astroai-website-schema';
      schema.setAttribute('type', 'application/ld+json');
      schema.textContent = JSON.stringify({
        '@context': 'https://schema.org', '@type': 'WebSite', name: 'AstroAI', url: origin + '/',
        inLanguage: ['en', 'ta'],
        description: 'A bilingual space for exploring Vedic and Western astrology and managing birth profiles.',
      });
      if (!existing) document.head.append(schema);
    } else existing?.remove();
  }, [pathname]);
  return null;
}
