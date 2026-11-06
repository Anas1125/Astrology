import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';

const page = await readFile(new URL('../src/astrology/VastuPage.tsx', import.meta.url), 'utf8');
const app = await readFile(new URL('../src/pages/App.tsx', import.meta.url), 'utf8');
const api = await readFile(new URL('../src/auth/api.ts', import.meta.url), 'utf8');

test('Vastu page supports a floor-plan image, north-edge selection and user room markers', () => {
  assert.match(page, /type="file"/);
  assert.match(page, /northSide/);
  assert.match(page, /markRoom/);
  assert.match(page, /ROOM_TYPES/);
  assert.match(page, /does not automatically recognise room names or walls/);
});

test('Vastu is reachable from the main navigation and uses the authenticated API helper', () => {
  assert.match(app, /VastuPage/);
  assert.match(app, /#vastu/);
  assert.match(api, /analyzeVastuFloorPlan/);
  assert.match(api, /Authorization/);
});
