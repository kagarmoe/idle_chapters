/**
 * Reads a Discord channel's recent messages through a bot token. The swamp
 * registry's Discord extensions only post (webhooks are post-only), so this
 * is the read side. The bot needs only View Channel + Read Message History on
 * the channels it reads, plus the Message Content intent for message text.
 *
 * @module
 */
import { z } from "npm:zod@4";

const API = "https://discord.com/api/v10";

const GlobalArgsSchema = z.object({
  token: z.string().meta({ sensitive: true }),
  channelId: z.string().regex(/^\d+$/),
});

const MessageSchema = z.object({
  id: z.string(),
  author: z.string(),
  content: z.string(),
  timestamp: z.string(),
});

type Message = z.infer<typeof MessageSchema>;

type Context = {
  globalArgs: z.infer<typeof GlobalArgsSchema>;
  signal: AbortSignal;
  writeResource: (
    specName: string,
    name: string,
    data: Record<string, unknown>,
  ) => Promise<{ name: string }>;
};

/** Newest first, as Discord returns them. Throws on any non-2xx so an unreadable channel never looks empty. */
export async function fetchMessages(
  fetchImpl: typeof fetch,
  token: string,
  channelId: string,
  limit: number,
  signal?: AbortSignal,
): Promise<Message[]> {
  const url = `${API}/channels/${channelId}/messages?limit=${limit}`;
  const init = { headers: { Authorization: `Bot ${token}` }, signal };
  let res = await fetchImpl(url, init);
  if (res.status === 429) {
    // One retry after Discord's own back-off; a second 429 fails the run.
    const { retry_after = 1 } = await res.json();
    await new Promise((r) => setTimeout(r, retry_after * 1000));
    res = await fetchImpl(url, init);
  }
  const body = await res.json();
  if (!res.ok) {
    const hint = res.status === 403 ? " (bot lacks View Channel / Read Message History here)" : "";
    throw new Error(`discord: channel ${channelId} returned ${res.status}${hint}: ${JSON.stringify(body).slice(0, 300)}`);
  }
  return body.map((m: { id: string; author: { username: string }; content: string; timestamp: string }) => ({
    id: m.id,
    author: m.author.username,
    content: m.content,
    timestamp: m.timestamp,
  }));
}

/** Read-only access to one Discord channel. */
export const behavior = {
  type: "@kagarmoe/discord-channel",
  version: "2026.10.22.1",
  globalArguments: GlobalArgsSchema,
  resources: {
    "messages": {
      description: "A channel's most recent messages, newest first",
      schema: z.object({
        channelId: z.string(),
        messages: z.array(MessageSchema),
        readAt: z.iso.datetime(),
      }),
      lifetime: "infinite",
      garbageCollection: 20,
    },
  },
  methods: {
    read: {
      description: "Read the channel's most recent messages (newest first)",
      arguments: z.object({ limit: z.number().int().min(1).max(100).default(50) }),
      execute: async (args: { limit: number }, context: Context) => {
        const { token, channelId } = context.globalArgs;
        const messages = await fetchMessages(fetch, token, channelId, args.limit, context.signal);
        const handle = await context.writeResource("messages", channelId, {
          channelId,
          messages,
          readAt: new Date().toISOString(),
        });
        return { dataHandles: [handle] };
      },
    },
  },
};
