/**
 * Typed API client for the Idle Chapters backend.
 *
 * Covers /v1/sessions/* and /v1/world/* endpoints.
 * Base URL is read from the VITE_API_URL environment variable.
 */

// ---------------------------------------------------------------------------
// Types — derived from docs/openapi.json component schemas
// ---------------------------------------------------------------------------

export interface ViewAction {
	action_id: string;
	label: string;
}

export interface ViewModel {
	prompt: string | null;
	scene_id: string | null;
	eligible_actions: ViewAction[];
	visible_items: string[];
	visible_npcs: string[];
}

export interface StepResponse {
	view: ViewModel;
	journal_page: Record<string, unknown> | null;
	choices: ViewAction[];
}

export interface SessionCreateRequest {
	place_id?: string;
}

export interface SessionCreateResponse {
	session_id: string;
	view: ViewModel;
	journal_page: Record<string, unknown> | null;
}

export interface SessionGetResponse {
	session_id: string;
	view: ViewModel;
	state: Record<string, unknown> | null;
}

export interface ActionRequest {
	action_id: string;
}

export interface IntentRequest {
	input: string;
}

export interface WorldManifest {
	schemas: Record<string, unknown>;
	assets: Record<string, unknown>;
	lexicons: Record<string, unknown>;
}

/** RFC 9457 Problem Details — player projection (minimal). */
export interface ProblemDetailPlayer {
	type: string;
	title: string;
	status: number;
}

/** RFC 9457 Problem Details — developer projection (full + Z535 extensions). */
export interface ProblemDetailDeveloper {
	type: string;
	title: string;
	status: number;
	detail: string;
	instance: string;
	effect: 'none' | 'applied' | 'partial' | 'unknown';
	recovery: 'retryable' | 'correctable' | 'terminal' | 'escalate';
	signal: 'DANGER' | 'WARNING' | 'CAUTION' | 'NOTICE';
	context: Record<string, unknown>;
}

export type ProblemDetail = ProblemDetailPlayer | ProblemDetailDeveloper;

// ---------------------------------------------------------------------------
// Client
// ---------------------------------------------------------------------------

class ApiError extends Error {
	public problemDetail: ProblemDetailPlayer | null;

	constructor(
		public status: number,
		public body: unknown
	) {
		const parsed = body as ProblemDetail | null;
		const message = parsed?.title ?? `API error ${status}`;
		super(message);
		this.name = 'ApiError';
		this.problemDetail = parsed && 'type' in parsed
			? parsed as ProblemDetailPlayer
			: null;
	}
}

export { ApiError };

const BASE_URL = (import.meta.env.VITE_API_URL as string | undefined) ?? '';

async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
	const url = `${BASE_URL}${path}`;
	const init: RequestInit = {
		method,
		headers: { 'Content-Type': 'application/json' }
	};
	if (body !== undefined) {
		init.body = JSON.stringify(body);
	}
	const res = await fetch(url, init);
	if (!res.ok) {
		throw new ApiError(res.status, await res.json().catch(() => null));
	}
	return res.json() as Promise<T>;
}

// ---------------------------------------------------------------------------
// Sessions
// ---------------------------------------------------------------------------

export const sessions = {
	create(req?: SessionCreateRequest): Promise<SessionCreateResponse> {
		return request('POST', '/v1/sessions', req);
	},

	get(sessionId: string): Promise<SessionGetResponse> {
		return request('GET', `/v1/sessions/${encodeURIComponent(sessionId)}`);
	},

	enter(sessionId: string): Promise<StepResponse> {
		return request('POST', `/v1/sessions/${encodeURIComponent(sessionId)}/enter`);
	},

	action(sessionId: string, actionId: string): Promise<StepResponse> {
		return request('POST', `/v1/sessions/${encodeURIComponent(sessionId)}/action`, {
			action_id: actionId
		} satisfies ActionRequest);
	},

	intent(sessionId: string, input: string): Promise<StepResponse> {
		return request('POST', `/v1/sessions/${encodeURIComponent(sessionId)}/intent`, {
			input
		} satisfies IntentRequest);
	},

	journal(sessionId: string): Promise<Record<string, unknown>[]> {
		return request('GET', `/v1/sessions/${encodeURIComponent(sessionId)}/journal`);
	},

	journalPage(sessionId: string, pageId: string): Promise<Record<string, unknown>> {
		return request(
			'GET',
			`/v1/sessions/${encodeURIComponent(sessionId)}/journal/${encodeURIComponent(pageId)}`
		);
	}
};

// ---------------------------------------------------------------------------
// World
// ---------------------------------------------------------------------------

export const world = {
	manifest(): Promise<WorldManifest> {
		return request('GET', '/v1/world/manifest');
	},

	places(): Promise<Record<string, unknown>[]> {
		return request('GET', '/v1/world/places');
	},

	scenes(): Promise<Record<string, unknown>[]> {
		return request('GET', '/v1/world/scenes');
	},

	actions(): Promise<Record<string, unknown>[]> {
		return request('GET', '/v1/world/actions');
	},

	collectibles(): Promise<Record<string, unknown>[]> {
		return request('GET', '/v1/world/collectibles');
	},

	npcs(): Promise<Record<string, unknown>[]> {
		return request('GET', '/v1/world/npcs');
	}
};
