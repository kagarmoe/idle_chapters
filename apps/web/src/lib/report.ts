/**
 * Tell the API about a browser error, handled or not, so it reaches the logs (monitoring design §1).
 * At most 10 a page load, each distinct one once; nothing the player typed is sent.
 */
const sent = new Set<string>();

export function reportError(level: 'warning' | 'error', kind: string, err: unknown): void {
	const message = (err instanceof Error ? err.message : String(err)).slice(0, 500);
	const key = `${kind}\n${message}`;
	if (sent.has(key) || sent.size >= 10 || typeof navigator === 'undefined' || !navigator.sendBeacon) return;
	sent.add(key);
	const report = {
		level,
		kind: kind.slice(0, 100),
		message,
		path: location.pathname.slice(0, 200),
		stack: (err instanceof Error ? (err.stack ?? '') : '').slice(0, 4000)
	};
	navigator.sendBeacon('/v1/client-errors', new Blob([JSON.stringify(report)], { type: 'application/json' }));
}
