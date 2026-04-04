<script lang="ts">
	import '../app.css';
	import favicon from '$lib/assets/favicon.svg';

	let { children } = $props();
</script>

<svelte:head>
	<link rel="icon" href={favicon} />
	<title>Idle Chapters</title>
</svelte:head>

<div class="min-h-screen flex flex-col">
	<nav class="border-b border-[var(--color-cloud)] px-6 py-4">
		<div class="max-w-4xl mx-auto flex items-center justify-between">
			<a href="/" class="text-xl tracking-wide text-[var(--color-ink)] hover:text-[var(--color-moss)] transition-colors">
				Idle Chapters
			</a>
			<ul class="flex gap-6 text-sm">
				<li><a href="/projects" class="text-[var(--color-ink-light)] hover:text-[var(--color-moss)] transition-colors">Projects</a></li>
				<li><a href="/writing" class="text-[var(--color-ink-light)] hover:text-[var(--color-moss)] transition-colors">Writing</a></li>
				<li><a href="/data" class="text-[var(--color-ink-light)] hover:text-[var(--color-moss)] transition-colors">Data</a></li>
				<li><a href="/thinking" class="text-[var(--color-ink-light)] hover:text-[var(--color-moss)] transition-colors">Thinking</a></li>
				<li><a href="/play" class="text-[var(--color-ink-light)] hover:text-[var(--color-moss)] transition-colors">Play</a></li>
			</ul>
		</div>
	</nav>

	<main class="flex-1 max-w-4xl mx-auto w-full px-6 py-10">
		{@render children()}
	</main>

	<footer class="border-t border-[var(--color-cloud)] px-6 py-6 text-center text-xs text-[var(--color-ink-light)]">
		<p>A quiet place for projects, writing, and small games.</p>
	</footer>
</div>
