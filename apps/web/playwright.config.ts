import { defineConfig } from '@playwright/test';

export default defineConfig({
	testDir: 'e2e',
	webServer: {
		command: 'npm run build && npm run preview -- --port 4173',
		port: 4173,
		// The API shares the page's origin; a stale VITE_API_URL must not send the client elsewhere.
		env: { VITE_API_URL: 'https://elsewhere.invalid' },
		reuseExistingServer: !process.env.CI
	},
	// PW_CHANNEL=chrome runs against an installed Chrome locally; CI uses Playwright's own build.
	use: { baseURL: 'http://localhost:4173', channel: process.env.PW_CHANNEL }
});
