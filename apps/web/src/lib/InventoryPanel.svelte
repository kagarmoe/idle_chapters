<!--
  InventoryPanel.svelte — Shows the player's visible items and NPCs.

  Props:
    items — array of item name strings
    npcs  — array of NPC name strings
-->
<script lang="ts">
	interface Props {
		items?: string[];
		npcs?: string[];
	}

	let { items = [], npcs = [] }: Props = $props();

	const hasContent = $derived(items.length > 0 || npcs.length > 0);
</script>

{#if hasContent}
	<aside class="inventory-panel" aria-label="Inventory and surroundings">
		{#if items.length > 0}
			<div class="inventory-section">
				<h4 class="inventory-heading">◆ Items</h4>
				<ul class="inventory-list">
					{#each items as item}
						<li class="inventory-item">{item}</li>
					{/each}
				</ul>
			</div>
		{/if}

		{#if npcs.length > 0}
			<div class="inventory-section">
				<h4 class="inventory-heading">🐾 Nearby</h4>
				<ul class="inventory-list">
					{#each npcs as npc}
						<li class="inventory-item">{npc}</li>
					{/each}
				</ul>
			</div>
		{/if}
	</aside>
{/if}

<style>
	.inventory-panel {
		border: 1px solid var(--color-cloud);
		border-radius: 4px;
		padding: 1rem 1.25rem;
		margin-top: 1rem;
		font-family: 'Courier New', 'Consolas', monospace;
	}

	.inventory-section + .inventory-section {
		margin-top: 0.75rem;
		padding-top: 0.75rem;
		border-top: 1px solid var(--color-cloud);
	}

	.inventory-heading {
		font-size: 0.7rem;
		text-transform: uppercase;
		letter-spacing: 0.1em;
		color: var(--color-moss);
		margin-bottom: 0.4rem;
	}

	.inventory-list {
		list-style: none;
		padding: 0;
		margin: 0;
		display: flex;
		flex-wrap: wrap;
		gap: 0.3rem 0.8rem;
	}

	.inventory-item {
		font-size: 0.8rem;
		color: var(--color-ink-light);
	}
</style>
