import { expect, test } from '@playwright/test';

test('splash menu appears after the title art reveals', async ({ page }) => {
	await page.goto('/play/idle-chapters');
	await expect(page.getByRole('button', { name: /New Game/ })).toBeVisible({ timeout: 10_000 });
});
