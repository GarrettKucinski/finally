import { test, expect } from '@playwright/test';

test.describe('Smoke Tests', () => {
  test('app loads and displays the dashboard', async ({ page }) => {
    await page.goto('/');
    // The page should load and render the FinAlly header brand
    await expect(page.getByText('FinAlly')).toBeVisible({ timeout: 15000 });
  });

  test('prices start streaming via SSE', async ({ page }) => {
    await page.goto('/');
    // Wait for at least one ticker to show in the watchlist with a price
    // AAPL is the first default ticker -- it should appear once SSE data arrives
    await expect(page.getByText('AAPL')).toBeVisible({ timeout: 15000 });
    // Verify a dollar-formatted price is displayed somewhere on the page
    await expect(page.getByText(/\$\d+\.\d{2}/)).toBeVisible({ timeout: 15000 });
  });

  test('shows starting cash balance', async ({ page }) => {
    await page.goto('/');
    // The header shows "Cash" label with the $10,000 starting balance
    await expect(page.getByText(/\$10,000/)).toBeVisible({ timeout: 15000 });
  });

  test('shows portfolio value in header', async ({ page }) => {
    await page.goto('/');
    // The header has a "Portfolio Value" label
    await expect(page.getByText('Portfolio Value')).toBeVisible({ timeout: 15000 });
  });

  test('connection status shows connected after SSE starts', async ({ page }) => {
    await page.goto('/');
    // Wait for SSE to connect -- status indicator should say "Connected"
    await expect(page.getByText('Connected')).toBeVisible({ timeout: 15000 });
  });
});
