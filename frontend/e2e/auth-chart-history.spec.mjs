import { expect, test } from '@playwright/test';
import { readFile, unlink } from 'node:fs/promises';
import { join } from 'node:path';
import { tmpdir } from 'node:os';

const apiBase = process.env.ASTROAI_E2E_API_BASE_URL ?? `http://127.0.0.1:${process.env.ASTROAI_E2E_API_PORT ?? '8000'}/api/v1`;

async function selectBirthTime(page, hour, minute, meridiem) {
  await page.getByLabel('Hour').selectOption(hour);
  await page.getByLabel('Minute').selectOption(minute);
  await page.getByLabel('AM/PM').selectOption(meridiem);
}

test('local Vedic D1 and D9 calculations persist and reopen through the authenticated UI and API', async ({ page }) => {
  test.skip(process.env.ASTROAI_E2E_LOCAL_CALCULATIONS !== 'true', 'Requires explicitly enabled loopback-only local Swiss Ephemeris development runtime');
  const email = `astroai-vedic-local-${Date.now()}@example.com`;
  const password = 'local-chart-test-password-123';
  await page.goto('/');
  await page.getByRole('link', { name: /create account/i }).first().click();
  await page.getByLabel('Email address').fill(email);
  await page.getByLabel(/^Password/).fill(password);
  await page.getByLabel('Confirm password').fill(password);
  await page.getByRole('button', { name: /create account/i }).click();
  await expect(page).toHaveURL(/\/app$/);

  await page.getByRole('link', { name: 'Birth chart' }).click();
  await page.getByRole('button', { name: 'Manage birth profiles' }).click();
  await page.getByRole('button', { name: 'Add profile' }).click();
  await page.getByLabel('Display name').fill('Local Vedic test profile');
  await page.getByLabel('Date of birth').fill('2000-01-01');
  await page.getByLabel('Birth time accuracy').selectOption('exact');
  await selectBirthTime(page, '05', '30', 'PM');
  await page.getByLabel('Birthplace').fill('Chennai');
  await page.getByLabel('Country').fill('India');
  await page.getByLabel('Latitude').fill('13.0827');
  await page.getByLabel('Longitude').fill('80.2707');
  await page.getByLabel('IANA timezone').fill('Asia/Kolkata');
  const profileResponse = page.waitForResponse(response => response.url().endsWith('/api/v1/profiles') && response.request().method() === 'POST');
  await page.getByRole('button', { name: 'Save profile' }).click();
  const profile = await (await profileResponse).json();
  await page.getByRole('link', { name: 'Birth chart' }).click();
  await expect(page.getByLabel('Birth profile')).toHaveValue(profile.id);
  await expect(page.getByLabel('Chart division')).toHaveValue('D1');

  const token = await page.evaluate(() => sessionStorage.getItem('astroai_access_token'));
  const d1ResponsePromise = page.waitForResponse(response => response.url().endsWith('/api/v1/astrology/charts/vedic') && response.request().method() === 'POST');
  await page.getByRole('button', { name: /calculate chart/i }).click();
  const d1Response = await d1ResponsePromise;
  expect(d1Response.status()).toBe(201);
  const d1 = await d1Response.json();
  expect(d1.status).toBe('complete');
  expect(d1.result.planets).toHaveLength(12);
  expect(d1.result.planets.every(planet => Number.isFinite(planet.longitude) && Number.isInteger(planet.house) && planet.house >= 1 && planet.house <= 12 && planet.rashi && planet.nakshatra?.name && planet.nakshatra.pada >= 1 && planet.nakshatra.pada <= 4)).toBe(true);
  expect(d1.result.ascendant.longitude).toEqual(expect.any(Number));
  expect(d1.result.vimshottari_dasha.year_convention).toBe('savana_360_day');
  expect(d1.result.vimshottari_dasha.pratyantardashas.length).toBeGreaterThan(0);
  await expect(page.getByRole('heading', { name: 'Planet placements' })).toBeVisible();
  await expect(page.locator('.chart-data-section').filter({ has: page.getByRole('heading', { name: 'Planet placements' }) }).locator('tbody tr')).toHaveCount(12);

  await page.getByLabel('Chart division').selectOption('D9');
  const d9ResponsePromise = page.waitForResponse(response => response.url().endsWith('/api/v1/astrology/charts/vedic') && response.request().method() === 'POST');
  await page.getByRole('button', { name: /calculate chart/i }).click();
  const d9Response = await d9ResponsePromise;
  expect(d9Response.status()).toBe(201);
  const d9 = await d9Response.json();
  expect(d9.result.division).toBe('D9');
  expect(d9.result.division_houses).toHaveLength(12);
  expect(d9.result.planets.every(planet => planet.division_rashi && Number.isInteger(planet.division_house) && planet.division_house >= 1 && planet.division_house <= 12)).toBe(true);
  expect(d9.result.configuration.d9_house_convention).toBeTruthy();

  const saved = await page.request.get(`${apiBase}/astrology/charts/${d9.chart_id}`, { headers: { Authorization: `Bearer ${token}` } });
  expect(saved.status()).toBe(200);
  expect((await saved.json()).result).toEqual(d9.result);
  await page.reload();
  await page.getByRole('link', { name: 'Birth chart' }).click();
  await expect(page.getByRole('heading', { name: 'Saved chart history' })).toBeVisible();
  await expect(page.locator('.chart-history-item').filter({ hasText: 'D9' }).first()).toBeVisible();
  await page.locator('.chart-history-item').filter({ hasText: 'D9' }).first().click();
  await expect(page.getByRole('heading', { name: 'Planet placements' })).toBeVisible();
  await expect(page.locator('.chart-data-section').filter({ has: page.getByRole('heading', { name: 'Planet placements' }) }).locator('tbody tr')).toHaveCount(12);

  await page.getByRole('link', { name: 'Astrologer chat' }).click();
  await page.getByLabel('Birth profile').selectOption(profile.id);
  await page.getByLabel('Astrology system').selectOption('vedic');
  await page.getByLabel('Saved calculated chart').selectOption('');
  const educationalTurns = [
    ['What is a Nakshatra?', '27 Nakshatras'],
    ['How many Padas does each Nakshatra have?', 'four Padas'],
    ['Can you explain Ashwini Nakshatra in detail?', 'Nakshatra number 1'],
    ['What is its ruling planet?', 'assigned to Ketu'],
    ['How is it used in Vedic birth chart interpretation?', 'not your chart'],
  ];
  for (const [question, answer] of educationalTurns) {
    const input = page.getByLabel('Ask about your chart…');
    await input.fill(question);
    await input.press('Enter');
    await expect(page.locator('.ai-message.assistant').last()).toContainText(answer);
  }
  await expect(page.locator('.ai-message.user')).toHaveCount(educationalTurns.length);
});

test('signup, create profile, chart gates and history persist across logout/login', async ({ page }) => {
  test.skip(process.env.ASTROAI_E2E_LOCAL_CALCULATIONS === 'true', 'This journey asserts disabled calculation gates; enabled local calculation flows have a separate journey');
  const email = `astroai-e2e-${Date.now()}@example.com`;
  const password = 'e2e-private-password-123';

  await page.goto('/');
  await page.getByRole('link', { name: /create account/i }).first().click();
  await page.getByLabel('Email address').fill(email);
  await page.getByLabel(/^Password/).fill(password);
  await page.getByLabel('Confirm password').fill(password);
  await page.getByRole('button', { name: /create account/i }).click();
  await expect(page).toHaveURL(/\/app$/);

  await page.getByRole('link', { name: 'Birth chart' }).click();
  await expect(page.getByText('Add a birth profile to begin')).toBeVisible();

  await page.route('**/api/v1/profiles', route => route.abort());
  await page.reload();
  await page.getByRole('link', { name: 'Birth chart' }).click();
  await expect(page.getByRole('alert')).toContainText(/failed to fetch|network/i);
  await page.unroute('**/api/v1/profiles');
  await page.getByRole('button', { name: 'Try again' }).click();
  await expect(page.getByText('Add a birth profile to begin')).toBeVisible();

  await page.getByRole('button', { name: 'Manage birth profiles' }).click();
  await page.getByRole('button', { name: 'Add profile' }).click();
  await page.route('**/api/v1/profiles/location-search**', route => route.fulfill({ json: [
    { id: 'nagercoil-india', city: 'Nagercoil', region: 'Tamil Nadu', country: 'India', latitude: 8.1833, longitude: 77.4119, timezone: 'Asia/Kolkata', attribution: 'Geoapify · © OpenStreetMap contributors' },
    { id: 'nagercoil-other', city: 'Nagercoil', region: 'Other State', country: 'Other Country', latitude: 10.2, longitude: 70.3, timezone: null, attribution: 'Geoapify · © OpenStreetMap contributors' },
  ] }));
  await page.getByLabel('Display name').fill('E2E profile');
  await page.getByLabel('Date of birth').fill('1990-05-14');
  await page.getByLabel('Birth time accuracy').selectOption('exact');
  await selectBirthTime(page, '08', '30', 'PM');
  await page.getByLabel('Birthplace').fill('Nagercoil');
  const suggestions = page.getByRole('listbox', { name: 'Place suggestions' });
  await expect(suggestions.getByRole('option')).toHaveCount(2);
  await expect(suggestions.getByRole('option').first()).toContainText('Tamil Nadu, India');
  await expect(suggestions.getByRole('option').nth(1)).toContainText('Other State, Other Country');
  await expect(page.getByLabel('Latitude')).toHaveValue('');
  await suggestions.getByRole('option').first().click();
  await expect(page.getByLabel('Country')).toHaveValue('India');
  await expect(page.getByLabel('Latitude')).toHaveValue('8.1833');
  await expect(page.getByLabel('IANA timezone')).toHaveValue('Asia/Kolkata');
  await page.getByLabel('Longitude').fill('77.4120');
  const profileResponse = page.waitForResponse(response => response.url().endsWith('/api/v1/profiles') && response.request().method() === 'POST');
  await page.getByRole('button', { name: 'Save profile' }).click();
  const profile = await (await profileResponse).json();
  expect(profile.birth_time).toBe('20:30:00');
  expect(profile.latitude).toBe(8.1833);
  expect(profile.longitude).toBe(77.412);
  await page.getByRole('button', { name: 'Edit E2E profile' }).click();
  await expect(page.getByLabel('Hour')).toHaveValue('08');
  await expect(page.getByLabel('Minute')).toHaveValue('30');
  await expect(page.getByLabel('AM/PM')).toHaveValue('PM');
  await page.getByRole('button', { name: 'Cancel' }).click();
  await expect(page.getByText('E2E profile', { exact: true })).toBeVisible();

  await page.getByRole('link', { name: 'Horoscope' }).click();
  await expect(page.getByRole('heading', { name: 'Horoscope' })).toBeVisible();
  await expect(page.getByText(/No content is shown unless it exactly matches the selected tradition/)).toBeVisible();
  await page.getByRole('button', { name: 'Check availability' }).click();
  await expect(page.getByRole('status')).toContainText(/horoscope catalogue is empty/i);
  await expect(page.getByRole('status')).toContainText('catalogue_empty');
  await page.getByLabel('Reading type').selectOption('personalized');
  await expect(page.getByRole('button', { name: 'Check availability' })).toBeDisabled();
  await expect(page.getByText(/A completed saved chart for the selected profile and system is required/)).toBeVisible();
  await page.getByRole('link', { name: 'Panchang' }).click();
  await expect(page.getByRole('heading', { name: 'Daily Panchang' })).toBeVisible();
  await page.getByLabel('Saved profile location').selectOption(profile.id);
  await page.getByRole('button', { name: 'Calculate Panchang' }).click();
  await expect(page.getByRole('alert')).toContainText(/calculations are currently disabled intentionally/i);
  await expect(page.getByRole('alert')).toContainText(/No calculation was performed and no chart was saved/i);
  await page.getByRole('link', { name: 'Compatibility' }).click();
  await expect(page.getByRole('heading', { name: 'Compatibility' })).toBeVisible();
  await expect(page.getByText(/never estimates a score from names or birth details/)).toBeVisible();

  await page.getByRole('link', { name: 'Birth chart' }).click();
  await expect(page.getByLabel('Birth profile')).toHaveValue(profile.id);
  await expect(page.getByLabel('Chart division')).toHaveValue('D1');
  await page.getByLabel('Chart division').selectOption('D9');
  await expect(page.getByLabel('Chart division')).toHaveValue('D9');
  await page.getByLabel('Chart division').selectOption('D1');

  await page.getByRole('button', { name: /calculate chart/i }).click();
  await expect(page.getByRole('alert')).toContainText('Chart calculation unavailable');
  await expect(page.getByRole('alert')).toContainText(/disabled intentionally/i);
  await expect(page.getByRole('alert').getByRole('button', { name: 'Try again' })).toHaveCount(0);
  await page.getByLabel('Astrology system').selectOption('western');
  await page.getByRole('button', { name: /calculate chart/i }).click();
  await expect(page.getByRole('alert')).toContainText('Chart calculation unavailable');

  // With calculation gates disabled, seed only an unavailable chart record via the existing
  // authenticated endpoint so the history journey uses real persisted API data, not a chart fixture.
  const token = await page.evaluate(() => sessionStorage.getItem('astroai_access_token'));
  const saved = await page.request.post(`${apiBase}/astrology/charts`, {
    headers: { Authorization: `Bearer ${token}` },
    data: { profile_id: profile.id, system: 'vedic', division: 'D1' },
  });
  expect(saved.status()).toBe(202);
  await page.getByLabel('Astrology system').selectOption('vedic');
  await expect(page.getByRole('heading', { name: 'Saved chart history' })).toBeVisible();
  await expect(page.locator('.chart-history-item')).toContainText('E2E profile');
  await page.locator('.chart-history-item').first().click();
  await expect(page.getByRole('alert')).toContainText('Chart calculation unavailable');

  await page.getByRole('link', { name: 'Astrologer chat' }).click();
  await expect(page.getByRole('heading', { name: 'AI astrologer' })).toBeVisible();
  await page.getByLabel('Birth profile').selectOption(profile.id);
  await page.getByLabel('Astrology system').selectOption('vedic');
  await expect(page.getByLabel('Saved calculated chart')).toHaveValue('');
  await page.getByLabel('Ask about your chart…').fill('What can you tell me about my birth chart?');
  const conversationRequest = page.waitForRequest(request => request.url().endsWith('/api/v1/ai/conversations') && request.method() === 'POST');
  const chatRequest = page.waitForRequest(request => request.url().includes('/api/v1/ai/conversations/') && request.url().endsWith('/messages/stream'));
  const chatResponse = page.waitForResponse(response => response.url().includes('/api/v1/ai/conversations/') && response.url().endsWith('/messages/stream'));
  await page.getByRole('button', { name: 'Send' }).click();
  const createdConversation = await conversationRequest;
  expect(createdConversation.postDataJSON()).toEqual({ profile_id: profile.id, chart_id: null, astrology_system: 'vedic', language: 'en' });
  const sentRequest = await chatRequest;
  expect(sentRequest.postDataJSON()).toEqual({ content: 'What can you tell me about my birth chart?' });
  const stream = await chatResponse;
  expect(await stream.text()).toContain('"status": "missing_chart"');
  await expect(page.getByText(/completed saved chart is required before personalized interpretation/i)).toBeVisible();
  await expect(page.getByText(/Visit Birth chart to calculate and save one first/i)).toBeVisible();
  await expect(page.locator('.ai-message.user p')).toHaveText('What can you tell me about my birth chart?');
  const firstUserToken = await page.evaluate(() => sessionStorage.getItem('astroai_access_token'));
  const firstConversations = await page.request.get(`${apiBase}/ai/conversations`, {
    headers: { Authorization: `Bearer ${firstUserToken}` },
  });
  const firstConversation = (await firstConversations.json()).items[0];
  expect(firstConversation).toBeTruthy();

  await page.getByRole('button', { name: 'Log out' }).click();
  await expect(page).toHaveURL(/\/login$/);
  await page.getByLabel('Email address').fill(email);
  await page.getByRole('textbox', { name: 'Password' }).fill(password);
  await page.getByRole('button', { name: /^Log in/ }).click();
  await expect(page).toHaveURL(/\/app$/);
  await page.getByRole('link', { name: 'Birth chart' }).click();
  await expect(page.getByRole('heading', { name: 'Saved chart history' })).toBeVisible();
  await expect(page.locator('.chart-history-item')).toContainText('E2E profile');

  await page.getByRole('link', { name: 'Astrologer chat' }).click();
  await expect(page.locator('.ai-conversation-select')).toContainText('What can you tell me about my birth chart?');
  await page.locator('.ai-conversation-select').click();
  await expect(page.getByText(/completed saved chart is required before personalized interpretation/i)).toBeVisible();
  await page.getByRole('button', { name: 'தமிழுக்கு மாற்று' }).click();
  await expect(page.getByRole('heading', { name: 'AI ஜோதிடர்' })).toBeVisible();

  const secondEmail = `astroai-e2e-isolation-${Date.now()}@example.com`;
  const secondPassword = 'e2e-isolation-password-123';
  const registration = await page.request.post(`${apiBase}/auth/register`, {
    data: { email: secondEmail, password: secondPassword },
  });
  expect(registration.status()).toBe(201);
  const secondLogin = await page.request.post(`${apiBase}/auth/login`, {
    form: { username: secondEmail, password: secondPassword },
  });
  expect(secondLogin.status()).toBe(200);
  const secondToken = (await secondLogin.json()).access_token;
  const privateConversation = await page.request.get(`${apiBase}/ai/conversations/${firstConversation.id}`, {
    headers: { Authorization: `Bearer ${secondToken}` },
  });
  expect(privateConversation.status()).toBe(404);
  const secondProfiles = await page.request.get(`${apiBase}/profiles`, {
    headers: { Authorization: `Bearer ${secondToken}` },
  });
  const secondProfilePayload = await secondProfiles.json();
  const secondProfileRows = Array.isArray(secondProfilePayload) ? secondProfilePayload : secondProfilePayload.items;
  expect(secondProfileRows.map(item => item.id)).not.toContain(profile.id);
  await page.getByRole('button', { name: /உரையாடலை நீக்கு/ }).click();
  await expect(page.locator('.ai-conversation-row')).toHaveCount(0);

  await page.getByRole('button', { name: 'Log out' }).click();
  await expect(page).toHaveURL(/\/login$/);
  const englishToggle = page.getByRole('button', { name: 'Switch to English' });
  await expect(englishToggle).toBeVisible();
  await englishToggle.click();
  await expect(page.getByRole('link', { name: 'Forgot password?' })).toBeVisible();
  await page.getByRole('link', { name: 'Forgot password?' }).click();
  await expect(page.getByRole('heading', { name: 'Reset your password' })).toBeVisible();
  await page.getByLabel('Email address').fill(email);
  const forgotResponse = page.waitForResponse(response => response.url().endsWith('/api/v1/auth/forgot-password'));
  await page.getByRole('button', { name: /send reset instructions/i }).click();
  expect((await forgotResponse).status()).toBe(202);
  await expect(page.getByRole('status')).toContainText(/If the address is registered and email delivery is available/i);
  const resetLinkFile = join(tmpdir(), 'astroai-e2e-password-reset-link.txt');
  const resetUrl = (await readFile(resetLinkFile, 'utf8')).trim();
  await unlink(resetLinkFile);
  expect(resetUrl).toContain('/reset-password#token=');
  expect(resetUrl).not.toMatch(/api\/v1/);
  await page.goto(resetUrl);
  await page.getByLabel('New password', { exact: true }).fill('e2e-updated-password-789');
  await page.getByLabel('Confirm new password').fill('e2e-updated-password-789');
  const resetResponse = page.waitForResponse(response => response.url().endsWith('/api/v1/auth/reset-password'));
  await page.getByRole('button', { name: /update password/i }).click();
  expect((await resetResponse).status()).toBe(200);
  await expect(page.getByRole('status')).toContainText(/password has been updated/i);
  await page.getByRole('link', { name: 'Back to log in' }).click();
  await page.getByLabel('Email address').fill(email);
  await page.getByRole('textbox', { name: 'Password' }).fill('e2e-updated-password-789');
  await page.getByRole('button', { name: /^Log in/ }).click();
  await expect(page).toHaveURL(/\/app$/);
  const revokedToken = await page.request.get(`${apiBase}/auth/me`, {
    headers: { Authorization: `Bearer ${firstUserToken}` },
  });
  expect(revokedToken.status()).toBe(401);

  await page.evaluate(() => sessionStorage.setItem('astroai_access_token', 'expired.invalid.token'));
  await page.reload();
  await expect(page).toHaveURL(/\/login$/);
});
