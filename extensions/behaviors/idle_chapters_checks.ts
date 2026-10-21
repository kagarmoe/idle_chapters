/**
 * Quality gates and shipping for Idle Chapters: asset/schema validation,
 * pytest, the web app's svelte-check + build + e2e, deploying the API at an
 * exact commit, and a live smoke test. Each method writes a record only when
 * it passes; a failure throws so workflows stop on it.
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
  apiUrl: z.string().default("https://idle-chapters-api.vercel.app"),
  webUrl: z.string().default("https://idle-chapters.vercel.app"),
  apiProjectId: z.string().default("prj_QlitUIikmNFcqZjBzIbTWpg6lSKi"),
  vercelOrgId: z.string().default("team_SMACO8iOr6wPIGx5as56P468"),
});

type GlobalArgs = z.infer<typeof GlobalArgsSchema>;

const GateSchema = z.object({
  gate: z.string(),
  commands: z.array(z.string()),
  durationMs: z.number(),
  outputTail: z.string(),
  checkedAt: z.iso.datetime(),
});

const DeploySchema = z.object({
  commit: z.string(),
  url: z.string(),
  deployedAt: z.iso.datetime(),
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
  version: "2026.10.21.2",
  globalArguments: GlobalArgsSchema,
  resources: {
    "gate": {
      description: "A quality gate that passed",
      schema: GateSchema,
      lifetime: "infinite",
      garbageCollection: 20,
    },
    "deploy": {
      description: "An API deployment of an exact commit",
      schema: DeploySchema,
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
    deployApi: {
      description:
        "Deploy the API to Vercel production from an exact commit (git archive, not the working tree)",
      arguments: z.object({ commit: z.string().regex(/^[0-9a-f]{40}$/) }),
      execute: async (args: { commit: string }, context: Context) => {
        const g = context.globalArgs;
        const dir = await Deno.makeTempDir({ prefix: "ic-api-deploy-" });
        try {
          const tar = `${dir}.tar`;
          await runSteps("deployApi", [
            { argv: ["git", "archive", "-o", tar, args.commit], cwd: context.repoDir },
            { argv: ["tar", "-xf", tar, "-C", dir], cwd: dir },
          ], context);
          await Deno.remove(tar);
          // Kept out of the repo: root-level Vercel config would also apply to the web project.
          await Deno.mkdir(`${dir}/.vercel`);
          await Deno.writeTextFile(
            `${dir}/.vercel/project.json`,
            JSON.stringify({ projectId: g.apiProjectId, orgId: g.vercelOrgId }),
          );
          await Deno.writeTextFile(`${dir}/vercel.json`, JSON.stringify({ framework: "fastapi" }));
          const output = await runSteps("deployApi", [{
            argv: ["vercel", "deploy", "--prod", "--yes", "--cwd", dir],
            cwd: dir,
          }], context);
          const url = output.match(/https:\/\/[a-z0-9-]+\.vercel\.app/)?.[0];
          if (!url) throw new Error(`deployApi: no deployment URL in output:\n${output.slice(-TAIL_CHARS)}`);
          const handle = await context.writeResource("deploy", "api", {
            commit: args.commit,
            url,
            deployedAt: new Date().toISOString(),
          });
          return { dataHandles: [handle] };
        } finally {
          await Deno.remove(dir, { recursive: true });
        }
      },
    },
    smoke: {
      description:
        "Live smoke test: API health, a new session offers choices with CORS for the web origin, and the play page loads",
      arguments: z.object({}),
      execute: async (_args: Record<string, never>, context: Context) => {
        const { apiUrl, webUrl } = context.globalArgs;
        const started = Date.now();
        await expectOk(`${apiUrl}/health`);
        const res = await fetch(`${apiUrl}/v1/sessions`, {
          method: "POST",
          headers: {
            "content-type": "application/json",
            "Accept-Projection": "player",
            Origin: webUrl,
          },
          body: JSON.stringify({ place_id: "cottage_home" }),
        });
        const session = await res.json();
        if (!res.ok || !session.view?.eligible_actions?.length) {
          throw new Error(`smoke: new session offered no choices (${res.status}): ${JSON.stringify(session).slice(0, 500)}`);
        }
        if (res.headers.get("access-control-allow-origin") !== webUrl) {
          throw new Error(`smoke: API does not allow CORS from ${webUrl}`);
        }
        await expectOk(`${webUrl}/play/idle-chapters`);
        const handle = await context.writeResource("gate", "smoke", {
          gate: "smoke",
          commands: [`GET ${apiUrl}/health`, `POST ${apiUrl}/v1/sessions`, `GET ${webUrl}/play/idle-chapters`],
          durationMs: Date.now() - started,
          outputTail: `choices: ${session.view.eligible_actions.map((a: { action_id: string }) => a.action_id).join(", ")}`,
          checkedAt: new Date().toISOString(),
        });
        return { dataHandles: [handle] };
      },
    },
  },
};
