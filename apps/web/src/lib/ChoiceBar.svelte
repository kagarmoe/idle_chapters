<!--
  ChoiceBar.svelte — Presents available actions as a horizontal/vertical bar.

  Props:
    choices   — array of { action_id, label } objects
    disabled  — whether choices are clickable (e.g. during typewriter)
    onchoose  — called with the chosen action_id
-->
<script lang="ts">
	import type { ViewAction } from '$lib/api';

	interface Props {
		choices: ViewAction[];
		disabled?: boolean;
		onchoose?: (actionId: string) => void;
	}

	let { choices, disabled = false, onchoose }: Props = $props();

	function select(actionId: string) {
		if (!disabled) {
			onchoose?.(actionId);
		}
	}

	function handleKeydown(e: KeyboardEvent, actionId: string) {
		if (e.key === 'Enter' || e.key === ' ') {
			e.preventDefault();
			select(actionId);
		}
	}
</script>

{#if choices.length > 0}
	<nav class="choice-bar" aria-label="Available actions">
		{#each choices as choice (choice.action_id)}
			<button
				class="choice-btn"
				class:choice-disabled={disabled}
				disabled={disabled}
				onclick={() => select(choice.action_id)}
				onkeydown={(e) => handleKeydown(e, choice.action_id)}
			>
				▸ {choice.label}
			</button>
		{/each}
	</nav>
{/if}

<style>
	.choice-bar {
		display: flex;
		flex-wrap: wrap;
		gap: 0.5rem;
		margin-top: 1.5rem;
		animation: fade-in 0.4s ease-out;
	}

	.choice-btn {
		background: none;
		border: 1px solid var(--color-cloud);
		font-family: 'Courier New', 'Consolas', monospace;
		font-size: 0.85rem;
		color: var(--color-ink);
		cursor: pointer;
		padding: 0.5rem 1rem;
		border-radius: 4px;
		transition: color 0.2s, background-color 0.2s, border-color 0.2s;
		letter-spacing: 0.03em;
	}

	.choice-btn:hover:not(:disabled),
	.choice-btn:focus-visible:not(:disabled) {
		color: var(--color-moss);
		background-color: var(--color-cloud);
		border-color: var(--color-moss-light);
		outline: none;
	}

	.choice-disabled {
		opacity: 0.4;
		cursor: default;
	}

	@keyframes fade-in {
		from { opacity: 0; transform: translateY(4px); }
		to   { opacity: 1; transform: translateY(0); }
	}
</style>
