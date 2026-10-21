import { expect, test, type Page } from '@playwright/test';

const view = (actions: { action_id: string; label: string }[]) => ({
	prompt: 'The kettle ticks as it cools.',
	scene_id: 'cottage_wake_v1',
	eligible_actions: actions,
	visible_items: [],
	visible_npcs: []
});

async function stubSavedSession(page: Page, actions: { action_id: string; label: string }[]) {
	const entered: string[] = [];
	await page.addInitScript(() => localStorage.setItem('idle-chapters-session-id', 's1'));
	await page.route('**/v1/sessions/s1', (route) =>
		route.fulfill({ json: { session_id: 's1', view: view(actions), journal_page: null, state: null } })
	);
	await page.route('**/v1/sessions/s1/enter', (route) => {
		entered.push(route.request().method());
		const fresh = [{ action_id: 'look_around', label: 'Look around' }];
		return route.fulfill({ json: { view: view(fresh), journal_page: null, choices: fresh } });
	});
	await page.goto('/play/idle-chapters');
	await page.getByRole('button', { name: /Continue/ }).click({ timeout: 10_000 });
	return entered;
}

test('Continue resumes the saved choices without re-entering', async ({ page }) => {
	const entered = await stubSavedSession(page, [{ action_id: 'make_tea', label: 'Make tea' }]);
	await expect(page.getByRole('button', { name: /Make tea/ })).toBeVisible({ timeout: 10_000 });
	expect(entered).toEqual([]);
});

test('Continue re-enters when the saved node has no choices', async ({ page }) => {
	const entered = await stubSavedSession(page, []);
	await expect(page.getByRole('button', { name: /Look around/ })).toBeVisible({ timeout: 10_000 });
	expect(entered).toEqual(['POST']);
});
