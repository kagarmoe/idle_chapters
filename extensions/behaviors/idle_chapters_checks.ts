/**
 * Local quality gates for Idle Chapters: asset/schema validation, pytest, and
 * the web app's svelte-check + build. Each method writes a record only when its
 * gate passes; a failing gate throws so workflows stop on it.
 *
 * @module
 */
import { z } from "npm:zod@4";

const GlobalArgsSchema = z.object({
  // requirements.txt is the dependency source of truth (pyproject has none).
  python: z.array(z.string()).default([
    "uv",
    "run",
    "--with-requirements",
    "requirements.txt",
    "python",
  ]),
  webDir: z.string().default("apps/web"),
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

// Reuses the app's own loader: it validates each manifest asset against its
// schema, then checks cross-file id references.
const VALIDATE_ASSETS = [
  "from idle_chapters.content.repo import ContentRepo",
  "from idle_chapters.content.validators import validate_cross_file_integrity",
  "validate_cross_file_integrity(ContentRepo())",
  "print('assets valid')",
].join("; ");

const TAIL_CHARS = 4000;

async function runGate(
  gate: string,
  steps: Array<{ argv: string[]; cwd: string }>,
  context: Context,
) {
  const started = Date.now();
  let output = "";
  for (const { argv, cwd } of steps) {
    const [cmd, ...args] = argv;
    const result = await new Deno.Command(cmd, {
      args,
      cwd,
      signal: context.signal,
      stdout: "piped",
      stderr: "piped",
    }).output();
    const decoder = new TextDecoder();
    output += decoder.decode(result.stdout) + decoder.decode(result.stderr);
    if (!result.success) {
      throw new Error(
        `${gate} failed (exit ${result.code}) running \`${argv.join(" ")}\`:\n` +
          output.slice(-TAIL_CHARS),
      );
    }
  }
  const handle = await context.writeResource("gate", gate, {
    gate,
    commands: steps.map((s) => s.argv.join(" ")),
    durationMs: Date.now() - started,
    outputTail: output.slice(-TAIL_CHARS),
    checkedAt: new Date().toISOString(),
  });
  return { dataHandles: [handle] };
}

/** Quality gates for the Idle Chapters repo. */
export const behavior = {
  type: "@kagarmoe/idle-chapters-checks",
  version: "2026.10.21.1",
  globalArguments: GlobalArgsSchema,
  resources: {
    "gate": {
      description: "A quality gate that passed",
      schema: GateSchema,
      lifetime: "infinite",
      garbageCollection: 20,
    },
  },
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
  },
};
