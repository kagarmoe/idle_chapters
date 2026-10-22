import { expect, test } from '@playwright/test';

test('the web client asks the API for the player projection', async ({ page }) => {
	// Only the request matters here; the stub body is not a real session, so the page may show its error screen.
	await page.route('**/v1/sessions', (route) => route.fulfill({ status: 200, json: {} }));
	await page.goto('/play/idle-chapters');
	const newGame = page.getByRole('button', { name: /New Game/ });
	await expect(newGame).toBeVisible({ timeout: 10_000 });

	const created = page.waitForRequest(
		(request) => request.method() === 'POST' && new URL(request.url()).pathname === '/v1/sessions'
	);
	await newGame.click();

	expect((await created).headers()['accept-projection']).toBe('player');
});

test('the web client calls the API on its own origin', async ({ page }) => {
	// The build sets VITE_API_URL to an unreachable host (playwright.config.ts); the client must ignore it.
	await page.route('**/v1/sessions', (route) => route.fulfill({ status: 200, json: {} }));
	await page.goto('/play/idle-chapters');
	const newGame = page.getByRole('button', { name: /New Game/ });
	await expect(newGame).toBeVisible({ timeout: 10_000 });

	const created = page.waitForRequest(
		(request) => request.method() === 'POST' && new URL(request.url()).pathname === '/v1/sessions'
	);
	await newGame.click();

	expect(new URL((await created).url()).origin).toBe(new URL(page.url()).origin);
});
