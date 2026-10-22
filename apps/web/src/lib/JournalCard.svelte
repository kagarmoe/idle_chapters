<!--
  JournalCard.svelte — The journal so far, newest page first, folded away until opened.

  Props:
    pages — journal pages from the API, oldest first
-->
<script lang="ts">
	interface Props {
		pages: Record<string, unknown>[];
	}

	let { pages }: Props = $props();

	const newestFirst = $derived([...pages].reverse());
</script>

{#if pages.length > 0}
	<details class="journal-card">
		<summary class="journal-header">
			<span class="journal-icon" aria-hidden="true">📖</span>
			<span class="journal-label">Journal · {pages.length} {pages.length === 1 ? 'page' : 'pages'}</span>
		</summary>
		<ol class="journal-pages">
			{#each newestFirst as page (page.page_id)}
				<li class="journal-page">
					{#if page.prompt}
						<h3 class="journal-title">{page.prompt}</h3>
					{/if}
					{#each String(page.body ?? '').split('\n\n') as paragraph}
						<p class="journal-body">{paragraph}</p>
					{/each}
				</li>
			{/each}
		</ol>
	</details>
{/if}

<style>
	.journal-card {
		border: 1px solid var(--color-cloud);
		border-left: 3px solid var(--color-amber);
		border-radius: 4px;
		padding: 1rem 1.25rem;
		margin-top: 1.5rem;
		background-color: color-mix(in srgb, var(--color-parchment) 50%, white);
	}

	.journal-header {
		display: flex;
		align-items: center;
		gap: 0.4rem;
		cursor: pointer;
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

	.journal-pages {
		list-style: none;
		padding: 0;
		margin: 0.75rem 0 0;
		max-height: 24rem;
		overflow-y: auto;
	}

	.journal-page + .journal-page {
		margin-top: 1rem;
		padding-top: 1rem;
		border-top: 1px solid var(--color-cloud);
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

	.journal-body + .journal-body {
		margin-top: 0.4rem;
	}
</style>
