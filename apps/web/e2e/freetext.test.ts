import { expect, test } from '@playwright/test';

const view = (prompt: string) => ({
	prompt,
	scene_id: 'cottage_wake_v1',
	eligible_actions: [{ action_id: 'make_tea', label: 'Make a cup of tea' }],
	visible_items: [],
	visible_npcs: ['Moss'],
	inventory: ['Travel kit']
});

test('free text answers questions on the page and does what you ask', async ({ page }) => {
	const said: string[] = [];
	await page.addInitScript(() => localStorage.setItem('idle-chapters-session-id', 's1'));
	await page.route('**/v1/sessions/s1', (route) =>
		route.fulfill({ json: { session_id: 's1', view: view('The kettle ticks.'), journal_page: null, state: null } })
	);
	await page.route('**/v1/sessions/s1/journal', (route) =>
		route.fulfill({ json: [{ page_id: 'p1', prompt: 'What softened today?', body: 'Morning.\n\nThe kettle ticks.' }] })
	);
	await page.route('**/v1/sessions/s1/intent', (route) => {
		const input = route.request().postDataJSON().input as string;
		said.push(input);
		if (input === 'fly to the moon') {
			return route.fulfill({
				status: 422,
				json: { type: 'urn:idle-chapters:error:intent_no_match', title: 'Hmm, I’m not sure what you mean.', status: 422 }
			});
		}
		return route.fulfill({ json: { view: view('Steam curls up.'), journal_page: null, choices: [] } });
	});

	await page.goto('/play/idle-chapters');
	await page.getByRole('button', { name: /Continue/ }).click({ timeout: 10_000 });
	const box = page.getByRole('textbox', { name: /What would you like to do/ });
	const note = page.getByRole('status');

	await box.fill('What is here?');
	await box.press('Enter');
	await expect(note).toContainText('Moss');
	await box.fill('what can I do');
	await box.press('Enter');
	await expect(note).toContainText('Make a cup of tea');
	await box.fill('help');
	await box.press('Enter');
	await expect(note).toContainText('What can I do?');
	expect(said).toEqual([]);

	await box.fill('fly to the moon');
	await box.press('Enter');
	await expect(note).toContainText('not sure what you mean');
	await box.fill('make tea please');
	await box.press('Enter');
	await expect(page.getByText('Steam curls up.')).toBeVisible();
	expect(said).toEqual(['fly to the moon', 'make tea please']);

	await expect(page.getByText('cottage_wake_v1')).toHaveCount(0);
	await expect(page.getByText('Travel kit')).toBeVisible();
	await page.getByText(/^Journal/).click();
	await expect(page.getByText('What softened today?')).toBeVisible();
});
