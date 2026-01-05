# Storylets and Assets: How They Work Together

This document explains **how storylets use assets** in *idle_chapters*,
and why they are intentionally separate concepts.

If this feels abstract at first, that’s normal — storylets are *not content*,
they are *logic shapes* that cause content to appear.

## One-sentence definition

**Storylets don’t contain assets.
Storylets reference assets, and the generator resolves those references at runtime.**

Assets are the *world*.
Storylets are the *shapes of moments* that occur in that world.

## Mental model: layered system

Think of the system in four layers, each with a distinct responsibility.

### 1. Assets — static world facts

Assets define *what exists*, not *what happens*.

Examples:

- `places.yaml` — locations and their sensory qualities
- `npcs.yaml` — people and animals
- `collectibles.yaml` — items, ingredients, tools
- `interactions.yaml` — things beings can say or do
- `tea.yaml`, `spells.yaml` — structured recipes
- `lexicons/*.yaml` — word pools and tone constraints

Key properties of assets:

- Static (not created or destroyed at runtime)
- Schema-validated
- Reusable across many moments
- Do nothing on their own

Assets are **ingredients**, not scenes.

### 2. Storylets — moment logic (not prose)

A **storylet describes what *kind* of thing happens next**, not the text of what happens.

A storylet:

- Declares constraints (where, when, who)
- Declares references (types of items, NPCs, interactions)
- Declares effects (inventory changes, flags, movement)
- Avoids concrete nouns when possible

Example storylet shape:

```yaml
place_id: beach_tidepools
entry_type: tea
tags: [quiet, found_object]
choices:
  - label: Gather something gentle
    effects:
      add_item: any:calming_herb
  - label: Rest
    effects:
      set_flag: rested
  - label: Leave the shore
    effects:
      move_place: beach_path
```

Important:

- The storylet does **not** name a specific herb
- It does **not** contain prose
- It defines *what must be resolved later*

Storylets are intentionally underspecified.

### 3. Generator — resolving storylets using assets

The generator is the glue between storylets and assets.

At runtime, it:

1. Reads current game state
   - location
   - inventory
   - flags
   - time / phase

2. Selects an appropriate storylet shape

3. Resolves storylet references using assets
   - `any:calming_herb` → choose from `collectibles.yaml` with tag `calming`
   - NPC actions → choose from `interactions.yaml`
   - Sensory words → choose from `lexicons`

4. Produces a fully concrete *storylet instance*
   - Still schema-valid
   - Debuggable and traceable

This is the first point where assets become text-adjacent.

### 4. Journal renderer — assets → prose

Only after a storylet is selected and resolved do we write prose.

The renderer:

- Takes the resolved storylet
- Pulls required asset details
- Applies a journal template
- Expands into Markdown

Example mapping:

| Storylet field | Asset source |
||-|
| `entry_type: tea` | tea journal template |
| `need_hint: calm` | calming lexicon |
| `ingredient_ref` | `collectibles.yaml` |
| `place_id` | `places.yaml` sensory data |

**Storylets never write sentences.
They cause sentences to be written.**

## End-to-end example

### Assets

```yaml
# collectibles.yaml
- item_id: chamomile_flower
  tags: [calming, herb]
```

```yaml
# places.yaml
- place_id: beach_tidepools
  sensory_focus: [salt, wind, light]
```

### Generated storylet instance (runtime)

```yaml
storylet_id: gen_beach_quiet_014
place_id: beach_tidepools
entry_type: tea
need_hint: calm
choices:
  - label: Gather something gentle
    effects:
      add_item: chamomile
```

### Journal output

```markdown

place: beach_tidepools
entry_type: tea
ingredients: [chamomile]


The wind moves softly across the tidepools.
You find chamomile growing where the sand stays cool.

What do you do next?
```

Note:

- The storylet never knew chamomile’s prose
- The asset never knew it would be used
- The renderer stitched them together

## Why this separation matters

This architecture enables:

- Infinite reuse of assets
- Procedural variation without authoring explosions
- Debuggable generation (“why did this happen?”)
- Later prose polish without logic refactors
- Real game feel instead of branching-novel sprawl

If storylets contained assets, this would become a branching novel.
Instead, this is a **world engine**.

## Guiding slogan

> **Assets are nouns.
> Storylets are verbs.
> The generator conjugates them.**

## Related directories

- `dev/game_design/` — design docs like this one
- `dev/images/` — diagrams and reference images for design docs
- `assets/` — world data
- `schemas/` — validation rules
- `generators/` — runtime resolution logic
  