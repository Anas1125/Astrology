import assert from 'node:assert/strict';
import { after, before, test } from 'node:test';
import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { createServer } from 'vite';

let vite;
let api;
let i18n;
let utils;
let vedicModule;
let westernModule;
let feedbackModule;

before(async () => {
  vite = await createServer({
    root: new URL('..', import.meta.url).pathname,
    configFile: new URL('../vite.config.ts', import.meta.url).pathname,
    appType: 'custom',
    logLevel: 'silent',
    server: { middlewareMode: true },
  });
  [api, i18n, utils, vedicModule, westernModule, feedbackModule] = await Promise.all([
    vite.ssrLoadModule('/src/auth/api.ts'),
    vite.ssrLoadModule('/src/astrology/i18n.ts'),
    vite.ssrLoadModule('/src/astrology/chartUtils.ts'),
    vite.ssrLoadModule('/src/astrology/VedicChartView.tsx'),
    vite.ssrLoadModule('/src/astrology/WesternChartView.tsx'),
    vite.ssrLoadModule('/src/astrology/ChartFeedback.tsx'),
  ]);
});

after(async () => { await vite?.close(); });

const savedFetch = globalThis.fetch;

test('chart API sends exact authenticated requests, history filters and saved retrieval path', async () => {
  const calls = [];
  globalThis.fetch = async (url, init) => {
    calls.push({ url: String(url), init });
    return new Response(JSON.stringify({ chart_id: 'chart/1' }), { status: 200, headers: { 'Content-Type': 'application/json' } });
  };
  try {
    await api.calculateVedicChart('jwt', 'profile-1', 'D1');
    await api.calculateVedicChart('jwt', 'profile-1', 'D9');
    await api.calculateWesternChart('jwt', 'profile-1', 'W', { conjunction: 4 });
    await api.getSavedChart('jwt', 'chart/1');
    await api.listChartHistory('jwt', { profileId: 'profile-1', system: 'vedic', limit: 10, offset: 20 });
    assert.equal(calls[0].url, 'http://localhost:8000/api/v1/astrology/charts/vedic');
    assert.deepEqual(JSON.parse(calls[0].init.body), { profile_id: 'profile-1', division: 'D1', house_system: 'P', dasha_year_convention: 'savana_360_day' });
    assert.equal(JSON.parse(calls[1].init.body).division, 'D9');
    assert.deepEqual(JSON.parse(calls[2].init.body), { profile_id: 'profile-1', house_system: 'W', aspect_orbs: { conjunction: 4 } });
    assert.equal(calls[3].url, 'http://localhost:8000/api/v1/astrology/charts/chart%2F1');
    assert.equal(calls[4].url, 'http://localhost:8000/api/v1/astrology/charts?profile_id=profile-1&system=vedic&limit=10&offset=20');
    for (const call of calls) {
      assert.equal(call.init.headers.Authorization, 'Bearer jwt');
      assert.equal(call.init.headers['Content-Type'], 'application/json');
    }
    assert.equal(calls[3].init.method, 'GET');
    assert.equal(calls[4].init.method, 'GET');
  } finally { globalThis.fetch = savedFetch; }
});

test('chart API retains backend gate status and error detail', async () => {
  globalThis.fetch = async () => new Response(JSON.stringify({ detail: 'Calculation disabled by server configuration' }), { status: 503 });
  try {
    await assert.rejects(api.calculateVedicChart('jwt', 'profile-1', 'D1'), error => error.status === 503 && /disabled/.test(error.message));
  } finally { globalThis.fetch = savedFetch; }
});

const houseSet = Array.from({ length: 12 }, (_, index) => ({ number: index + 1, cusp_longitude: index * 30, sign: ['Aries','Taurus','Gemini','Cancer','Leo','Virgo','Libra','Scorpio','Sagittarius','Capricorn','Aquarius','Pisces'][index], sign_index: index, degrees_in_sign: 0 }));
const vedic = {
  calculation_system: 'vedic', division: 'D1', planets: [
    { name: 'Sun', longitude: 12.5, retrograde: false, house: 1, nakshatra: { index: 0, name: 'Ashwini', lord: 'Ketu', pada: 2, remaining_fraction: 0.4, degrees_remaining: 4, rashi: 'Mesha', degrees_in_rashi: 12.5 }, division_rashi: 'Mesha', division_rashi_index: 0, division_longitude: 12.5, division_house: 1 },
    { name: 'Moon', longitude: 44, retrograde: false, house: 2, nakshatra: { index: 3, name: 'Rohini', lord: 'Moon', pada: 1, remaining_fraction: 0.6, degrees_remaining: 8, rashi: 'Vrishabha', degrees_in_rashi: 14 }, division_rashi: 'Karka', division_rashi_index: 3, division_longitude: 104, division_house: 4 },
  ], houses: houseSet, division_houses: houseSet,
  ascendant: { longitude: 5, rashi: 'Mesha', rashi_index: 0, house: 1, division_longitude: 95, division_rashi: 'Karka', division_rashi_index: 3, division_house: 1 },
  vimshottari_dasha: { year_convention: 'savana_360_day', year_length_days: 360, starting_nakshatra: 'Ashwini', starting_lord: 'Ketu', birth_balance_days: 100, mahadashas: [{ lord: 'Ketu', start: '2020-01-01T00:00:00Z', end: '2027-01-01T00:00:00Z', full_duration_days: 2520, balance_days_at_birth: 100 }], antardashas: [{ lord: 'Venus', mahadasha_lord: 'Ketu', start: '2021-01-01T00:00:00Z', end: '2022-01-01T00:00:00Z', full_duration_days: 360 }] },
};
const western = {
  calculation_system: 'western', planets: [
    { name: 'Sun', longitude: 12.5, sign: 'Aries', degrees_in_sign: 12.5, house: 1, retrograde: false },
    { name: 'Moon', longitude: 72, sign: 'Gemini', degrees_in_sign: 12, house: 3, retrograde: false },
  ], houses: houseSet,
  ascendant: { longitude: 0, sign: 'Aries' }, midheaven: { longitude: 270, sign: 'Capricorn' },
  aspects: [{ planet_a: 'Sun', planet_b: 'Moon', aspect: 'sextile', angle: 60, separation: 59.5, orb: 0.5, allowed_orb: 6, motion: 'applying' }],
};

test('profile selection restores a current or remembered profile only when it belongs to the loaded profile list', () => {
  const profiles = [{ id: 'p1' }, { id: 'p2' }];
  assert.equal(utils.chooseProfileId(profiles, 'p2', 'p1'), 'p2');
  assert.equal(utils.chooseProfileId(profiles, 'deleted', 'p1'), 'p1');
  assert.equal(utils.chooseProfileId(profiles, '', 'deleted'), 'p1');
  assert.equal(utils.chooseProfileId([], '', null), '');
});

test('Vedic view renders response placements, Nakshatra, dasha and D1/D9 layouts', () => {
  const render = (division, language, initialLayout) => renderToStaticMarkup(React.createElement(vedicModule.VedicChartView, { data: vedic, division, language, initialLayout }));
  const d1 = render('D1', 'en', 'south');
  const d9 = render('D9', 'en', 'south');
  const north = render('D1', 'ta', 'north');
  assert.match(d1, /South Indian sign chart/);
  assert.match(d1, /Ashwini/);
  assert.match(d1, /Pada/);
  assert.match(d1, /Vimshottari Mahadasha/);
  assert.match(d1, /360-day Savana/);
  assert.match(d9, /Karka/);
  assert.match(north, /வடஇந்திய பாவக் கட்டம்/);
  assert.match(north, /சூரியன்/);
});

test('Western view renders actual houses, planets, angles and aspect details', () => {
  const html = renderToStaticMarkup(React.createElement(westernModule.default, { data: western, language: 'en' }));
  assert.match(html, /Western tropical natal chart wheel/);
  assert.match(html, /ASC/);
  assert.match(html, /MC/);
  assert.match(html, /Major aspects/);
  assert.match(html, />sextile</);
  assert.match(html, /Applying/);
  assert.match(html, /Aries/);
});

test('chart feedback covers loading, empty, unavailable and error states in English and Tamil', () => {
  const { ChartLoadingState, ChartEmptyState, ChartErrorState } = feedbackModule;
  assert.match(renderToStaticMarkup(React.createElement(ChartLoadingState, { language: 'en' })), /Calculating/);
  assert.match(renderToStaticMarkup(React.createElement(ChartEmptyState, { language: 'ta', noProfiles: true })), /பிறப்பு விவரத்தைச் சேர்க்கவும்/);
  assert.match(renderToStaticMarkup(React.createElement(ChartErrorState, { language: 'en', message: 'Server disabled', unavailable: true })), /Chart calculation unavailable/);
  assert.match(renderToStaticMarkup(React.createElement(ChartErrorState, { language: 'ta', message: 'பிழை' })), /ஜாதகத்தை ஏற்ற முடியவில்லை/);
});

test('every chart interface translation key is present in English and Tamil', () => {
  const flatten = value => Object.entries(value).flatMap(([key, child]) => child && typeof child === 'object' ? Object.keys(child).map(nested => `${key}.${nested}`) : [key]).sort();
  assert.deepEqual(flatten(i18n.astrologyText.en), flatten(i18n.astrologyText.ta));
  for (const [key, value] of Object.entries(i18n.astrologyText.ta)) {
    if (typeof value === 'string') assert.ok(value.trim(), `Tamil translation missing: ${key}`);
  }
});
