import { sveltekit } from '@sveltejs/kit/vite';
import tailwindcss from '@tailwindcss/vite';
import { defineConfig } from 'vite';

export default defineConfig({
	plugins: [tailwindcss(), sveltekit()],
	// In production the API shares the page's origin (vercel.json services); in dev, forward to uvicorn.
	server: {
		proxy: {
			'/v1': 'http://localhost:8000',
			'/health': 'http://localhost:8000'
		}
	}
});
