import { expect, test } from '@playwright/test';

test('a handled API error still reaches the logs, once', async ({ page }) => {
	const reports: Record<string, unknown>[] = [];
	await page.addInitScript(() => localStorage.setItem('idle-chapters-session-id', 's1'));
	await page.route('**/v1/sessions/s1', (route) =>
		route.fulfill({ status: 503, json: { type: 'urn:idle-chapters:error:persistence_failure', title: 'The world rests.', status: 503 } })
	);
	await page.route('**/v1/client-errors', (route) => {
		reports.push(route.request().postDataJSON());
		return route.fulfill({ status: 204 });
	});

	await page.goto('/play/idle-chapters');
	await page.getByRole('button', { name: /Continue/ }).click({ timeout: 10_000 });
	await expect(page.getByText('The world rests.')).toBeVisible();

	await expect.poll(() => reports.length).toBe(1);
	expect(reports[0]).toMatchObject({ level: 'warning', kind: 'ApiError', message: '503 The world rests.', path: '/play/idle-chapters' });
});
