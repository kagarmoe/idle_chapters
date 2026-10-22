import type { HandleClientError } from '@sveltejs/kit';
import { reportError } from '$lib/report';

export const handleError: HandleClientError = ({ error }) => {
	reportError('error', 'unexpected', error);
};

// Errors outside SvelteKit's reach: scripts, timers, promises nobody awaited.
window.addEventListener('error', (e) => reportError('error', 'window.error', e.error ?? e.message));
window.addEventListener('unhandledrejection', (e) => reportError('error', 'unhandledrejection', e.reason));
