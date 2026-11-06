import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
const page = await readFile(new URL('../src/astrology/VastuPage.tsx', import.meta.url), 'utf8');
const api = await readFile(new URL('../src/auth/api.ts', import.meta.url), 'utf8');
test('Vastu requires four selected building corners before room marking or review', () => {
  assert.match(page, /boundaryMode/); assert.match(page, /Mark the building boundary/);
  assert.match(page, /boundary\.length !== 4/); assert.match(page, /vastu-boundary-overlay/);
  assert.match(page, /clockwise, starting at the top-left corner/);
});
test('Vastu submits the selected boundary with authenticated multipart data', () => {
  assert.match(api, /VastuBoundaryPoint/); assert.match(api, /form\.append\('boundary', JSON\.stringify\(boundary\)\)/);
  assert.match(api, /Authorization: `Bearer \$\{token\}`/); assert.match(page, /, boundary\)/);
});
