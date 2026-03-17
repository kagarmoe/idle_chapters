<script lang="ts">
	import Splash from '$lib/Splash.svelte';

	// TODO: detect existing save via localStorage or API
	let hasSave = $state(false);

	function handleNewGame() {
		// Will be wired to sessions.create() in Task 7
		console.log('New Game requested');
	}

	function handleContinue() {
		// Will be wired to sessions.get() in Task 7
		console.log('Continue requested');
	}
</script>

<svelte:head>
	<title>Idle Chapters — Play</title>
</svelte:head>

<Splash
	{hasSave}
	onnewgame={handleNewGame}
	oncontinue={handleContinue}
/>
