import { expect, test } from '@playwright/test';

test('local AGPL development mode calculates Panchang through the authenticated UI and API', async ({ page }) => {
  test.skip(process.env.ASTROAI_E2E_LOCAL_CALCULATIONS !== 'true', 'Run with the explicit local-calculation opt-in');
  const email = `astroai-panchang-local-${Date.now()}@example.com`;
  const password = 'local-panchang-test-password-123';

  await page.goto('/');
  await page.getByRole('link', { name: /create account/i }).first().click();
  await page.getByLabel('Email address').fill(email);
  await page.getByLabel(/^Password/).fill(password);
  await page.getByLabel('Confirm password').fill(password);
  await page.getByRole('button', { name: /create account/i }).click();
  await expect(page).toHaveURL(/\/app$/);

  await page.getByRole('link', { name: 'Panchang' }).click();
  await page.getByLabel('Location name').fill('IMD Central Station reference');
  await page.getByLabel('Local date').fill('2026-03-22');
  await page.getByLabel('Latitude').fill(String(23 + 11 / 60));
  await page.getByLabel('Longitude').fill('82.5');
  await page.getByLabel('IANA timezone').fill('Asia/Kolkata');
  const calculation = page.waitForResponse(response => response.url().endsWith('/api/v1/panchang/daily'));
  await page.getByRole('button', { name: 'Calculate Panchang' }).click();
  const response = await calculation;
  expect(response.status()).toBe(200);
  const result = await response.json();
  expect(result.tithi).toEqual({ index: 4, name: 'Chaturthi', paksha: 'Shukla' });
  expect(result.vara.name).toBe('Sunday');
  expect(result.nakshatra.name).toBe('Bharani');
  expect(result.yoga.name).toBe('Vaidhriti');
  expect(result.karana.name).toBe('Vanija');
  expect(Object.keys(result.transitions).sort()).toEqual(['karana', 'nakshatra', 'tithi', 'yoga']);
  expect(Object.values(result.transitions).every(transition => Date.parse(transition.at) > Date.parse(result.sunrise))).toBe(true);
  expect(Object.keys(result.daytime_windows).sort()).toEqual(['abhijit_muhurta', 'gulika_kalam', 'rahu_kalam', 'yamagandam']);
  expect(result.calculated_at).toBeTruthy();
  expect(result.calculation.ephemeris).toBe('Swiss Ephemeris files only; Moshier fallback refused');
  await expect(page.getByText('IMD Central Station reference')).toBeVisible();
  await expect(page.getByText('Shukla Chaturthi')).toBeVisible();
  await expect(page.getByText('Bharani')).toBeVisible();
});
