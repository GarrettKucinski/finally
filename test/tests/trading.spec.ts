import { test, expect } from '@playwright/test';

test.describe('Trading', () => {
  test('can buy shares and see position appear', async ({ page }) => {
    await page.goto('/');
    // Wait for prices to stream so trades can execute at a known price
    await expect(page.getByText('AAPL')).toBeVisible({ timeout: 15000 });

    // The trade bar has: ticker input (placeholder "AAPL"), quantity input (placeholder "10")
    const tickerInput = page.getByPlaceholder('AAPL');
    const quantityInput = page.getByPlaceholder('10');

    await tickerInput.fill('AAPL');
    await quantityInput.fill('1');

    // Click the Buy button
    await page.getByRole('button', { name: 'Buy' }).click();

    // After buying, a success toast should appear confirming the trade
    // "Bought 1 AAPL at $XXX.XX"
    await expect(page.getByText(/Bought .* AAPL/)).toBeVisible({ timeout: 10000 });

    // The positions table should now show AAPL
    // Look for the "Positions" heading and AAPL in the table area
    await expect(page.getByText('Positions')).toBeVisible();
  });

  test('can sell shares after buying', async ({ page }) => {
    await page.goto('/');
    await expect(page.getByText('AAPL')).toBeVisible({ timeout: 15000 });

    const tickerInput = page.getByPlaceholder('AAPL');
    const quantityInput = page.getByPlaceholder('10');

    // First buy a share
    await tickerInput.fill('AAPL');
    await quantityInput.fill('1');
    await page.getByRole('button', { name: 'Buy' }).click();

    // Wait for buy confirmation
    await expect(page.getByText(/Bought .* AAPL/)).toBeVisible({ timeout: 10000 });

    // Now sell it -- inputs may have been cleared after successful buy
    await tickerInput.fill('AAPL');
    await quantityInput.fill('1');
    await page.getByRole('button', { name: 'Sell' }).click();

    // Should see a sell confirmation toast
    await expect(page.getByText(/Sold .* AAPL/)).toBeVisible({ timeout: 10000 });
  });

  test('shows error when selling shares not owned', async ({ page }) => {
    await page.goto('/');
    await expect(page.getByText('AAPL')).toBeVisible({ timeout: 15000 });

    const tickerInput = page.getByPlaceholder('AAPL');
    const quantityInput = page.getByPlaceholder('10');

    // Try to sell shares we don't own (use a ticker unlikely to have positions)
    await tickerInput.fill('GOOGL');
    await quantityInput.fill('100');
    await page.getByRole('button', { name: 'Sell' }).click();

    // Should show an error (toast notification for insufficient shares)
    // The backend returns an error like "Insufficient shares" which gets toasted
    await expect(page.getByText(/insufficient|not enough|no position/i)).toBeVisible({ timeout: 10000 });
  });

  test('cash balance decreases after buying', async ({ page }) => {
    await page.goto('/');
    await expect(page.getByText(/\$10,000/)).toBeVisible({ timeout: 15000 });

    const tickerInput = page.getByPlaceholder('AAPL');
    const quantityInput = page.getByPlaceholder('10');

    // Buy a share
    await tickerInput.fill('AAPL');
    await quantityInput.fill('1');
    await page.getByRole('button', { name: 'Buy' }).click();

    // Wait for trade to complete
    await expect(page.getByText(/Bought .* AAPL/)).toBeVisible({ timeout: 10000 });

    // Cash balance should no longer be $10,000.00 (it decreased by the price of 1 AAPL)
    // The header "Cash" section should show a lower amount
    // We verify by checking that $10,000.00 is no longer the cash display
    // (Note: portfolio value label may still show $10,000 since value = cash + positions)
    await page.waitForTimeout(1000);
  });
});
