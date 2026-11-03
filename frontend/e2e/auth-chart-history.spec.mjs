import { expect, test } from '@playwright/test';

test('signup, create profile, chart gates and history persist across logout/login', async ({ page }) => {
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
  await page.getByLabel('Display name').fill('E2E profile');
  await page.getByLabel('Date of birth').fill('1990-05-14');
  await page.getByLabel('Birth time accuracy').selectOption('exact');
  await page.getByLabel('Birth time', { exact: true }).fill('08:30');
  await page.getByLabel('Birthplace').fill('Chennai');
  await page.getByLabel('Country').fill('India');
  await page.getByLabel('Latitude').fill('13.0827');
  await page.getByLabel('Longitude').fill('80.2707');
  await page.getByLabel('IANA timezone').fill('Asia/Kolkata');
  const profileResponse = page.waitForResponse(response => response.url().endsWith('/api/v1/profiles') && response.request().method() === 'POST');
  await page.getByRole('button', { name: 'Save profile' }).click();
  const profile = await (await profileResponse).json();
  await expect(page.getByText('E2E profile', { exact: true })).toBeVisible();

  await page.getByRole('link', { name: 'Birth chart' }).click();
  await expect(page.getByLabel('Birth profile')).toHaveValue(profile.id);
  await expect(page.getByLabel('Chart division')).toHaveValue('D1');
  await page.getByLabel('Chart division').selectOption('D9');
  await expect(page.getByLabel('Chart division')).toHaveValue('D9');
  await page.getByLabel('Chart division').selectOption('D1');

  await page.getByRole('button', { name: /calculate chart/i }).click();
  await expect(page.getByRole('alert')).toContainText('Chart calculation unavailable');
  await page.getByLabel('Astrology system').selectOption('western');
  await page.getByRole('button', { name: /calculate chart/i }).click();
  await expect(page.getByRole('alert')).toContainText('Chart calculation unavailable');

  // With calculation gates disabled, seed only an unavailable chart record via the existing
  // authenticated endpoint so the history journey uses real persisted API data, not a chart fixture.
  const token = await page.evaluate(() => sessionStorage.getItem('astroai_access_token'));
  const saved = await page.request.post('http://127.0.0.1:8000/api/v1/astrology/charts', {
    headers: { Authorization: `Bearer ${token}` },
    data: { profile_id: profile.id, system: 'vedic', division: 'D1' },
  });
  expect(saved.status()).toBe(202);
  await page.getByLabel('Astrology system').selectOption('vedic');
  await expect(page.getByRole('heading', { name: 'Saved chart history' })).toBeVisible();
  await expect(page.locator('.chart-history-item')).toContainText('E2E profile');
  await page.locator('.chart-history-item').first().click();
  await expect(page.getByRole('alert')).toContainText('Chart calculation unavailable');

  await page.getByRole('link', { name: 'AI astrologer' }).click();
  await expect(page.getByRole('heading', { name: 'AI astrologer' })).toBeVisible();
  await page.getByLabel('Birth profile').selectOption(profile.id);
  await page.getByLabel('Astrology system').selectOption('western');
  await expect(page.getByLabel('Saved calculated chart')).toHaveValue('');
  await page.getByLabel('Ask about your chart…').fill('In my Western natal chart, where is my Moon?');
  await page.getByRole('button', { name: 'Send' }).click();
  await expect(page.getByText('A completed saved chart for this profile and system is not available.', { exact: false })).toBeVisible();
  await expect(page.locator('.ai-message.user p')).toHaveText('In my Western natal chart, where is my Moon?');
  const firstUserToken = await page.evaluate(() => sessionStorage.getItem('astroai_access_token'));
  const firstConversations = await page.request.get('http://127.0.0.1:8000/api/v1/ai/conversations', {
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

  await page.getByRole('link', { name: 'AI astrologer' }).click();
  await expect(page.locator('.ai-conversation-select')).toContainText('In my Western natal chart, where is my Moon?');
  await page.locator('.ai-conversation-select').click();
  await expect(page.getByText('A completed saved chart for this profile and system is not available.', { exact: false })).toBeVisible();
  await page.getByRole('button', { name: 'தமிழுக்கு மாற்று' }).click();
  await expect(page.getByRole('heading', { name: 'AI ஜோதிடர்' })).toBeVisible();

  const secondEmail = `astroai-e2e-isolation-${Date.now()}@example.com`;
  const secondPassword = 'e2e-isolation-password-123';
  const registration = await page.request.post('http://127.0.0.1:8000/api/v1/auth/register', {
    data: { email: secondEmail, password: secondPassword },
  });
  expect(registration.status()).toBe(201);
  const secondLogin = await page.request.post('http://127.0.0.1:8000/api/v1/auth/login', {
    form: { username: secondEmail, password: secondPassword },
  });
  expect(secondLogin.status()).toBe(200);
  const secondToken = (await secondLogin.json()).access_token;
  const privateConversation = await page.request.get(`http://127.0.0.1:8000/api/v1/ai/conversations/${firstConversation.id}`, {
    headers: { Authorization: `Bearer ${secondToken}` },
  });
  expect(privateConversation.status()).toBe(404);
  const secondProfiles = await page.request.get('http://127.0.0.1:8000/api/v1/profiles', {
    headers: { Authorization: `Bearer ${secondToken}` },
  });
  const secondProfilePayload = await secondProfiles.json();
  const secondProfileRows = Array.isArray(secondProfilePayload) ? secondProfilePayload : secondProfilePayload.items;
  expect(secondProfileRows.map(item => item.id)).not.toContain(profile.id);
  await page.getByRole('button', { name: /உரையாடலை நீக்கு/ }).click();
  await expect(page.locator('.ai-conversation-row')).toHaveCount(0);

  await page.evaluate(() => sessionStorage.setItem('astroai_access_token', 'expired.invalid.token'));
  await page.reload();
  await expect(page).toHaveURL(/\/login$/);
});
