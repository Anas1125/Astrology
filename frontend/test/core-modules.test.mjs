import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { after, before, test } from 'node:test';
import { createServer } from 'vite';

let vite, api, panchang, horoscope, compatibility, birthTime;
before(async () => {
  vite = await createServer({ root: new URL('..', import.meta.url).pathname, configFile: new URL('../vite.config.ts', import.meta.url).pathname, appType: 'custom', logLevel: 'silent', server: { middlewareMode: true } });
  [api, panchang, horoscope, compatibility, birthTime] = await Promise.all([
    vite.ssrLoadModule('/src/auth/api.ts'), vite.ssrLoadModule('/src/astrology/PanchangPage.tsx'),
    vite.ssrLoadModule('/src/astrology/HoroscopePage.tsx'), vite.ssrLoadModule('/src/astrology/CompatibilityPage.tsx'),
    vite.ssrLoadModule('/src/pages/birthTime.ts'),
  ]);
});
after(async () => { await vite?.close(); });

const originalFetch = globalThis.fetch;
test('Panchang API sends authenticated local date, manual coordinates and IANA timezone', async () => {
  let call;
  const windows = { rahu_kalam: { part: 8, parts_in_daylight: 8, start: '2026-03-22T16:00:00+05:30', end: '2026-03-22T17:30:00+05:30' }, yamagandam: { part: 5, parts_in_daylight: 8, start: '2026-03-22T11:30:00+05:30', end: '2026-03-22T13:00:00+05:30' }, gulika_kalam: { part: 7, parts_in_daylight: 8, start: '2026-03-22T14:30:00+05:30', end: '2026-03-22T16:00:00+05:30' }, abhijit_muhurta: { part: 8, parts_in_daylight: 15, start: '2026-03-22T11:16:00+05:30', end: '2026-03-22T12:08:00+05:30' } };
  globalThis.fetch = async (url, init) => { call = { url: String(url), init }; return new Response(JSON.stringify({ local_date: '2026-03-22', daytime_windows: windows }), { status: 200 }); };
  try {
    const result = await api.calculateDailyPanchang('test-token', { local_date: '2026-03-22', location_name: 'Chennai', latitude: 13.08, longitude: 80.27, timezone: 'Asia/Kolkata' });
    assert.equal(call.url, 'http://localhost:8000/api/v1/panchang/daily');
    assert.equal(call.init.headers.Authorization, 'Bearer test-token');
    assert.deepEqual(JSON.parse(call.init.body), { local_date: '2026-03-22', location_name: 'Chennai', latitude: 13.08, longitude: 80.27, timezone: 'Asia/Kolkata' });
    assert.deepEqual(result.daytime_windows, windows);
  } finally { globalThis.fetch = originalFetch; }
});

test('Panchang UI retains the server licensing gate message on 503', async () => {
  globalThis.fetch = async () => new Response(JSON.stringify({ detail: 'Chart calculations are blocked pending Swiss Ephemeris licensing review. No result was saved.' }), { status: 503 });
  try {
    await assert.rejects(api.calculateDailyPanchang('test-token', { local_date: '2026-03-22', location_name: 'Chennai', latitude: 13, longitude: 80, timezone: 'Asia/Kolkata' }), error => error.status === 503 && /licensing review/.test(error.message));
  } finally { globalThis.fetch = originalFetch; }
});

test('horoscope and compatibility request contracts are authenticated and do not invent output', async () => {
  const calls = [];
  globalThis.fetch = async (url, init) => { calls.push({ url: String(url), init }); return new Response(JSON.stringify({ status: 'unavailable', content: null, source_references: [], score: null, factors: [] }), { status: 200 }); };
  try {
    const general = await api.checkDailyHoroscope('jwt', { mode: 'general', system: 'vedic', local_date: '2026-03-22', language: 'ta', sign: 'Mesha' });
    const personal = await api.checkDailyHoroscope('jwt', { mode: 'personalized', system: 'western', local_date: '2026-03-22', language: 'en', profile_id: 'owned-profile' });
    const compared = await api.checkCompatibility('jwt', { profile_a_id: 'profile-a', profile_b_id: 'profile-b', system: 'western' });
    assert.equal(calls[0].url, 'http://localhost:8000/api/v1/horoscope/daily');
    assert.deepEqual(JSON.parse(calls[0].init.body), { mode: 'general', system: 'vedic', local_date: '2026-03-22', language: 'ta', sign: 'Mesha' });
    assert.equal(JSON.parse(calls[1].init.body).profile_id, 'owned-profile');
    assert.deepEqual(JSON.parse(calls[2].init.body), { profile_a_id: 'profile-a', profile_b_id: 'profile-b', system: 'western' });
    for (const call of calls) assert.equal(call.init.headers.Authorization, 'Bearer jwt');
    assert.equal(general.content, null); assert.deepEqual(general.source_references, []);
    assert.equal(compared.score, null); assert.deepEqual(compared.factors, []);
  } finally { globalThis.fetch = originalFetch; }
});

test('birthplace lookup uses authenticated backend proxy and preserves returned ambiguity and optional timezone', async () => {
  const place = { id: 'nagercoil-india', city: 'Nagercoil', region: 'Tamil Nadu', country: 'India', latitude: 8.1833, longitude: 77.4119, timezone: 'Asia/Kolkata', attribution: 'Geoapify' };
  let call;
  globalThis.fetch = async (url, init) => { call = { url: String(url), init }; return new Response(JSON.stringify([place, { ...place, id: 'nagercoil-other', region: 'Other Region', country: 'Other Country', timezone: null }]), { status: 200 }); };
  try {
    const controller = new AbortController();
    const places = await api.searchBirthplaces('jwt', 'Nagercoil', 'ta', controller.signal);
    assert.match(call.url, /\/profiles\/location-search\?q=Nagercoil&language=ta$/);
    assert.equal(call.init.headers.Authorization, 'Bearer jwt');
    assert.equal(call.init.signal, controller.signal);
    assert.equal(places.length, 2);
    assert.equal(places[0].region, 'Tamil Nadu');
    assert.equal(places[1].timezone, null);
  } finally { globalThis.fetch = originalFetch; }
});

test('horoscope API failures stay distinct from a successful unavailable-content response', async () => {
  globalThis.fetch = async () => new Response(JSON.stringify({ detail: 'Temporarily unavailable' }), { status: 503 });
  try {
    await assert.rejects(
      api.checkDailyHoroscope('jwt', { mode: 'general', system: 'vedic', local_date: '2026-03-22', language: 'en', sign: 'Mesha' }),
      error => error instanceof api.ApiError && error.status === 503 && error.message === 'Temporarily unavailable',
    );
  } finally { globalThis.fetch = originalFetch; }
});

test('12-hour birth time conversion handles midnight, noon, AM, PM and profile edit values', () => {
  assert.equal(birthTime.toBackendBirthTime({ hour: '12', minute: '00', meridiem: 'AM' }), '00:00:00');
  assert.equal(birthTime.toBackendBirthTime({ hour: '12', minute: '00', meridiem: 'PM' }), '12:00:00');
  assert.equal(birthTime.toBackendBirthTime({ hour: '11', minute: '30', meridiem: 'AM' }), '11:30:00');
  assert.equal(birthTime.toBackendBirthTime({ hour: '07', minute: '45', meridiem: 'PM' }), '19:45:00');
  assert.deepEqual(birthTime.to12HourParts('00:00:00'), { hour: '12', minute: '00', meridiem: 'AM' });
  assert.deepEqual(birthTime.to12HourParts('12:00:00'), { hour: '12', minute: '00', meridiem: 'PM' });
  assert.deepEqual(birthTime.to12HourParts('19:45:00'), { hour: '07', minute: '45', meridiem: 'PM' });
});

test('new modules provide matching English and Tamil labels and explain unavailable content', () => {
  for (const text of [panchang.panchangText, horoscope.horoscopeText, compatibility.compatibilityText]) {
    assert.deepEqual(Object.keys(text.en).sort(), Object.keys(text.ta).sort());
    for (const value of Object.values(text.ta)) assert.ok(value.trim());
  }
  assert.match(horoscope.horoscopeText.en.limitation, /source and bilingual editorial review/);
  assert.match(compatibility.compatibilityText.en.method, /No score/);
  assert.match(panchang.panchangText.en.runtime, /licensing review/);
});

test('global typography tokens and responsive navigation make text/control sizes readable', async () => {
  const css = await readFile(new URL('../src/style.css', import.meta.url), 'utf8');
  assert.match(css, /--type-body:16px/);
  assert.match(css, /\.ai-message p\{font-size:15px/);
  assert.match(css, /\.profile-fields input,.profile-fields select\{height:42px/);
  assert.match(css, /\.sidebar nav a\{font-size:15px/);
  assert.match(css, /@media\(max-width:700px\)[\s\S]*?\.sidebar nav a/);
});
