<script lang="ts">
	import Splash from '#lib/Splash.svelte';
	import Typewriter from '#lib/Typewriter.svelte';
	import ChoiceBar from '#lib/ChoiceBar.svelte';
	import JournalCard from '#lib/JournalCard.svelte';
	import InventoryPanel from '#lib/InventoryPanel.svelte';
	import { sessions, type ViewModel, type ViewAction, ApiError } from '#lib/api.js';
	import { reportError } from '#lib/report.js';

	// ── Game states ────────────────────────────────────────────
	type GameScreen = 'splash' | 'loading' | 'playing' | 'error';

	let screen = $state<GameScreen>('splash');
	let sessionId = $state<string | null>(null);
	let view = $state<ViewModel | null>(null);
	let choices = $state<ViewAction[]>([]);
	let pages = $state<Record<string, unknown>[]>([]);
	let freeText = $state('');
	let note = $state('');
	let errorMsg = $state('');
	let typewriterDone = $state(false);

	// ── Save detection ─────────────────────────────────────────
	const SAVE_KEY = 'idle-chapters-session-id';
	let hasSave = $state(false);

	$effect(() => {
		const saved = localStorage.getItem(SAVE_KEY);
		hasSave = saved !== null;
	});

	// ── Session management ─────────────────────────────────────
	async function handleNewGame() {
		screen = 'loading';
		try {
			const res = await sessions.create();
			sessionId = res.session_id;
			localStorage.setItem(SAVE_KEY, res.session_id);
			show(res.view, res.view.eligible_actions);
			screen = 'playing';
		} catch (err) {
			handleError(err);
		}
	}

	async function handleContinue() {
		const savedId = localStorage.getItem(SAVE_KEY);
		if (!savedId) return handleNewGame();

		screen = 'loading';
		try {
			const res = await sessions.get(savedId);
			sessionId = res.session_id;
			if (res.view.eligible_actions.length > 0) {
				show(res.view, res.view.eligible_actions);
			} else {
				// Nothing to resume (a dead-end node, or a scene the server can no longer rebuild): re-enter for fresh choices.
				const step = await sessions.enter(savedId);
				show(step.view, step.choices.length > 0 ? step.choices : step.view.eligible_actions);
			}
			screen = 'playing';
		} catch (err) {
			if (err instanceof ApiError && err.status === 404) {
				localStorage.removeItem(SAVE_KEY);
				hasSave = false;
				screen = 'splash';
				return;
			}
			handleError(err);
		}
	}

	// ── Game loop ──────────────────────────────────────────────
	async function handleChoice(actionId: string) {
		if (!sessionId) return;
		try {
			const res = await sessions.action(sessionId, actionId);
			show(res.view, res.choices.length > 0 ? res.choices : res.view.eligible_actions);
		} catch (err) {
			handleError(err);
		}
	}

	function show(next: ViewModel, nextChoices: ViewAction[]) {
		view = next;
		choices = nextChoices;
		note = '';
		typewriterDone = false;
		refreshJournal();
	}

	function refreshJournal() {
		if (!sessionId) return;
		// The journal is a keepsake, not the game: if it can't load, play goes on.
		sessions.journal(sessionId).then((p) => (pages = p)).catch(() => {});
	}

	function handleTypewriterFinish() {
		typewriterDone = true;
	}

	// ── Free text ──────────────────────────────────────────────
	// Questions about the world are answered here and change nothing (CLI_INTENT_PARSING.md).
	function answerAloud(text: string): string | null {
		const t = text.toLowerCase().replace(/[^\w\s']/g, ' ').replace(/\s+/g, ' ').trim();
		if (/^(help|how do i play)$/.test(t)) {
			return 'Type what you would like to do, like “make tea” or “look around.” You can also ask “What can I do?” or “What is here?”';
		}
		if (/^(what (can|could) i do( here| now)?|what now)$/.test(t)) {
			return choices.length > 0
				? `You could: ${choices.map((c) => c.label).join(', ')}.`
				: 'Nothing needs doing just now.';
		}
		if (/^(what is here|what's here|who is here|who's here|who is around)$/.test(t)) {
			const here = [...(view?.visible_npcs ?? []), ...(view?.visible_items ?? [])];
			return here.length > 0 ? `Here with you: ${here.join(', ')}.` : "It's quiet here, just you.";
		}
		return null;
	}

	async function handleFreeText(e: SubmitEvent) {
		e.preventDefault();
		const text = freeText.trim();
		if (!text || !sessionId) return;
		freeText = '';
		const answer = answerAloud(text);
		if (answer) {
			note = answer;
			return;
		}
		try {
			const res = await sessions.intent(sessionId, text);
			show(res.view, res.choices.length > 0 ? res.choices : res.view.eligible_actions);
		} catch (err) {
			if (err instanceof ApiError && err.status === 422) {
				note = err.problemDetail?.title ?? "I didn't quite catch that. What would you like to do?";
				return;
			}
			handleError(err);
		}
	}

	// ── Error handling ─────────────────────────────────────────
	function handleError(err: unknown) {
		// The player sees a gentle line; the logs still hear about it.
		if (err instanceof ApiError) reportError('warning', 'ApiError', `${err.status} ${err.message}`);
		else reportError('error', 'unexpected', err);
		if (err instanceof ApiError) {
			errorMsg = err.problemDetail?.title ?? `Something went quiet (${err.status}). The world rests.`;
		} else {
			errorMsg = 'The path fades for a moment. Try again.';
		}
		screen = 'error';
	}

	function returnToSplash() {
		screen = 'splash';
		errorMsg = '';
	}
</script>

<svelte:head>
	<title>Idle Chapters — Play</title>
</svelte:head>

{#if screen === 'splash'}
	<Splash
		{hasSave}
		onnewgame={handleNewGame}
		oncontinue={handleContinue}
	/>

{:else if screen === 'loading'}
	<div class="game-loading">
		<p class="loading-text">· · ·</p>
	</div>

{:else if screen === 'playing' && view}
	<div class="game-container">
		{#if view.prompt}
			{#key view.prompt}
				<Typewriter text={view.prompt} onfinish={handleTypewriterFinish} />
			{/key}
		{:else}
			<p class="game-quiet">A quiet moment. Nothing stirs.</p>
		{/if}

		<ChoiceBar
			{choices}
			disabled={!typewriterDone}
			onchoose={handleChoice}
		/>

		<form class="free-text" onsubmit={handleFreeText}>
			<input
				class="free-text-input"
				type="text"
				bind:value={freeText}
				aria-label="What would you like to do?"
				placeholder="What would you like to do?"
				autocomplete="off"
			/>
		</form>
		<p class="game-note" role="status" aria-live="polite">{note}</p>

		<JournalCard {pages} />

		<InventoryPanel
			items={view.visible_items}
			npcs={view.visible_npcs}
			carrying={view.inventory}
		/>
	</div>

{:else if screen === 'error'}
	<div class="game-error">
		<p class="error-text">{errorMsg}</p>
		<button class="error-btn" onclick={returnToSplash}>
			▸ Return to title
		</button>
	</div>
{/if}

<style>
	.game-container {
		max-width: 640px;
		margin: 0 auto;
	}

	.free-text {
		margin-top: 1rem;
	}

	.free-text-input {
		width: 100%;
		font-family: 'Georgia', 'Times New Roman', serif;
		font-size: 0.95rem;
		color: var(--color-ink);
		background: none;
		border: none;
		border-bottom: 1px solid var(--color-cloud);
		padding: 0.4rem 0.1rem;
	}

	.free-text-input:focus-visible {
		outline: none;
		border-bottom-color: var(--color-moss);
	}

	.game-note {
		font-family: 'Georgia', 'Times New Roman', serif;
		font-style: italic;
		font-size: 0.9rem;
		color: var(--color-ink-light);
		min-height: 1.5rem;
		margin-top: 0.5rem;
	}

	.game-quiet {
		font-family: 'Georgia', 'Times New Roman', serif;
		font-style: italic;
		color: var(--color-ink-light);
		min-height: 3rem;
	}

	.game-loading {
		display: flex;
		align-items: center;
		justify-content: center;
		min-height: 40vh;
	}

	.loading-text {
		font-family: 'Courier New', 'Consolas', monospace;
		font-size: 1.5rem;
		color: var(--color-ink-light);
		animation: pulse 1.5s ease-in-out infinite;
	}

	.game-error {
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		min-height: 40vh;
		gap: 1.5rem;
	}

	.error-text {
		font-family: 'Georgia', 'Times New Roman', serif;
		font-style: italic;
		color: var(--color-ink-light);
		text-align: center;
	}

	.error-btn {
		background: none;
		border: 1px solid var(--color-cloud);
		font-family: 'Courier New', 'Consolas', monospace;
		font-size: 0.85rem;
		color: var(--color-ink);
		cursor: pointer;
		padding: 0.5rem 1.2rem;
		border-radius: 4px;
		transition: color 0.2s, background-color 0.2s;
	}

	.error-btn:hover,
	.error-btn:focus-visible {
		color: var(--color-moss);
		background-color: var(--color-cloud);
		outline: none;
	}

	@keyframes pulse {
		0%, 100% { opacity: 0.4; }
		50% { opacity: 1; }
	}
</style>
