import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';

test('dashboard includes Tamil and English labels and accessible language switch', async () => {
  const source = await readFile(new URL('../src/pages/App.tsx', import.meta.url), 'utf8');
  assert.match(source, /உங்கள் வானம்/);
  assert.match(source, /Welcome to AstroAI/);
  assert.match(source, /setLanguage\(tamil \? 'en' : 'ta'\)/);
});

test('astrology data is explicitly marked unavailable until verified', async () => {
  const source = await readFile(new URL('../../backend/app/services/astrology/vedic.py', import.meta.url), 'utf8');
  assert.match(source, /Astrology calculations are disabled until licensing\/runtime verification is completed/);
  assert.match(source, /Swiss Ephemeris licensing has not been confirmed; public calculations remain disabled/);
});

test('dashboard avoids fake controls and static dates, and explains unavailable modules in both languages', async () => {
  const source = await readFile(new URL('../src/pages/App.tsx', import.meta.url), 'utf8');
  assert.match(source, /Intl\.DateTimeFormat\(tamil \? 'ta-IN' : 'en-US'/);
  assert.doesNotMatch(source, /November 3, 2026|நவம்பர் 3, 2026|Visit our guide|<Bell/);
  assert.match(source, /No date-specific horoscope content has passed source and editorial review/);
  assert.match(source, /பொது கணக்கீடுகள் தற்போது முடக்கப்பட்டுள்ளன/);
  assert.match(source, /No score is generated/);
});
