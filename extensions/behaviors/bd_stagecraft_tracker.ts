/**
 * Beads as a stagecraft tracker: `describe` and `operate` on `@maphew/bd`, to
 * stagecraft's tracker contract 1 (TRACKERS.md in @swamp/stagecraft). A
 * `@swamp/stagecraft/publisher` sits in front and keeps the delivery ledger,
 * cursor and ticket index; this only makes one bd operation and writes its
 * answer. Offers the six operations every tracker has, no optional capability.
 *
 * Relations are bd dependencies. `X parent_of Y` is Y depending on X
 * (parent-child); `X blocked_by Y` (blocks), `X related_to Y` (related) and
 * `X duplicate_of Y` (duplicates, via `bd duplicate`, which closes X) are X
 * depending on Y.
 *
 * @module
 */
import { z } from "npm:zod@4";

const TRACKER = "beads";
const RELATION_TYPES = ["parent_of", "blocked_by", "related_to", "duplicate_of"] as const;
type RelationType = typeof RELATION_TYPES[number];
type Kind = "auth" | "not_found" | "rate_limited" | "invalid" | "upstream";

// bd dependency type ↔ relation type, and whether the dependent (the side that
// depends) reads it as outgoing. Only parent-child points the other way.
const BY_DEP: Record<string, { type: RelationType; dependentOutgoing: boolean }> = {
  "parent-child": { type: "parent_of", dependentOutgoing: false },
  blocks: { type: "blocked_by", dependentOutgoing: true },
  related: { type: "related_to", dependentOutgoing: true },
  duplicates: { type: "duplicate_of", dependentOutgoing: true },
};
const DEP_OF: Record<RelationType, string> = {
  parent_of: "parent-child",
  blocked_by: "blocks",
  related_to: "related",
  duplicate_of: "duplicates",
};
const MAX_PARENT_DEPTH = 10;

interface Relation {
  type: RelationType;
  direction: "outgoing" | "incoming";
  issue: string;
  display: string;
}

interface Ticket {
  id: string;
  display: string;
  title: string;
  status: { id: string; name: string };
  relations: Relation[];
  description?: string;
  labels?: string[];
  assignees?: string[];
  createdAt?: string;
  updatedAt?: string;
  activity?: { kind: "comment"; id: string; author?: string; body: string; at: string }[];
}

class Failure extends Error {
  constructor(readonly kind: Kind, readonly detail: string) {
    super(detail);
  }
}

interface Ctx {
  globalArgs: { bdCommand?: string; bdDir?: string };
  readResource: (name: string) => Promise<Record<string, unknown> | null>;
  writeResource: (spec: string, name: string, data: Record<string, unknown>) => Promise<{ name: string }>;
}

async function bd(ctx: Ctx, args: string[]): Promise<unknown> {
  // swamp-quality-ignore deno-command: the bd CLI is the tracker this wraps; args are an argv array (no shell).
  const out = await new Deno.Command(ctx.globalArgs.bdCommand ?? "bd", {
    args,
    cwd: ctx.globalArgs.bdDir ?? ".",
    stdout: "piped",
    stderr: "piped",
  }).output();
  const stdout = new TextDecoder().decode(out.stdout).trim();
  const stderr = new TextDecoder().decode(out.stderr).trim();
  let parsed: unknown = null;
  try {
    parsed = stdout ? JSON.parse(stdout) : null;
  } catch { /* bd printed text, not JSON: only the failure paths below read it */ }
  const error = (parsed as { error?: string } | null)?.error;
  if (out.success && !error) return parsed;
  const detail = (error ?? [stderr, stdout].filter(Boolean).join("\n")) || `bd exited ${out.code}`;
  if (/not found|no issues found/i.test(detail)) throw new Failure("not_found", detail.split("\n")[0]);
  if (/invalid|validation failed/i.test(detail)) throw new Failure("invalid", detail);
  throw new Failure("upstream", detail);
}

function relationsFrom(deps: unknown, dependent: boolean): Relation[] {
  if (!Array.isArray(deps)) return [];
  return deps.flatMap((d: Record<string, unknown>) => {
    const map = BY_DEP[String(d.dependency_type)];
    if (!map) return [];
    const outgoing = map.dependentOutgoing === dependent;
    return [{ type: map.type, direction: outgoing ? "outgoing" : "incoming", issue: String(d.id), display: String(d.id) }];
  });
}

async function fetchTicket(ctx: Ctx, ref: string): Promise<Ticket> {
  const shown = await bd(ctx, ["show", ref, "--json"]);
  const raw = (Array.isArray(shown) ? shown[0] : shown) as Record<string, unknown> | undefined;
  if (!raw?.id) throw new Failure("not_found", `no beads issue ${ref}`);
  const id = String(raw.id);
  const dependents = await bd(ctx, ["dep", "list", id, "--direction", "up", "--json"]);
  const comments = await bd(ctx, ["comments", id, "--json"]);
  const status = String(raw.status);
  const labels = Array.isArray(raw.labels) && raw.labels.length ? raw.labels.map(String) : [String(raw.issue_type)];
  return {
    id,
    display: id,
    title: String(raw.title ?? ""),
    status: { id: status, name: status },
    relations: [...relationsFrom(raw.dependencies, true), ...relationsFrom(dependents, false)],
    description: typeof raw.description === "string" ? raw.description : "",
    labels,
    assignees: raw.assignee ? [String(raw.assignee)] : [],
    createdAt: String(raw.created_at),
    updatedAt: String(raw.updated_at),
    activity: (Array.isArray(comments) ? comments : []).map((c: Record<string, unknown>) => ({
      kind: "comment" as const,
      id: String(c.id),
      ...(c.author ? { author: String(c.author) } : {}),
      body: String(c.text ?? ""),
      at: String(c.created_at),
    })),
  };
}

function has(from: Ticket, type: RelationType, to: Ticket): boolean {
  return from.relations.some((r) => r.type === type && r.direction === "outgoing" && r.issue === to.id) ||
    to.relations.some((r) => r.type === type && r.direction === "incoming" && r.issue === from.id);
}

/** The relation rules every tracker keeps (TRACKERS.md); bd checks none of them. */
async function checkRelate(ctx: Ctx, from: Ticket, type: RelationType, to: Ticket): Promise<boolean> {
  const refuse = (detail: string): never => {
    throw new Failure("invalid", detail);
  };
  if (from.id === to.id) refuse(`${from.id} cannot be related to itself`);
  if (has(from, type, to)) return true;
  const parentOf = (t: Ticket) => t.relations.find((r) => r.type === "parent_of" && r.direction === "incoming");
  if (type === "parent_of") {
    const parent = parentOf(to);
    if (parent) refuse(`${to.id} already has a parent, ${parent.issue}; unrelate it first`);
    const seen = new Set([to.id]);
    let current = from;
    for (let depth = 0; depth < MAX_PARENT_DEPTH; depth++) {
      const up = parentOf(current);
      if (!up) break;
      if (seen.has(up.issue)) refuse(`${from.id} parent_of ${to.id} would form a circular parent chain`);
      seen.add(up.issue);
      current = await fetchTicket(ctx, up.issue);
    }
  }
  if (type === "duplicate_of") {
    const dup = (t: Ticket, direction: Relation["direction"]) =>
      t.relations.filter((r) => r.type === "duplicate_of" && r.direction === direction);
    const other = dup(from, "outgoing")[0];
    if (other) refuse(`${from.id} is already a duplicate of ${other.issue}; unrelate that first`);
    const chain = dup(to, "outgoing")[0];
    if (chain) refuse(`${to.id} is a duplicate of ${chain.issue}; mark ${from.id} a duplicate of ${chain.issue} instead`);
    const dups = dup(from, "incoming");
    if (dups.length) refuse(`${dups.map((r) => r.issue).join(", ")} duplicate ${from.id}; re-point them first`);
  }
  return false;
}

const Id = z.string().min(1);
const Rel = z.object({ issue: Id, type: z.enum(RELATION_TYPES), to: Id });

const OPERATIONS: Record<string, (ctx: Ctx, req: unknown) => Promise<unknown>> = {
  fetch_issue: (ctx, req) => fetchTicket(ctx, z.object({ issue: Id }).parse(req).issue),

  async create(ctx, req) {
    const { title, body, type } = z.object({ title: Id, body: z.string(), type: Id }).parse(req);
    const made = await bd(ctx, ["create", `--description=${body}`, `--type=${type}`, "--json", "--", title]) as {
      id?: string;
    };
    if (!made?.id) throw new Failure("upstream", "bd create returned no id");
    return fetchTicket(ctx, made.id);
  },

  async comment(ctx, req) {
    const { issue, body } = z.object({ issue: Id, body: z.string() }).parse(req);
    await fetchTicket(ctx, issue);
    const made = await bd(ctx, ["comments", "add", issue, "--json", "--", body]) as { id?: string };
    if (!made?.id) throw new Failure("upstream", "bd comments add returned no id");
    return { id: String(made.id) };
  },

  async set_status(ctx, req) {
    const { issue, status } = z.object({ issue: Id, status: z.string() }).parse(req);
    const ticket = await fetchTicket(ctx, issue);
    if (ticket.status.name === status) return { changed: false, status: ticket.status };
    await bd(ctx, ["update", ticket.id, `--status=${status}`, "--json"]);
    return { changed: true, status: { id: status, name: status } };
  },

  async relate(ctx, req) {
    const { issue, type, to } = Rel.parse(req);
    const from = await fetchTicket(ctx, issue);
    const target = await fetchTicket(ctx, to);
    if (await checkRelate(ctx, from, type, target)) return { changed: false };
    if (type === "duplicate_of") await bd(ctx, ["duplicate", from.id, `--of=${target.id}`, "--json"]);
    else if (type === "parent_of") await bd(ctx, ["dep", "add", target.id, from.id, `--type=${DEP_OF[type]}`, "--json"]);
    else await bd(ctx, ["dep", "add", from.id, target.id, `--type=${DEP_OF[type]}`, "--json"]);
    return { changed: true };
  },

  async unrelate(ctx, req) {
    const { issue, type, to } = Rel.parse(req);
    const from = await fetchTicket(ctx, issue);
    const target = await fetchTicket(ctx, to);
    if (!has(from, type, target)) return { changed: false };
    // bd keeps one dependency per pair, so removing the pair removes exactly this relation.
    const [child, parent] = type === "parent_of" ? [target.id, from.id] : [from.id, target.id];
    await bd(ctx, ["dep", "remove", child, parent, "--json"]);
    return { changed: true };
  },
};

const DescriptionSchema = z.object({
  tracker: z.string(),
  contract: z.number(),
  origin: z.string(),
  capabilities: z.object({ history: z.boolean(), assign: z.boolean(), pullRequests: z.boolean() }),
  closesDuplicates: z.boolean(),
});
const AnswerSchema = z.looseObject({ operation: z.string(), run: z.string().optional(), ok: z.boolean() });

export const extension = {
  type: "@maphew/bd",
  resources: {
    description: {
      description: "What this beads tracker says of itself, so a stagecraft factory can bind to it",
      schema: DescriptionSchema,
      lifetime: "infinite",
      garbageCollection: 5,
    },
    answer: {
      description: "One stagecraft tracker operation's answer: its result, or its failure",
      schema: AnswerSchema,
      lifetime: "infinite",
      garbageCollection: 5,
    },
  },
  methods: [{
    describe: {
      description: "Record what this tracker is (beads, contract 1), so a stagecraft publisher and factory can bind to it",
      arguments: z.object({}),
      execute: async (_args: Record<string, never>, ctx: Ctx) => {
        const handle = await ctx.writeResource("description", "description", {
          tracker: TRACKER,
          contract: 1,
          origin: "snapshot",
          capabilities: { history: false, assign: false, pullRequests: false },
          closesDuplicates: true,
        });
        return { dataHandles: [handle] };
      },
    },
    operate: {
      description:
        "Make one stagecraft tracker operation on beads and write its answer under the given name; an answer that already succeeded is kept and nothing is made again",
      arguments: z.object({
        operation: z.string(),
        request: z.union([z.record(z.string(), z.unknown()), z.string()]),
        answer: z.string().regex(/^answer-[A-Za-z0-9._-]+$/),
        run: z.string().optional(),
      }),
      execute: async (
        args: { operation: string; request: Record<string, unknown> | string; answer: string; run?: string },
        ctx: Ctx,
      ) => {
        const prior = await ctx.readResource(args.answer);
        if (prior?.ok === true) return { dataHandles: [] };
        const base = { operation: args.operation, ...(args.run ? { run: args.run } : {}) };
        let answer: Record<string, unknown>;
        try {
          const op = OPERATIONS[args.operation];
          if (!op) throw new Failure("invalid", `beads does not offer ${args.operation}: ${Object.keys(OPERATIONS).join(", ")}`);
          const request = typeof args.request === "string" ? JSON.parse(args.request) : args.request;
          answer = { ...base, ok: true, result: await op(ctx, request) };
        } catch (e) {
          const failure = e instanceof Failure
            ? e
            : e instanceof z.ZodError || e instanceof SyntaxError
            ? new Failure("invalid", e.message)
            : new Failure("upstream", e instanceof Error ? e.message : String(e));
          answer = { ...base, ok: false, kind: failure.kind, detail: failure.detail };
        }
        return { dataHandles: [await ctx.writeResource("answer", args.answer, answer)] };
      },
    },
  }],
};
