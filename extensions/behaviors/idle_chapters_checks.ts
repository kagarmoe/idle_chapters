/**
 * Quality gates and shipping for Idle Chapters: asset/schema validation,
 * pytest, the web app's svelte-check + build + e2e, and a live smoke test of
 * the one Vercel project that serves both web and API. Each method writes a
 * record only when it passes; a failure throws so workflows stop on it.
 *
 * @module
 */
import { z } from "npm:zod@4";

const GlobalArgsSchema = z.object({
  // requirements.txt is the full dev lock; pyproject lists only runtime deps.
  python: z.array(z.string()).default([
    "uv",
    "run",
    "--with-requirements",
    "requirements.txt",
    "python",
  ]),
  webDir: z.string().default("apps/web"),
  // Local runs use an installed Chrome; CI installs Playwright's own build.
  playwrightChannel: z.string().default("chrome"),
  // Web app and API share this origin (vercel.json services).
  webUrl: z.string().default("https://idle-chapters.vercel.app"),
  deployWaitMs: z.number().default(600_000),
  deployPollMs: z.number().default(15_000),
});

type GlobalArgs = z.infer<typeof GlobalArgsSchema>;

const GateSchema = z.object({
  gate: z.string(),
  commands: z.array(z.string()),
  durationMs: z.number(),
  outputTail: z.string(),
  checkedAt: z.iso.datetime(),
});

type Context = {
  globalArgs: GlobalArgs;
  repoDir: string;
  signal: AbortSignal;
  writeResource: (
    specName: string,
    name: string,
    data: Record<string, unknown>,
  ) => Promise<{ name: string }>;
};

type Step = { argv: string[]; cwd: string; env?: Record<string, string> };

// Reuses the app's own loader: it validates each manifest asset against its
// schema, then checks cross-file id references.
const VALIDATE_ASSETS = [
  "from idle_chapters.content.repo import ContentRepo",
  "from idle_chapters.content.validators import validate_cross_file_integrity",
  "validate_cross_file_integrity(ContentRepo())",
  "print('assets valid')",
].join("; ");

const TAIL_CHARS = 4000;
const decoder = new TextDecoder();

async function runSteps(gate: string, steps: Step[], context: Context) {
  let output = "";
  for (const { argv, cwd, env } of steps) {
    const [cmd, ...args] = argv;
    const result = await new Deno.Command(cmd, {
      args,
      cwd,
      env,
      signal: context.signal,
      stdout: "piped",
      stderr: "piped",
    }).output();
    output += decoder.decode(result.stdout) + decoder.decode(result.stderr);
    if (!result.success) {
      throw new Error(
        `${gate} failed (exit ${result.code}) running \`${argv.join(" ")}\`:\n` +
          output.slice(-TAIL_CHARS),
      );
    }
  }
  return output;
}

async function runGate(gate: string, steps: Step[], context: Context) {
  const started = Date.now();
  const output = await runSteps(gate, steps, context);
  const handle = await context.writeResource("gate", gate, {
    gate,
    commands: steps.map((s) => s.argv.join(" ")),
    durationMs: Date.now() - started,
    outputTail: output.slice(-TAIL_CHARS),
    checkedAt: new Date().toISOString(),
  });
  return { dataHandles: [handle] };
}

async function expectOk(url: string, init?: RequestInit) {
  const res = await fetch(url, init);
  const body = await res.text();
  if (!res.ok) throw new Error(`smoke: ${url} returned ${res.status}: ${body.slice(0, 500)}`);
  return body;
}

/** Quality gates and shipping for the Idle Chapters repo. */
export const behavior = {
  type: "@kagarmoe/idle-chapters-checks",
  version: "2026.10.22.1",
  globalArguments: GlobalArgsSchema,
  resources: {
    "gate": {
      description: "A quality gate that passed",
      schema: GateSchema,
      lifetime: "infinite",
      garbageCollection: 20,
    },
  },
  upgrades: [
    {
      toVersion: "2026.10.21.2",
      description: "Adds e2eWeb, smoke and deployApi; new globals have defaults",
      upgradeAttributes: (old: Record<string, unknown>) => old,
    },
    {
      toVersion: "2026.10.21.3",
      description: "test runs the Mongo-gated tests on the in-memory backend, as CI does on mongo:7",
      upgradeAttributes: (old: Record<string, unknown>) => old,
    },
    {
      toVersion: "2026.10.22.1",
      description: "One Vercel project serves web and API: deployApi and the API-project globals go; smoke waits for the commit",
      upgradeAttributes: (old: Record<string, unknown>) => old,
    },
  ],
  methods: {
    validateAssets: {
      description:
        "Validate assets/ JSON against schemas/ and check cross-file references",
      arguments: z.object({}),
      execute: (_args: Record<string, never>, context: Context) =>
        runGate("validateAssets", [{
          argv: [...context.globalArgs.python, "-c", VALIDATE_ASSETS],
          cwd: context.repoDir,
        }], context),
    },
    test: {
      description: "Run the Python test suite (pytest)",
      arguments: z.object({}),
      execute: (_args: Record<string, never>, context: Context) =>
        runGate("test", [{
          argv: [...context.globalArgs.python, "-m", "pytest", "-q"],
          cwd: context.repoDir,
          // CI runs the Mongo-gated tests against mongo:7; mongomock runs them here (close, not identical).
          env: { MONGO_URL: "memory://" },
        }], context),
    },
    buildWeb: {
      description: "Type-check and build the SvelteKit web app",
      arguments: z.object({}),
      execute: (_args: Record<string, never>, context: Context) => {
        const cwd = `${context.repoDir}/${context.globalArgs.webDir}`;
        return runGate("buildWeb", [
          { argv: ["npm", "run", "check"], cwd },
          { argv: ["npm", "run", "build"], cwd },
        ], context);
      },
    },
    e2eWeb: {
      description: "Run the web app's Playwright end-to-end tests",
      arguments: z.object({}),
      execute: (_args: Record<string, never>, context: Context) =>
        runGate("e2eWeb", [{
          argv: ["npx", "playwright", "test"],
          cwd: `${context.repoDir}/${context.globalArgs.webDir}`,
          env: { CI: "1", PW_CHANNEL: context.globalArgs.playwrightChannel },
        }], context),
    },
    smoke: {
      description:
        "Live smoke test of production once Vercel has deployed the commit: health reports it, a new session offers choices and reads back, and the play page loads",
      arguments: z.object({ commit: z.string().regex(/^[0-9a-f]{40}$/) }),
      execute: async (args: { commit: string }, context: Context) => {
        const { webUrl, deployWaitMs, deployPollMs } = context.globalArgs;
        const started = Date.now();
        // Vercel's Git integration deploys main; until this commit is live, /health is old, missing or not JSON.
        let seen: unknown = "no response";
        while ((seen as { commit?: string })?.commit !== args.commit) {
          if (Date.now() - started > deployWaitMs) {
            throw new Error(`smoke: ${webUrl}/health never reported ${args.commit}; last saw ${JSON.stringify(seen).slice(0, 200)}`);
          }
          try {
            const res = await fetch(`${webUrl}/health`, { signal: context.signal });
            seen = res.ok ? await res.json() : `HTTP ${res.status}`;
          } catch (e) {
            seen = String(e);
          }
          if ((seen as { commit?: string })?.commit !== args.commit) {
            await new Promise((r) => setTimeout(r, deployPollMs));
          }
        }
        const res = await fetch(`${webUrl}/v1/sessions`, {
          method: "POST",
          headers: { "content-type": "application/json", "Accept-Projection": "player" },
          body: JSON.stringify({ place_id: "cottage_home" }),
        });
        const session = await res.json();
        if (!res.ok || !session.view?.eligible_actions?.length) {
          throw new Error(`smoke: new session offered no choices (${res.status}): ${JSON.stringify(session).slice(0, 500)}`);
        }
        // Read it back: sessions must persist between requests (MONGO_URL reaches the database).
        await expectOk(`${webUrl}/v1/sessions/${session.session_id}`);
        await expectOk(`${webUrl}/play/idle-chapters`);
        const handle = await context.writeResource("gate", "smoke", {
          gate: "smoke",
          commands: [
            `GET ${webUrl}/health (until commit ${args.commit})`,
            `POST ${webUrl}/v1/sessions`,
            `GET ${webUrl}/v1/sessions/${session.session_id}`,
            `GET ${webUrl}/play/idle-chapters`,
          ],
          durationMs: Date.now() - started,
          outputTail: `choices: ${session.view.eligible_actions.map((a: { action_id: string }) => a.action_id).join(", ")}`,
          checkedAt: new Date().toISOString(),
        });
        return { dataHandles: [handle] };
      },
    },
  },
};
