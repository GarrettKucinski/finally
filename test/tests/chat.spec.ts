import { test, expect } from '@playwright/test';

test.describe('AI Chat', () => {
  test('chat panel is visible on load', async ({ page }) => {
    await page.goto('/');
    await expect(page.getByText('AAPL')).toBeVisible({ timeout: 15000 });

    // The chat panel starts open (chatOpen defaults to true in Dashboard)
    // It should show the "AI Assistant" header
    await expect(page.getByText('AI Assistant')).toBeVisible();

    // The message input should be visible with placeholder "Ask FinAlly..."
    await expect(page.getByPlaceholder('Ask FinAlly...')).toBeVisible();
  });

  test('can collapse and reopen chat panel', async ({ page }) => {
    await page.goto('/');
    await expect(page.getByText('AI Assistant')).toBeVisible({ timeout: 15000 });

    // Click the collapse button (aria-label "Collapse chat")
    await page.getByLabel('Collapse chat').click();

    // The chat input should no longer be visible
    await expect(page.getByPlaceholder('Ask FinAlly...')).not.toBeVisible();

    // A floating "AI" button should appear to reopen
    await page.getByRole('button', { name: 'AI' }).click();

    // Chat panel should be visible again
    await expect(page.getByText('AI Assistant')).toBeVisible();
  });

  test('can send a message and receive mock AI response', async ({ page }) => {
    await page.goto('/');
    await expect(page.getByText('AI Assistant')).toBeVisible({ timeout: 15000 });

    // Type a message in the chat input
    const messageInput = page.getByPlaceholder('Ask FinAlly...');
    await messageInput.fill('What is my portfolio value?');

    // Send the message by pressing Enter
    await messageInput.press('Enter');

    // Wait for the mock AI response to appear
    // The mock returns: "Mock response: I received your message about 'What is my portfolio value?'. As a mock AI assistant, I can confirm the chat system is working correctly."
    await expect(page.getByText(/Mock response.*chat system is working correctly/)).toBeVisible({ timeout: 15000 });
  });

  test('user message appears in chat history', async ({ page }) => {
    await page.goto('/');
    await expect(page.getByText('AI Assistant')).toBeVisible({ timeout: 15000 });

    const messageInput = page.getByPlaceholder('Ask FinAlly...');
    await messageInput.fill('Hello FinAlly');

    // Click Send button instead of Enter
    await page.getByRole('button', { name: 'Send' }).click();

    // The user message should appear in the chat history
    await expect(page.getByText('Hello FinAlly')).toBeVisible({ timeout: 10000 });

    // The "You" label should appear for user messages
    await expect(page.getByText('You')).toBeVisible();

    // The "FinAlly" label should appear for assistant messages
    await expect(page.getByText('FinAlly').nth(1)).toBeVisible({ timeout: 15000 });
  });

  test('shows empty state message before any conversation', async ({ page }) => {
    await page.goto('/');
    await expect(page.getByText('AI Assistant')).toBeVisible({ timeout: 15000 });

    // Before any messages, the chat shows a placeholder prompt
    await expect(page.getByText(/Ask FinAlly about your portfolio/)).toBeVisible();
  });
});
