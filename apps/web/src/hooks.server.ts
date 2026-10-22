import type { HandleServerError } from '@sveltejs/kit';
import { env } from '$env/dynamic/private';

// The same JSON line the API writes (monitoring design §1); Vercel's runtime logs carry it to the drain.
export const handleError: HandleServerError = ({ error, event, status }) => {
	console.error(
		JSON.stringify({
			event: 'error',
			level: status >= 500 ? 'error' : 'warning',
			source: 'ssr',
			kind: error instanceof Error ? error.name : 'unknown',
			status,
			method: event.request.method,
			path: event.route.id ?? 'unmatched',
			message: (error instanceof Error ? error.message : String(error)).slice(0, 500),
			stack: (error instanceof Error ? (error.stack ?? '') : '').slice(-4000),
			commit: env.VERCEL_GIT_COMMIT_SHA ?? null
		})
	);
};
