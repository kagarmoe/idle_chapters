import type { HandleClientError } from '@sveltejs/kit/hooks';
import { reportError } from '#lib/report.js';

// SvelteKit 3 also sends expected errors (404s, error()) here; only an unknown throw is a real error.
export const handleError: HandleClientError = ({ kind, error }) => {
	if (kind === 'unknown') reportError('error', 'unexpected', error);
	else reportError(error.status >= 500 ? 'error' : 'warning', `${kind}_${error.status}`, new Error(error.message));
};

// Errors outside SvelteKit's reach: scripts, timers, promises nobody awaited.
window.addEventListener('error', (e) => reportError('error', 'window.error', e.error ?? e.message));
window.addEventListener('unhandledrejection', (e) => reportError('error', 'unhandledrejection', e.reason));
