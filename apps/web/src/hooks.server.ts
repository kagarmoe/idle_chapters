import type { HandleServerError } from '@sveltejs/kit/hooks';
import { VERCEL_GIT_COMMIT_SHA } from '$app/env/private';

// The same JSON line the API writes (monitoring design §1); Vercel's runtime logs carry it to the drain.
// SvelteKit 3 also sends expected errors (404s, error()) here; only an unknown throw is a 500.
export const handleError: HandleServerError = ({ kind, error, event }) => {
	const status = kind === 'unknown' ? 500 : error.status;
	const thrown = kind === 'unknown' && error instanceof Error ? error : null;
	console.error(
		JSON.stringify({
			event: 'error',
			level: status >= 500 ? 'error' : 'warning',
			source: 'ssr',
			kind: thrown ? thrown.name : kind,
			status,
			method: event.request.method,
			path: event.route.id ?? 'unmatched',
			message: (kind === 'unknown' ? (thrown?.message ?? String(error)) : error.message).slice(0, 500),
			stack: (thrown?.stack ?? '').slice(-4000),
			commit: VERCEL_GIT_COMMIT_SHA || null
		})
	);
};
