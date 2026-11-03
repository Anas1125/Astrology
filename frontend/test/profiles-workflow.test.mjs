import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';

const read = path => readFile(new URL(path, import.meta.url), 'utf8');

test('birth profile API exposes authenticated list/create/update/delete operations', async () => {
  const api = await read('../src/auth/api.ts');
  assert.match(api, /listBirthProfiles/);
  assert.match(api, /createBirthProfile/);
  assert.match(api, /updateBirthProfile/);
  assert.match(api, /deleteBirthProfile/);
  assert.match(api, /Authorization: `Bearer \$\{token\}`/);
});

test('birth profile form captures birth and manual location fields and renders workflow states', async () => {
  const page = await read('../src/pages/ProfilesPage.tsx');
  for (const field of ['display_name', 'relationship', 'birth_date', 'birth_time', 'time_accuracy', 'birthplace', 'latitude', 'longitude', 'timezone']) {
    assert.match(page, new RegExp(field));
  }
  assert.match(page, /Loading birth profiles/);
  assert.match(page, /No birth profiles yet/);
  assert.match(page, /window\.confirm/);
  assert.match(page, /Birth profile created/);
  assert.match(page, /Birth profile updated/);
  assert.match(page, /Birth profile deleted/);
});

test('dashboard shows the live profiles module instead of the prior local-only form', async () => {
  const app = await read('../src/pages/App.tsx');
  assert.match(app, /<ProfilesPage language=\{language\}\/>/);
});
