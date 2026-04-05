<!--
  JournalCard.svelte — Displays the most recent journal page entry.

  Props:
    page — a journal page record from the API (or null if no entry yet)
-->
<script lang="ts">
	interface Props {
		page: Record<string, unknown> | null;
	}

	let { page }: Props = $props();

	// Extract display fields from the freeform journal page
	const title = $derived(page ? String(page.title ?? page.scene_id ?? 'Untitled') : '');
	const body = $derived(page ? String(page.body ?? page.text ?? page.description ?? '') : '');
</script>

{#if page}
	<aside class="journal-card" aria-label="Journal entry">
		<div class="journal-header">
			<span class="journal-icon">📖</span>
			<span class="journal-label">Journal</span>
		</div>
		{#if title}
			<h3 class="journal-title">{title}</h3>
		{/if}
		{#if body}
			<p class="journal-body">{body}</p>
		{/if}
	</aside>
{/if}

<style>
	.journal-card {
		border: 1px solid var(--color-cloud);
		border-left: 3px solid var(--color-amber);
		border-radius: 4px;
		padding: 1rem 1.25rem;
		margin-top: 1.5rem;
		background-color: color-mix(in srgb, var(--color-parchment) 50%, white);
		animation: fade-in 0.5s ease-out;
	}

	.journal-header {
		display: flex;
		align-items: center;
		gap: 0.4rem;
		margin-bottom: 0.5rem;
	}

	.journal-icon {
		font-size: 0.9rem;
	}

	.journal-label {
		font-family: 'Courier New', 'Consolas', monospace;
		font-size: 0.7rem;
		text-transform: uppercase;
		letter-spacing: 0.1em;
		color: var(--color-amber);
	}

	.journal-title {
		font-family: 'Georgia', 'Times New Roman', serif;
		font-size: 1rem;
		font-style: italic;
		color: var(--color-ink);
		margin-bottom: 0.4rem;
	}

	.journal-body {
		font-family: 'Georgia', 'Times New Roman', serif;
		font-size: 0.85rem;
		line-height: 1.6;
		color: var(--color-ink-light);
	}

	@keyframes fade-in {
		from { opacity: 0; transform: translateY(4px); }
		to   { opacity: 1; transform: translateY(0); }
	}
</style>
