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
