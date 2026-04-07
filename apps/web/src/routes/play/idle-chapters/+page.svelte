<script lang="ts">
	import Splash from '$lib/Splash.svelte';
	import Typewriter from '$lib/Typewriter.svelte';
	import ChoiceBar from '$lib/ChoiceBar.svelte';
	import JournalCard from '$lib/JournalCard.svelte';
	import InventoryPanel from '$lib/InventoryPanel.svelte';
	import { sessions, type ViewModel, type ViewAction, ApiError } from '$lib/api';

	// ── Game states ────────────────────────────────────────────
	type GameScreen = 'splash' | 'loading' | 'playing' | 'error';

	let screen = $state<GameScreen>('splash');
	let sessionId = $state<string | null>(null);
	let view = $state<ViewModel | null>(null);
	let choices = $state<ViewAction[]>([]);
	let journalPage = $state<Record<string, unknown> | null>(null);
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
			view = res.view;
			journalPage = res.journal_page;
			choices = res.view.eligible_actions;
			typewriterDone = false;
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
			view = res.view;
			journalPage = null;
			choices = res.view.eligible_actions;
			typewriterDone = false;
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
			view = res.view;
			journalPage = res.journal_page;
			choices = res.choices.length > 0 ? res.choices : res.view.eligible_actions;
			typewriterDone = false;
		} catch (err) {
			handleError(err);
		}
	}

	function handleTypewriterFinish() {
		typewriterDone = true;
	}

	// ── Error handling ─────────────────────────────────────────
	function handleError(err: unknown) {
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
		{#if view.scene_id}
			<p class="scene-label">{view.scene_id}</p>
		{/if}

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

		<JournalCard page={journalPage} />

		<InventoryPanel
			items={view.visible_items}
			npcs={view.visible_npcs}
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

	.scene-label {
		font-family: 'Courier New', 'Consolas', monospace;
		font-size: 0.7rem;
		text-transform: uppercase;
		letter-spacing: 0.12em;
		color: var(--color-moss);
		margin-bottom: 1rem;
		opacity: 0.7;
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
