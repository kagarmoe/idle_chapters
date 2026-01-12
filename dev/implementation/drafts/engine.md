# Game engine

The game engine is the coordinating layer.
It that determines what happens next when the player takes an action.
It sits between game content and player input.

**Content** is static
**State** is dynamic
The engine is the switchboard that connects content & state

Handles:

1. Game state
   1. The game engine is the single source of truth on the state of the world
   2. Game state is mutated through engine rules
   3. Game content can only read state, but not change it
2. Input validation and interpretation - boring & strict
   1. The RPG can have menu choices, simple commands, structured verbs
   2. The engine valdates the logic
   3. Maps it to an intent
   4. Rejects impossible actions
3. Eligibility logic
   1. The content says what could happen, but the engine determines if it can happen now.
   2. Eligibility = current state + preconditions + triggers/cooldowns
   3. Determines which scenes are currently eligible
   4. Which operations are visible & which are hidden
   5. Which events are mutually exclusive
4. Resolution rules - what changes as a result of an action
   1. The engine ensures outcomes are deterministic, traceable, and testable
   2. Applies state changes
   3. Records outcome
   4. Advances time/phase
5. Presentation handoff
   1. Selects content
   2. Passes content to the renderer
   3. Provides structured data alongside text

  ```json
  {
    "text": "The kettle has gone cold.",
    "choices": ["Reheat it", "Let it be"],
    "state_changes": {...}
  }
  ```

The game engine doesn't provide content - text, graphics, or sound.
