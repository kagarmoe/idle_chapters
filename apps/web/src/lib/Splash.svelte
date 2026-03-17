<!--
  Splash.svelte — ASCII art title screen for Idle Chapters.

  Displays an elaborate ASCII art title with cozy motifs woven into the
  letterforms (teacups, pillows, animals, gems, mirror). A typewriter
  effect reveals the art line-by-line, followed by a gentle menu.

  Props:
    hasSave — whether a Continue option should appear
  Events (via callbacks):
    onnewgame  — player chose New Game
    oncontinue — player chose Continue
-->
<script lang="ts">
	interface Props {
		hasSave?: boolean;
		onnewgame?: () => void;
		oncontinue?: () => void;
	}

	let { hasSave = false, onnewgame, oncontinue }: Props = $props();

	// ── ASCII art ──────────────────────────────────────────────
	// Each line is revealed one at a time by the typewriter.
	// Motifs: ☕ teacup, ◆ gem, 🪞 mirror frame, ~ pillow curves,
	// 🐾 animal tracks woven into the negative space.
	const ART_LINES = [
		'',
		'        ╭─────────────────────────────────────────────╮',
		'        │  ·  .  ·  .  ·  .  ·  .  ·  .  ·  .  ·  . │',
		'        ╰─────────────────────────────────────────────╯',
		'',
		'         ██╗██████╗ ██╗     ███████╗',
		'         ██║██╔══██╗██║     ██╔════╝',
		'         ██║██║  ██║██║     █████╗    ☕',
		'         ██║██║  ██║██║     ██╔══╝',
		'         ██║██████╔╝███████╗███████╗',
		'         ╚═╝╚═════╝ ╚══════╝╚══════╝',
		'',
		'   ██████╗██╗  ██╗ █████╗ ██████╗████████╗███████╗██████╗ ███████╗',
		'  ██╔════╝██║  ██║██╔══██╗██╔══██╗╚══██╔══╝██╔════╝██╔══██╗██╔════╝',
		'  ██║     ███████║███████║██████╔╝   ██║   █████╗  ██████╔╝███████╗',
		'  ██║     ██╔══██║██╔══██║██╔═══╝    ██║   ██╔══╝  ██╔══██╗╚════██║',
		'  ╚██████╗██║  ██║██║  ██║██║        ██║   ███████╗██║  ██║███████║',
		'   ╚═════╝╚═╝  ╚═╝╚═╝  ╚═╝╚═╝        ╚═╝   ╚══════╝╚═╝  ╚═╝╚══════╝',
		'',
		'        ~  ~ ·  ◆  · ~  ~    ◆   ~  ~ ·  ◆  · ~  ~',
		'',
		'           ☕  teacups cooling on the windowsill',
		'           ◆   small gems found between cushions',
		'           🐾  a cat asleep on an open book',
		'           ~   pillows arranged just so',
		'',
		'        ╭─────────────────────────────────────────────╮',
		'        │  ·  .  ·  .  ·  .  ·  .  ·  .  ·  .  ·  . │',
		'        ╰─────────────────────────────────────────────╯',
	];

	// ── Typewriter state ───────────────────────────────────────
	let revealedCount = $state(0);
	let typewriterDone = $state(false);
	let menuVisible = $state(false);
	let skipRequested = $state(false);

	const LINE_DELAY_MS = 65;
	const MENU_DELAY_MS = 400;

	function revealAll() {
		skipRequested = true;
		revealedCount = ART_LINES.length;
		typewriterDone = true;
		menuVisible = true;
	}

	$effect(() => {
		if (skipRequested) return;

		if (revealedCount < ART_LINES.length) {
			const timer = setTimeout(() => {
				revealedCount++;
			}, LINE_DELAY_MS);
			return () => clearTimeout(timer);
		}

		// Art fully revealed — show menu after a gentle pause
		if (!typewriterDone) {
			typewriterDone = true;
			const timer = setTimeout(() => {
				menuVisible = true;
			}, MENU_DELAY_MS);
			return () => clearTimeout(timer);
		}
	});

	function handleKeydown(e: KeyboardEvent) {
		// Any key during typewriter → skip to full reveal
		if (!typewriterDone) {
			revealAll();
			return;
		}
		// After menu is visible, Enter triggers default action
		if (menuVisible && e.key === 'Enter') {
			if (hasSave && oncontinue) {
				oncontinue();
			} else if (onnewgame) {
				onnewgame();
			}
		}
	}
</script>

<svelte:window onkeydown={handleKeydown} />

<!-- svelte-ignore a11y_click_events_have_key_events -->
<!-- svelte-ignore a11y_no_static_element_interactions -->
<div
	class="splash-container"
	onclick={() => { if (!typewriterDone) revealAll(); }}
>
	<pre class="splash-art" aria-label="Idle Chapters — ASCII art title">{#each ART_LINES as line, i}{#if i < revealedCount}{line}
{/if}{/each}</pre>

	{#if menuVisible}
		<nav class="splash-menu" aria-label="Main menu">
			{#if hasSave}
				<button class="splash-btn" onclick={oncontinue}>
					▸ Continue
				</button>
			{/if}
			<button class="splash-btn" onclick={onnewgame}>
				▸ New Game
			</button>
			<p class="splash-hint">
				{#if hasSave}
					press enter to continue
				{:else}
					press enter to begin
				{/if}
			</p>
		</nav>
	{/if}
</div>

<style>
	.splash-container {
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		min-height: 70vh;
		cursor: default;
		user-select: none;
	}

	.splash-art {
		font-family: 'Courier New', 'Consolas', monospace;
		font-size: 0.72rem;
		line-height: 1.25;
		color: var(--color-ink);
		text-align: left;
		white-space: pre;
		overflow-x: auto;
		max-width: 100%;
	}

	.splash-menu {
		margin-top: 2rem;
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 0.75rem;
		animation: fade-in 0.6s ease-out;
	}

	.splash-btn {
		background: none;
		border: none;
		font-family: 'Courier New', 'Consolas', monospace;
		font-size: 1rem;
		color: var(--color-ink);
		cursor: pointer;
		padding: 0.4rem 1.2rem;
		border-radius: 4px;
		transition: color 0.2s, background-color 0.2s;
		letter-spacing: 0.05em;
	}

	.splash-btn:hover,
	.splash-btn:focus-visible {
		color: var(--color-moss);
		background-color: var(--color-cloud);
		outline: none;
	}

	.splash-hint {
		font-family: 'Courier New', 'Consolas', monospace;
		font-size: 0.75rem;
		color: var(--color-ink-light);
		margin-top: 0.5rem;
		opacity: 0.7;
	}

	@keyframes fade-in {
		from { opacity: 0; transform: translateY(6px); }
		to   { opacity: 1; transform: translateY(0); }
	}
</style>
