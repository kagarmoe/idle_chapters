import { assertEquals, assertRejects } from "jsr:@std/assert@1.0.13";
import { fetchMessages } from "./discord_channel.ts";

const reply = (status: number, body: unknown) => () =>
  Promise.resolve(new Response(JSON.stringify(body), { status }));

Deno.test("maps Discord messages to id, author, content, timestamp", async () => {
  const fetchImpl = reply(200, [
    { id: "2", author: { username: "kim" }, content: "hi", timestamp: "2026-10-22T00:00:00Z", pinned: false },
  ]) as typeof fetch;
  assertEquals(await fetchMessages(fetchImpl, "t", "123", 1), [
    { id: "2", author: "kim", content: "hi", timestamp: "2026-10-22T00:00:00Z" },
  ]);
});

Deno.test("a channel the bot can't read fails instead of returning nothing", async () => {
  const fetchImpl = reply(403, { message: "Missing Access", code: 50001 }) as typeof fetch;
  await assertRejects(() => fetchMessages(fetchImpl, "t", "123", 1), Error, "403");
});
