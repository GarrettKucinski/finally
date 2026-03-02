import { test, expect } from '@playwright/test';

test.describe('Watchlist', () => {
  test('default watchlist shows 10 tickers', async ({ page }) => {
    await page.goto('/');
    // Wait for SSE prices to populate the watchlist
    await expect(page.getByText('AAPL')).toBeVisible({ timeout: 15000 });

    // Verify all 10 default tickers are present
    const tickers = ['AAPL', 'GOOGL', 'MSFT', 'AMZN', 'TSLA', 'NVDA', 'META', 'JPM', 'V', 'NFLX'];
    for (const ticker of tickers) {
      await expect(page.getByText(ticker, { exact: true }).first()).toBeVisible();
    }
  });

  test('watchlist shows live prices with dollar amounts', async ({ page }) => {
    await page.goto('/');
    await expect(page.getByText('AAPL')).toBeVisible({ timeout: 15000 });

    // Prices should be displayed as dollar amounts (e.g., $190.xx)
    // Look for at least one price pattern on the page
    await expect(page.getByText(/\$\d+\.\d{2}/).first()).toBeVisible();
  });

  test('watchlist header is visible', async ({ page }) => {
    await page.goto('/');
    // The watchlist panel has a "Watchlist" heading
    await expect(page.getByText('Watchlist')).toBeVisible({ timeout: 15000 });
  });
});
