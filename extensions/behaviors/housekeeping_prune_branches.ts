/**
 * `pruneMergedBranches` on `@maphew/housekeeping`: delete local and remote
 * branches whose work is already on main, and nothing else. (housekeeping's
 * own `check` lists `git branch --merged`, which misses squash merges.)
 *
 * PRs here are squash-merged, so git alone cannot tell a merged branch; GitHub
 * can. A branch is deleted only when a PR from it was merged and the branch tip
 * is exactly the commit that PR merged (no work after it). Always kept: the
 * owner's hand-curated branches (`kg/` prefix), main, Dolt's remote-info
 * branch, branches with an open or closed-unmerged PR or no PR at all, branches
 * with commits after their merge, and branches checked out in a worktree.
 *
 * Dry run by default. With `apply`, every deleted tip is first appended to a
 * backup file in the repository's git directory, so `git branch <name> <sha>`
 * restores it.
 *
 * @module
 */
import { z } from "npm:zod@4";

const ALWAYS_KEEP = new Set(["main", "__dolt_remote_info__", "HEAD"]);

export interface Pr {
  number: number;
  state: "OPEN" | "CLOSED" | "MERGED";
  headRefName: string;
  headRefOid: string;
}

export interface Verdict {
  scope: "local" | "remote";
  branch: string;
  sha: string;
  action: "delete" | "keep";
  reason: string;
}

/** The whole rule, pure, so the self-check below can pin it. */
export function classify(
  scope: "local" | "remote",
  branch: string,
  sha: string,
  prs: Pr[],
  worktreeBranches: Set<string>,
  protectPrefixes: string[],
): Verdict {
  const keep = (reason: string): Verdict => ({ scope, branch, sha, action: "keep", reason });
  if (ALWAYS_KEEP.has(branch)) return keep("protected");
  if (protectPrefixes.some((p) => branch.startsWith(p))) return keep("hand-curated");
  const mine = prs.filter((p) => p.headRefName === branch);
  const nums = (ps: Pr[]) => ps.map((p) => `#${p.number}`).join(",");
  if (mine.length === 0) return keep("no PR");
  if (mine.some((p) => p.state === "OPEN")) return keep(`open PR ${nums(mine.filter((p) => p.state === "OPEN"))}`);
  const merged = mine.filter((p) => p.state === "MERGED");
  if (merged.length === 0) return keep(`PR closed without merging ${nums(mine)}`);
  if (!merged.some((p) => p.headRefOid === sha)) return keep(`commits after merge of ${nums(merged)}`);
  if (scope === "local" && worktreeBranches.has(branch)) return keep(`merged ${nums(merged)}, but checked out in a worktree`);
  return { scope, branch, sha, action: "delete", reason: `merged ${nums(merged)}` };
}

// Runs on every call: a wrong rule must fail loudly before it deletes anything.
function selfCheck(): void {
  const prs: Pr[] = [
    { number: 1, state: "MERGED", headRefName: "done", headRefOid: "a" },
    { number: 2, state: "MERGED", headRefName: "kg/mine", headRefOid: "b" },
    { number: 3, state: "CLOSED", headRefName: "closed", headRefOid: "c" },
    { number: 4, state: "MERGED", headRefName: "more", headRefOid: "d" },
  ];
  const wt = new Set(["done-here"]);
  prs.push({ number: 5, state: "MERGED", headRefName: "done-here", headRefOid: "e" });
  const cases: [string, string, "local" | "remote", "delete" | "keep"][] = [
    ["done", "a", "remote", "delete"],
    ["kg/mine", "b", "remote", "keep"],
    ["closed", "c", "remote", "keep"],
    ["more", "d2", "remote", "keep"],
    ["nopr", "x", "local", "keep"],
    ["main", "m", "remote", "keep"],
    ["done-here", "e", "local", "keep"],
    ["done-here", "e", "remote", "delete"],
  ];
  for (const [branch, sha, scope, want] of cases) {
    const got = classify(scope, branch, sha, prs, wt, ["kg/"]).action;
    if (got !== want) throw new Error(`prune rule self-check: ${scope} ${branch} → ${got}, want ${want}`);
  }
}

interface Ctx {
  globalArgs: { projectDir?: string };
  writeResource: (spec: string, name: string, data: Record<string, unknown>) => Promise<{ name: string }>;
}

async function run(cwd: string, cmd: string, args: string[]): Promise<string> {
  // swamp-quality-ignore deno-command: git and gh are the tools this wraps; args are an argv array (no shell).
  const out = await new Deno.Command(cmd, { args, cwd, stdout: "piped", stderr: "piped" }).output();
  const stdout = new TextDecoder().decode(out.stdout);
  if (!out.success) throw new Error(`${cmd} ${args.join(" ")} failed: ${new TextDecoder().decode(out.stderr).trim()}`);
  return stdout;
}

function refs(text: string): [string, string][] {
  return text.split("\n").filter(Boolean).map((l) => l.split(" ") as [string, string]);
}

const VerdictSchema = z.object({
  scope: z.enum(["local", "remote"]),
  branch: z.string(),
  sha: z.string(),
  action: z.enum(["delete", "keep"]),
  reason: z.string(),
});

export const extension = {
  type: "@maphew/housekeeping",
  resources: {
    pruneReport: {
      description: "Which branches pruneMergedBranches deleted (or would delete) and which it kept, with why",
      schema: z.object({
        applied: z.boolean(),
        backupFile: z.string().nullable(),
        deleted: z.array(VerdictSchema),
        kept: z.array(VerdictSchema),
        ranAt: z.string(),
      }),
      lifetime: "infinite",
      garbageCollection: 10,
    },
  },
  methods: [{
    pruneMergedBranches: {
      description:
        "Delete local and remote branches whose PR was merged and that have no later commits; keeps kg/ branches, unmerged, PR-less and worktree branches. Dry run unless apply=true",
      arguments: z.object({
        apply: z.boolean().default(false).describe("Actually delete; otherwise only report"),
        protectPrefixes: z.array(z.string()).default(["kg/"]).describe("Branch prefixes never deleted"),
        remote: z.string().regex(/^[^-]/).default("origin").describe("Remote whose branches are pruned"),
      }),
      execute: async (args: { apply: boolean; protectPrefixes: string[]; remote: string }, ctx: Ctx) => {
        selfCheck();
        const cwd = ctx.globalArgs.projectDir ?? ".";
        const remote = args.remote;
        await run(cwd, "git", ["fetch", "--quiet", "--prune", remote]);
        const local = refs(await run(cwd, "git", ["for-each-ref", "--format=%(refname:short) %(objectname)", "refs/heads"]));
        const remoteRefs = refs(
          await run(cwd, "git", ["for-each-ref", "--format=%(refname:short) %(objectname)", `refs/remotes/${remote}`]),
        )
          .map(([ref, sha]) => [ref.slice(remote.length + 1), sha] as [string, string])
          .filter(([name]) => name !== "" && name !== "HEAD");
        const worktrees = new Set(
          (await run(cwd, "git", ["worktree", "list", "--porcelain"])).split("\n")
            .filter((l) => l.startsWith("branch refs/heads/")).map((l) => l.slice("branch refs/heads/".length)),
        );
        const prs = JSON.parse(
          await run(cwd, "gh", ["pr", "list", "--state", "all", "--limit", "5000", "--json", "number,state,headRefName,headRefOid"]),
        ) as Pr[];

        const verdicts = [
          ...remoteRefs.map(([b, s]) => classify("remote", b, s, prs, worktrees, args.protectPrefixes)),
          ...local.map(([b, s]) => classify("local", b, s, prs, worktrees, args.protectPrefixes)),
        ];
        const deleted = verdicts.filter((v) => v.action === "delete");
        let backupFile: string | null = null;
        if (args.apply && deleted.length > 0) {
          const gitDir = (await run(cwd, "git", ["rev-parse", "--path-format=absolute", "--git-common-dir"])).trim();
          backupFile = `${gitDir}/deleted-merged-branches.txt`;
          const lines = deleted.map((v) => `${new Date().toISOString()} ${v.scope} ${v.branch} ${v.sha}`).join("\n");
          await Deno.writeTextFile(backupFile, lines + "\n", { append: true });
          const remoteNames = deleted.filter((v) => v.scope === "remote").map((v) => v.branch);
          if (remoteNames.length > 0) await run(cwd, "git", ["push", "--quiet", remote, "--delete", ...remoteNames]);
          const localNames = deleted.filter((v) => v.scope === "local").map((v) => v.branch);
          if (localNames.length > 0) await run(cwd, "git", ["branch", "-D", ...localNames]);
        }
        const handle = await ctx.writeResource("pruneReport", "prune-report", {
          applied: args.apply,
          backupFile,
          deleted,
          kept: verdicts.filter((v) => v.action === "keep"),
          ranAt: new Date().toISOString(),
        });
        return { dataHandles: [handle] };
      },
    },
  }],
};
