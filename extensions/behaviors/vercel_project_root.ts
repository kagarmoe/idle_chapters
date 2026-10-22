/**
 * Adds `useRepoRoot` to @swamp/vercel/projects/projects. Vercel only accepts
 * null for "the repository root" as a project's Root Directory, and the
 * pulled type's `rootDirectory` argument is a string, so `update` cannot set it.
 *
 * @module
 */
import { z } from "npm:zod@4";

type Context = {
  globalArgs: { name: string; teamId?: string; token?: string };
  writeResource: (
    specName: string,
    name: string,
    data: Record<string, unknown>,
  ) => Promise<{ name: string }>;
};

export const extension = {
  type: "@swamp/vercel/projects/projects",
  resources: {
    "root": {
      description: "The project's Root Directory after useRepoRoot",
      schema: z.object({
        id: z.string(),
        name: z.string(),
        rootDirectory: z.string().nullable(),
        framework: z.string().nullable(),
      }),
      lifetime: "infinite",
      garbageCollection: 5,
    },
  },
  methods: [
    {
      useRepoRoot: {
        description: "Set the project's Root Directory to the repository root (null)",
        arguments: z.object({}),
        execute: async (_args: Record<string, never>, context: Context) => {
          const { name, teamId, token } = context.globalArgs;
          const qs = teamId ? `?teamId=${encodeURIComponent(teamId)}` : "";
          const res = await fetch(
            `https://api.vercel.com/v9/projects/${encodeURIComponent(name)}${qs}`,
            {
              method: "PATCH",
              headers: { Authorization: `Bearer ${token}`, "content-type": "application/json" },
              body: JSON.stringify({ rootDirectory: null }),
            },
          );
          const body = await res.json();
          if (!res.ok) {
            throw new Error(`useRepoRoot: PATCH returned ${res.status}: ${JSON.stringify(body).slice(0, 500)}`);
          }
          if (body.rootDirectory !== null) {
            throw new Error(`useRepoRoot: Vercel kept rootDirectory=${JSON.stringify(body.rootDirectory)}`);
          }
          const handle = await context.writeResource("root", "root", {
            id: body.id,
            name: body.name,
            rootDirectory: body.rootDirectory,
            framework: body.framework ?? null,
          });
          return { dataHandles: [handle] };
        },
      },
    },
  ],
};
