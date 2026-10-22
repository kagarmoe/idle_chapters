import { defineEnvVars } from '@sveltejs/kit/env';

// Unset outside Vercel; hooks.server logs a missing commit as null.
export const variables = defineEnvVars({ VERCEL_GIT_COMMIT_SHA: { schema: (input) => input ?? '' } });
