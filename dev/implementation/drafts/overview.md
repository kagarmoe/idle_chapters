# Planning Document

## Layers

|  Layer  | Responsibility |
| :-----: | :------------: |
| Content |  What exists   |
| Engine  | What's allowed |
|  State  |  What's true   |
|   UI    |  What's shown  |

## Model

Idle chapters has five subsystems, each with a narrow responsibility:

[ UI / API ]
     ↓
[ Engine ]
     ↓
[ State Store ]
     ↑
[ Content Repository ] ← [ Generators (optional, later) ]

### Engine (the invariant core)

  This is the only non-negotiable component.

  Responsibilities:

- Evaluate predicates (when)
- Select eligible content
- Apply effects
- Advance state
- Produce a renderable view model

  Key property:

  The engine must be able to run without procedural generation or an LLM.

  If the engine can't function with hand-authored content alone, the architecture is upside down.

  Stable interface (pseudo-code)

  ```pseudo
  Engine.step(state, input?) -> {
    text,
    choices[],
    new_state,
    audit_log
  }
  ```

  This interface should not change even if everything else does.

### State store (boring on purpose)

Responsibilities:

- Hold canonical game state
- Persist / load
- Provide immutable snapshots to the engine

Important constraints:

- No logic
- No interpretation
- No “helpful” behavior

State {
  location
  time
  flags
  inventory
  stats
  seed
}

Treat state like a database row, not an object with methods.

### Content repository (authoritative but passive)

This is where storylets live.

Responsibilities:

- Store storylets/templates
- Validate schema
- Provide lookup by tag / location / id

It does not:

- Decide eligibility
- Pick “the best” storylet
- Modify state

ContentRepo.find_candidates(query) -> List[Storylet]

Key idea:

Content is inert until the engine touches it.

### Generators (procedural, optional, swappable)

This is where procedural generation and later LLMs live.

Important:
Generators do not talk to the engine directly.

They only ever:

- Produce content-shaped objects
- Insert them into the content repository
- Or return candidates through the same interface as static content

Generator.generate(state) -> List[Storylet]

You can have:

- AmbientGenerator
- DailyMoodGenerator
- LLMTextGenerator (future)

If you delete this entire box, the game still runs.

That's the architectural test.

### UI / API (FastAPI fits cleanly here)

Responsibilities:

- Accept user input
- Call Engine.step
- Render output
- Never contain game logic

This maps beautifully to FastAPI:

POST /step
  input: { choice_id? }
  output: { text, choices }

OpenAPI docs become a natural artifact, not extra work.

## Content

Content can:

1. Describe text and choices
2. Declare preconditions ("only show if player has mirror")
3. Declare effects ("set flag X", "add item Y")
4. Provide tags/metadate for selection ("cozy", "rainy")

Content cannot:

1. Read/write storage
2. Execute arbitrary code
3. Reach into global state outside the provided context
4. Decide what happens next by itself (beyond declaring options)

## Engine

Engine can:

1. Evaluate preconditions against state
2. Choose among eligible content (selection policy)
3. Apply effects (single mutation path)
4. Handle randomness deterministically (seeded)
5. Validate content (schema, missing references)

## Boundary pattern

### Content (data only)

```pseudo
Storylet {
  id: "kitchen_kettle_cold"
  tags: ["kitchen", "cozy", "idle"]
  priority: 10

  // declarative gating
  when: ALL(
    FLAG_NOT_SET("kettle_reheated_today"),
    LOCATION_IS("kitchen")
  )

  text: """
  The kettle has gone cold again.
  """

  choices: [
    Choice {
      id: "reheat"
      label: "Reheat it"
      when: HAS_ITEM("matches")
      effects: [
        SET_FLAG("kettle_reheated_today"),
        ADVANCE_TIME(minutes=5)
      ]
      goto: "kitchen_steam_rises"
    },

    Choice {
      id: "let_be"
      label: "Let it be"
      effects: [
        ADD_MOOD("wistful", +1),
        ADVANCE_TIME(minutes=1)
      ]
      goto: "kitchen_sit_quiet"
    }
  ]
}
```

Note: Content is declarative.

### Engine (evaluation + selection + resolution)

```pseudo
def next_node(state):
  candidates = content_repo.find_storylets(tags=[state.location])
  eligible = filter(candidates, s => eval_predicate(s.when, state))
  chosen = select_one(eligible, policy="highest_priority_then_weighted_random",
    seed=state.seed)
  return render_node(chosen, state)

def apply_choice(state, storylet_id, choice_id):
  storylet = content_repo.get(storylet_id)
  choice = storylet.choice(choice_id)

  assert eval_predicate(choice.when, state)  // prevent tampering / stale UI
  new_state = apply_effects(state, choice.effects)
  return transition(new_state, choice.goto)
```

State changes must be engine side
The engine is the only component that applies effects.

```pseudo
// content
effects: [ADD_ITEM("tea"), SET_FLAG("met_baker")]

// engine
function apply_effects(state, effects):
  for effect in effects:
    validate(effect)          // schema + allowed operations
    state = reducer(state, effect)  // pure transformation
  return state
```

Selection policy must be engine side

```pseudo
// engine selection policy
sort eligible by priority desc
top = take where priority == max
chosen = weighted_random(top, weights=storylet.weight, seed=state.seed)
```

Randomness must be engine side
Content can request a randome outcome, but the engine owns randomness and logs it

```pseudo
// content
effects: [RANDOM_CHOICE(
  outcomes=[
    {weight: 70, effects:[ADD_MOOD("calm", +1)]},
    {weight: 30, effects:[ADD_MOOD("restless", +1)]}
  ]
)]

// engine (seeded)
result = rng(seed=state.seed).pick(outcomes)
apply_effects(state, result.effects)
```

## Summary

Content provides:

- `text`
- `choices`
- `when` predicates
- `effects` lists
- tags, `weight`, `priority`
- optional `assets`/references (sound cue, icon id, etc)

Engine provides

- `state`
- `eligible choices` post-filter
- `rendered view model` for ui
- `next state` after action
- `audit trail` of what happened and why

How to implement:

1. Allowlist predicate/effect operators - no arbitrary expressions

    ```pseudo
    HAS_ITEM("matches")
    FLAG_SET("met_baker")
    STAT_GTE("warmth", 3)
    ```

2. State is immutable outside of engine by treating state updates like reducers

    ```pseudo
    new_state = reduce(state, effects)
    ```

3. Validate content at load time

  ```pseudo
  validate_storylet(storylet):
    ensure id unique
    ensure all goto targets exist
    ensure predicates are parseable
    ensure effects are allowed
  ```

## Content (story) boundaries

Choices aren't alays explicit. When the content ends, the engine chooses the next storylet

```pseudo
Choice { label:"Let it be", effects:[...], goto: "ENGINE_PICK_NEXT" }
```

## Litmus test

You're in a good place if:

- You could delete every generator and still have a working game
- You could rewrite the UI and not touch the engine
- You could add an LLM without changing engine code
- You could explain the architecture to another engineer without saying “it's kind of fuzzy”
