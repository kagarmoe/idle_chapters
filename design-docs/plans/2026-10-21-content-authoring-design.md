# Content authoring — design (DRAFT, in conversation)

**Status: not approved.** The conversation paused on 2026-10-21 and resumes the next day. This
records where it stands and the options on the table, so it can pick up without re-asking.
Nothing here is decided unless marked "owner said".

## Why

Owner said: the last time they had a scene in mind, they opened a branch and started writing,
but got stuck on how to move through it: how to connect it to data, how to define what objects
are in the scene, and so on. They need to write both **scenes** and **storylets** by hand
(the most important part), and also add content to `/writing`, `/data`, `/thinking` (bare
pages today) and `/projects` (its purpose is unclear for now). They may want more small games
under `/play` later.

Owner said: **forms** would be useful. On `/writing`, `/data` and `/thinking` they may need to
get fussy with text and image layout, so a page form should switch between a text view and an
HTML view of the same content.

## What exists today (read from the code, 2026-10-21)

A hand-written scene is spread over four places, and mistakes in it fail silently:

| Piece | File | Holds |
|---|---|---|
| Scene | `assets/scenes/<name>.json` (`schemas/scene.schema.json`) | Shape only: `place_id`, `entry_node`, nodes → `action_ref` + `choices`. No prose, no conditions. |
| Actions | `assets/actions.json` (`schemas/actions.schema.json`) | The prose (`result`), the gate (`when`), what happens (`effects`), the label and intent words. Shared by every scene. |
| Manifest | `assets/scenes/manifest.json` | The scene file must be listed, or the game never sees it. |
| References | `collectibles.json`, `places.json`, `npcs.json` | Ids that `effects.add_items`, `place_id`, `move_to` and `when.location` point at. |

- There are only three authored scenes: `cottage_wake_v1`, `cottage_home_return_v1`, `town_bakery_v1`.
  Every other place gets a generated moment (`domain/scene_generator.py`).
- "Storylet" has no format in the code. `game_design/storylets_design.md` describes a system
  that was not built that way. `game_design/COTTAGE_STORYLET_GRAPH.md` is the accurate worked example.
- The silent failures:
  - a `choices` entry naming no node is dropped;
  - a missing `action_ref` is dropped;
  - a manifest entry with no file is skipped.
  - `validate_cross_file_integrity` checks none of the scene links, nor `add_items` against
    collectibles.
- Every scene's prose goes through no check: lexicons filter generated text only, and
  `tone_contract.md` §10 is a manual check.
- The schema rejects `tags` on actions, although the engine reads them.
- The site pages (`apps/web/src/routes/{projects,writing,data,thinking}/+page.svelte`) are
  one-paragraph placeholders hard-coded in Svelte, with no Markdown support. `/play` is a
  hand-made card per game.

## Today's real shape, for reference

`assets/scenes/cottage_wake_v1.json` (excerpt):

```json
{
  "scene_id": "cottage_wake_v1",
  "place_id": "cottage_home",
  "entry_node": "cottage_wake",
  "nodes": [
    { "node_id": "cottage_wake", "action_ref": "cottage_wake",
      "choices": ["rest_longer", "look_around", "make_tea", "pick_up_journal"] },
    { "node_id": "make_tea", "action_ref": "make_tea",
      "choices": ["look_around", "pick_up_journal", "head_to_town"] }
  ]
}
```

…and, in a different file, `assets/actions.json`:

```json
{
  "action_id": "make_tea",
  "label": "Make a cup of tea",
  "when": { "location": "cottage_home", "flags_not_set": ["made_tea"] },
  "result": "You fill the kettle and set it on to warm. …",
  "intent_signature": { "keywords": ["tea", "kettle", "brew"], "phrases": ["make tea", "cup of tea"] },
  "effects": {
    "add_items": { "chamomile_flowers": 1, "black_tea": 1, "biscuits": 1 },
    "set_flags": ["made_tea"]
  }
}
```

## Options — scenes and storylets

These are for discussion. They combine: S1 is the cheapest floor that every other option
still wants.

### S1. Keep the files; make mistakes loud, and write a guide

- Extend `validate_cross_file_integrity` to cover scenes:
  - the scene's `place_id` exists;
  - every `action_ref` exists;
  - every `choices` entry is a node;
  - `entry_node` is a node;
  - every manifest entry has a file and every scene file is listed;
  - `add_items` keys are collectibles.
- Write `design-docs/game_design/AUTHORING.md`: one worked scene from blank to playable.
- Cost: small. It doesn't fix the core friction of prose and shape living in different files.

### S2. One file per storylet, prose next to its choices

The writer writes one file. A loader (or a build step) splits it into the scene and actions
the engine already reads, so engine changes stay small. The ids come from the keys, so the
writer doesn't repeat them.

```json
{
  "storylet_id": "cottage_wake_v1",
  "place": "cottage_home",
  "when": { "flags_not_set": ["woke_today"] },
  "start": "wake",
  "beats": {
    "wake": {
      "text": "Morning light comes through the curtains…",
      "choices": ["rest_longer", "make_tea", "pick_up_journal"]
    },
    "make_tea": {
      "label": "Make a cup of tea",
      "text": "You fill the kettle and set it on to warm. …",
      "when": { "flags_not_set": ["made_tea"] },
      "gives": { "chamomile_flowers": 1, "black_tea": 1, "biscuits": 1 },
      "sets": ["made_tea"],
      "choices": ["look_around", "pick_up_journal", "head_to_town"]
    }
  }
}
```

- The `when` on the storylet becomes the entry action's `when` (how scenes are gated today).
- Intent words could default from the label, so a writer adds them only when needed.
- Open: is JSON the writing format, or Markdown with a small header, since prose is the bulk?

```markdown
---
storylet: cottage_wake_v1
place: cottage_home
start: wake
---

## wake
Morning light comes through the curtains…
→ rest_longer, make_tea, pick_up_journal

## make_tea "Make a cup of tea"
when: flags_not_set made_tea · gives: chamomile_flowers, black_tea, biscuits · sets: made_tea
You fill the kettle and set it on to warm. …
→ look_around, pick_up_journal, head_to_town
```

### S3. A form for storylets (owner floated forms)

A writer's page with:
- a beat list on the left, the selected beat's text on the right;
- dropdowns filled from real data (places, collectibles, flags already in use) instead of
  typed ids;
- a live check panel (S1's checks plus `tone_contract.md` §10).

It saves S2 files (or today's files). Sketch:

```html
<form class="storylet-editor">
  <header>
    <input name="storylet_id" value="cottage_wake_v1">
    <select name="place"><option>cottage_home</option><option>town</option>…</select>
  </header>
  <nav class="beats">
    <button aria-current="true">wake (start)</button>
    <button>make_tea</button>
    <button>+ beat</button>
  </nav>
  <section class="beat">
    <label>Label <input value="Make a cup of tea"></label>
    <label>Text <textarea rows="8">You fill the kettle…</textarea></label>
    <fieldset><legend>Gives</legend>
      <select><option>chamomile_flowers</option>…</select> × <input type="number" value="1">
    </fieldset>
    <fieldset><legend>Leads to</legend>
      <label><input type="checkbox" checked> look_around</label>
      <label><input type="checkbox" checked> head_to_town</label>
    </fieldset>
  </section>
  <aside class="checks">✓ all links resolve · ⚠ "head_to_town" moves the player: exit</aside>
</form>
```

## Options — site pages (`/writing`, `/data`, `/thinking`, `/projects`)

### P1. A file per piece in the repo

- Each piece is a file such as `content/writing/<slug>.md`, with a title, date and summary in
  a header.
- The page lists the pieces; `/writing/<slug>` shows one. Markdown via mdsvex (or a small
  Markdown renderer), and raw HTML is allowed inline for fussy layout.
- Images live in `apps/web/static/content/<slug>/`.

```markdown
---
title: Notes on idle games
date: 2026-10-21
summary: Why nothing in the game is required.
---

Plain paragraphs in Markdown…

<figure class="wide">
  <img src="/content/idle-notes/cottage.png" alt="The cottage at dusk">
  <figcaption>Sketch of the cottage.</figcaption>
</figure>
```

### P2. A form with a text ⇄ HTML switch (owner's idea)

- The same files as P1, edited in a form. Toggling to HTML converts the Markdown and shows
  the HTML source; toggling back keeps the HTML as-is (Markdown allows raw HTML).
- A preview pane renders it with the site's own styles.

```html
<form class="page-editor">
  <input name="title" value="Notes on idle games">
  <div role="tablist">
    <button role="tab" aria-selected="true">Text</button>
    <button role="tab">HTML</button>
    <button role="tab">Preview</button>
  </div>
  <textarea name="body">Plain paragraphs in Markdown…</textarea>
  <input type="file" name="images" accept="image/*" multiple>
</form>
```

### P3. A page in a hosted CMS

Not recommended: a second system to keep running, and content outside git and CI.

## The question that decides most of this (next to ask)

**Where do the forms run, and where does a save go?**

- **(a) Local only:**
  - the forms run under `npm run dev` on the owner's machine and write files in the repo;
  - publishing is the usual branch → PR → merge → Vercel deploy, so CI checks every scene.
  - No login or storage to build.
- **(b) On the live site:** forms behind a login save to a database or commit through the
  GitHub API. Edit from anywhere, but it needs auth, a write path and moderation of mistakes
  in production.

My guess (unconfirmed): (a). It keeps content in git, where checks and history already are.

## Also still open

- What `/projects` is for (owner doesn't remember).
- Whether "storylet" and "scene" should mean different things to a writer, or one word is enough.
- Whether `/play` needs a list of games driven by data, or a card per game stays fine. YAGNI
  until a second game exists.
- Owner's earlier unfinished writing is on closed-unmerged or abandoned branches; it may hold
  a draft scene to use as the first real test of whichever format wins.

## Order, once decided (sketch)

1. S1: loud checks and a guide. Useful whatever else is chosen.
2. The storylet format (S2), converted alongside the existing three scenes, which keep working.
3. The page format (P1) for one page, then the rest.
4. The forms (S3, P2) on top of the formats.
