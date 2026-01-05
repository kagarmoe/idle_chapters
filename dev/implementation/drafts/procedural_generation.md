# Procedural generation of content

The engine governs narrative state and eligibility.
Procedural generation is used only to supply low-stakes, high-variance content.
The engine enforces strict constraints/rules.

Procedural generation is not a peer of the engine.

It is:

- A supplier to the content repository
- Called before or during candidate lookup
- Fully constrained by the engine’s rules

Two safe patterns:

1. Pre-fill (on load / per day)

on_new_day(state):
  content_repo.add(ambient_generator.generate(state))

1. Lazy fallback

candidates = content_repo.find(...)
if candidates.empty():
  content_repo.add(generator.generate(state))

In both cases:

- The engine stays ignorant of how content appeared
- It just enforces rules

## Model

Procedural Generation
        ↓
Content (storylets, locations, text fragments)
        ↓
Engine (rules, eligibility, state changes)
        ↓
State (what’s true right now)
        ↓
UI (what the player sees)

## Why procedural generation

Procedural generation creates many pieces of content, so I don't have to author all of it.

Procedural generation is a function that produces storylet-shaped objects.

### Example

Hand-authored content

```json
Storylet {
  id: "library_rain_evening"
  when: ALL(LOCATION("library"), TIME("evening"), WEATHER("rain"))
  text: "Rain taps softly against the tall windows."
}
```

Procedurally generated content:

```pseudo
generate_library_ambience(state):
  mood = weighted_pick(["quiet", "dusty", "warm"], seed=state.seed)
  sound = weighted_pick(["rain", "wind", "silence"], seed=state.seed)

  return Storylet {
    id: hash(mood, sound, state.time)
    tags: ["library", "ambient"]
    when: LOCATION("library")
    text: f"The library feels {mood}. Outside, there is {sound}."
  }
```

1. Provide texture

   - Ambient descriptions
   - Weather, time-of-day flavor
   - Idle thoughts
   - Repeated actions (“wait”, “walk”, “sit”)

2. Combinatorics instead of branching

  Keeps content small and expressive.
  Instead of:

  ```pseudo
  Rain + Evening + Kitchen = one storylet
  Rain + Morning + Kitchen = another storylet
  Clear + Evening + Kitchen = another storylet
  ```

  Use a function like:

  ```pseudo
    text = f"{weather_phrase()} {time_phrase()} in the {location}."
    ```

3. Controlled surprise

To avoid chaos with procedural generation:
 - Seed randomness from state
 - Limit generators to safe vocabularies
 - Keep effects small or zero

For example to make the same day always feel the same so it is psychologically calming.

```pseudo
seed = hash(day_number, location)
rng = Random(seed)
``

Procedural generation should not:
 - Modify state directly
 - Decide what content is eligible
 - Contain game logic
 - Create irreversible consequences unless the engine approves them

Bad boundary (don’t do this):

```pseudo
if rng.roll() < 0.1:
  state.flags.add("house_burned_down")
```

Good boundary:

```pseudo
effects: [REQUEST_EVENT("house_fire")]
```

Then the engine decides whether that event is allowed at all.

A strong engine can survive bad content.
Bad engine logic cannot be saved by clever generation.

## Game Engine vs Precedural Generation

|Aspect | Game Engine | Procedural Generation|
|:-----:|:-----------:|:---------------------"|
|Purpose | Enforce rules |Create content|
|Owns state? | Yes | No|
|Determinism |Required |Optional (but recommended)|
|Failure mode |Bugs, exploits |Blandness or nonsense|
|Testing |Logic-heavy |Distribution & bounds|
|Longevity |Core architecture |Swappable strategy|

## Implementations under consideration

1. Pre-generation (offline or on load)

    Generate a pool of content once per day / chapter / session.

    ```pseudo
    daily_ambience = generate_ambient_storylets(seed=day)
    content_repo.add(daily_ambience)
    ```

    The content feels authored but costs little.

2. Just-in-time generation

    Generate content when needed.

    ```pseudo
      if no ambient storylet eligible:
        inject(generate_ambient_storylet(state))
    ```

    Good for fallback

3. Template expansion

    Hybrid content with slots:

    ```pseudo
      Template {
        text: "You think about {memory}."
        slots:
          memory: weighted(["the smell of coffee", "an old letter",
          "nothing in particular"])
      }
    ```

## Downsides

- Procedural generation can undermine tone.
- Procedural generation can create nonsense.
