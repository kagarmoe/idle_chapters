<!--
  Typewriter.svelte — Reveals text character-by-character with a gentle pace.

  Props:
    text     — the full text to reveal
    speed    — milliseconds per character (default 30)
    onfinish — called when reveal completes
-->
<script lang="ts">
	interface Props {
		text: string;
		speed?: number;
		onfinish?: () => void;
	}

	let { text, speed = 30, onfinish }: Props = $props();

	let revealedLength = $state(0);
	let done = $state(false);

	function skipToEnd() {
		revealedLength = text.length;
		done = true;
		onfinish?.();
	}

	$effect(() => {
		// Reset when text changes
		revealedLength = 0;
		done = false;
	});

	$effect(() => {
		if (done) return;
		if (revealedLength >= text.length) {
			done = true;
			onfinish?.();
			return;
		}

		const timer = setTimeout(() => {
			revealedLength++;
		}, speed);
		return () => clearTimeout(timer);
	});
</script>

<!-- svelte-ignore a11y_click_events_have_key_events -->
<!-- svelte-ignore a11y_no_static_element_interactions -->
<div class="typewriter" onclick={skipToEnd}>
	<p class="typewriter-text" aria-live="polite">
		{text.slice(0, revealedLength)}<span class="cursor" class:hidden={done}>▌</span>
	</p>
	{#if !done}
		<p class="typewriter-hint">click to skip</p>
	{/if}
</div>

<style>
	.typewriter {
		cursor: default;
		user-select: none;
	}

	.typewriter-text {
		font-family: 'Courier New', 'Consolas', monospace;
		font-size: 0.95rem;
		line-height: 1.7;
		color: var(--color-ink);
		white-space: pre-wrap;
		min-height: 3rem;
	}

	.cursor {
		animation: blink 0.8s step-end infinite;
		color: var(--color-moss);
	}

	.cursor.hidden {
		display: none;
	}

	.typewriter-hint {
		font-family: 'Courier New', 'Consolas', monospace;
		font-size: 0.7rem;
		color: var(--color-ink-light);
		opacity: 0.5;
		margin-top: 0.5rem;
	}

	@keyframes blink {
		50% { opacity: 0; }
	}
</style>
