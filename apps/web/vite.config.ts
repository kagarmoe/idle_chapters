import adapter from '@sveltejs/adapter-auto';
import { sveltekit } from '@sveltejs/kit/vite';
import tailwindcss from '@tailwindcss/vite';
import { defineConfig } from 'vite';

export default defineConfig({
	plugins: [
		tailwindcss(),
		sveltekit({
			dynamicCompileOptions: ({ filename }) => (filename.includes('node_modules') ? undefined : { runes: true }),

			// adapter-auto only supports some environments, see https://svelte.dev/docs/kit/adapter-auto for a list.
			// If your environment is not supported, or you settled on a specific environment, switch out the adapter.
			// See https://svelte.dev/docs/kit/adapters for more information about adapters.
			adapter: adapter()
		})
	],
	// In production the API shares the page's origin (vercel.json services); in dev, forward to uvicorn.
	server: {
		proxy: {
			'/v1': 'http://localhost:8000',
			'/health': 'http://localhost:8000'
		}
	}
});
