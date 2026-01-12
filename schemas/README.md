# Schemas

## Map schemas to files

|schema| file | purpose |
|------|------|---------|
|actions.schema.json | assets/actions.json | Defines actions that a player can take |
|collectibles.schema.json | assets/collectibles.json | Defines items that a player can pick up and use |
|common.schema.json | -- | Shared definitions used by other schemas |
|conditions.schema.json | -- | Conditions that must be met for an action to be available in a given location |
|interactions.schema.json | assets/interactions.json | Defines interactions a player can have with NPCs |
|lexicons.schema.json | lexicons/*.json | Defines global and location vocabulary |
|npcs.schema.json | assets/npcs.json | Defines NPCs and where they are found (global, zone, location) |
|places.schema.json | assets/places.json | Defines locations in the idle_chapters world |
|players.schema.json | assets/player.json | Defines player data; assets/player.json stores created players () |
|scene.schema.json | assets/scenes/<name>.json | Defines a specific scene |
|scenes_manifest.schema.json | -- | Manifest listing scenes available in the game |
|sessions.schema.json | -- | Runtime session stored in MongoDB; combines player identity with game state |
|spells.schema.json | assets/spells.json | Defines the format for spells in the collection |
|teas.schema.json | assets/tea.json | Defines the format for teas in the collection |


### Object collection and items

1. `action` in collection `actions`
2. `item` in collection `collectibles`
3. `condition` in collection `conditions`
4. `interaction` in collection `interactions`
5. `lexicon` in collection `lexicons`
6. `npc` in collection `npcs`
7. `place` in collection `places`
8. `player` in collection `players`
9. `scene` in collection `scenes`
10. `scene_id` entries in collection `scene_manifest` (top-level `scenes` array)
11. `session` in collection `sessions`
12. `spell` in collection `spells`
13. `tea` in collection `teas`

### Map for schema drafts

|schema| file | purpose |
|------|------|---------|
|ingredient_substitutions.schema.json | drafts/ingredient_substitutions.schema.json | Draft: substitute ingredients for spells/recipes; moved to `drafts/` until implemented |
|journal_page.schema.json | drafts/journal_page.schema.json | Draft: journal page schema; moved to `drafts/` until implemented |
|journal_templates.schema.json | drafts/journal_templates.schema.json | Draft: journal templates; moved to `drafts/` until implemented |

## Collections & required fields

|schema| collection | required fields (top-level / per-item) |
|------|-----------|---------------------------------------|
|actions.schema.json | `actions` | top-level: `actions` / per-action: `action_id`, `label`, `intent_signature` |
|collectibles.schema.json | `collectibles` | top-level: `collectibles` / per-item: `item_id`, `display_name`, `item_type`, `symbolic_meaning`, `cozy_association`, `tags`, `origin_scope`, `player_need_satisfied`, `safety_category`, `usable_in`, `stock_behavior` |
|interactions.schema.json | `interactions` | top-level: `interactions` / per-interaction: `interaction_id`, `npc_kind`, `interaction_type`, `text`, `conditions`, `selection` |
|lexicon.schema.json | `lexicon` | top-level: `lexicon` / per-entry: `lexicon_type`, `key`, `scope` (and either `words` or `extends`) |
|npcs.schema.json | `npcs` | top-level: `npcs` / per-npc: `npc_id`, `display_name`, `npc_kind`, `home_location_id`, `spawn_rules`, `interactions` (note: `spawn_rules.presence` required; `species` required when `npc_kind` == `animal`) |
|places.schema.json | `zones`, `places` | top-level: `zones`, `places` / zone required: `zone_id`, `display_name`, `mood` / place required: `place_id`, `display_name`, `zone_id`, `mood`, `profile` (profile requires `meaning`, `sensory_focus`, `social_level`, `time_sensitivity`, `weather_sensitivity`, `emotional_range`, `player_need_satisfied`) |
|spells.schema.json | `spell_recipes` | top-level: `spell_recipes` / per-recipe: `spell_id`, `display_name`, `incantation_style`, `incantation`, `narrative_purpose`, `target_need`, `place_affinity`, `ingredients`, `ritual_steps`, `tone`, `repeatable`, `output` |
|teas.schema.json | `tea_recipes` | top-level: `tea_recipes` / per-recipe: `recipe_id`, `display_name`, `intent`, `target_need`, `allowed_times`, `base_liquid`, `ingredients`, `steps`, `serves`, `repeatable` |
|players.schema.json | runtime/player | top-level: none required / nested: `premise.facets` is required when `premise` is present; otherwise player fields are optional |
|scene.schema.json | `scene` | top-level: `scene_id`, `place_id`, `entry_node`, `nodes` / per-node: `node_id`, `action_ref`, `choices` |
|sessions.schema.json | runtime/session | top-level: `session_id`, `state`, `created_at` / `state` requires `current_location` |

### actions.schema.json

The `actions.schema.json` file defines the structure for actions in the game.

#### Collection object
- **`actions`** (array, required): A list of action objects.
  - **Items**: Each item in the array is an `Action Object`Collection object.

#### Action object
- **`action_id`** (string, required): A unique identifier for the action. Referenced from `common.schema.json`.
- **`label`** (string, required): A label for the action. Referenced from `common.schema.json`.
- **`when`** (object or null, optional): Specifies the conditions under which the action is available. Defaults to `null`.
- **`effects`** (object, optional): Describes the effects of the action. Referenced from `common.schema.json`.
- **`result_variants`** (array, optional): A list of result variants. Defaults to an empty array.
- **`intent_signature`** (object, required): Specifies the intent signature for the action. Contains the following fields:
  - **`keywords`** (array, required): A list of keywords associated with the action.
  - **`phrases`** (array, required): A list of phrases associated with the action.

---

### collectibles.schema.json

The `collectibles.schema.json` file defines the structure for collectible items in the game.

#### Collection object
- **`collectibles`** (array, required): A list of collectible item objects.
  - **Items**: Each item in the array is a `Collectible Object`Collection object.

#### Collectible object
- **`item_id`** (string, required): A stable identifier used by recipes, inventory, and events. Referenced from `common.schema.json`.
- **`display_name`** (string, required): The name of the collectible item. Referenced from `common.schema.json`.
- **`item_type`** (string, required): The type of the item. Possible values include `Botanical`, `TeaBase`, `Crystal`, `Tool`, `Currency`, `Trinket`, and `Food`.
- **`botanical_kind`** (string or null, optional): Specifies the botanical kind if the item type is `Botanical`. Possible values include `Flower`, `Herb`, `Leaf`, `Root`, `Bark`, `Blend`, or `null` (default).
- **`symbolic_meaning`** (string, required): The symbolic meaning of the item.
- **`cozy_association`** (string, required): The cozy association of the item.
- **`tags`** (array, optional): A list of tags associated with the item. Defaults to an empty array.
- **`origin_scope`** (string, required): Specifies how the world produces this item. Possible values include `global`, `zone`, `npc`, `quest`, `starting`, and `craft`.
- **`origin_ref`** (string or null, optional): A reference ID depending on the `origin_scope`. Defaults to `null`.
- **`player_need_satisfied`** (string, required): The player need satisfied by the item.
- **`notes`** (string or null, optional): Additional notes about the item. Defaults to `null`.
- **`safety_category`** (string, required): The safety category of the item. Possible values include `generally_safe`, `caution_humans`, `pet_unsafe`, `toxic`, and `non_ingestible`.
- **`usable_in`** (array, required): A list of contexts in which the item can be used. Possible values include `tea`, `spell`, `portal`, `gift`, and `quest`.
- **`stock_behavior`** (string, required): Specifies inventory depletion rules. Possible values include `finite`, `infinite`, and `key_item`.
- **`starting_quantity`** (integer, optional): The quantity present at the start of the game. Defaults to `0`.
- **`max_stack`** (integer or null, optional): The maximum stack size for finite items. Defaults to `null` (uncapped).

---

### common.schema.json

The `common.schema.json` file defines shared definitions used across other schemas.

#### Definitions

- **`id`** (string): A unique identifier pattern. Must match the regex `^[a-z0-9_]+$`.
- **`nonempty_string`** (string): A string with a minimum length of 1.
- **`effects`** (object): Describes the effects of an action or event. Contains the following fields:
  - **`add_items`** (object, optional): Items to add to the inventory. The keys are item IDs, and the values are integers representing quantities (minimum 1).
  - **`remove_items`** (object, optional): Items to remove from the inventory. The keys are item IDs, and the values are integers representing quantities (minimum 1).
  - **`set_flags`** (array, optional): Flags to set (add to the player flags array). Each item is a non-empty string.
  - **`clear_flags`** (array, optional): Flags to clear (remove from the player flags array). Each item is a non-empty string.
  - **`move_to`** (string or null, optional): The place to move the player to. Can be a valid ID or `null`.

---

### conditions.schema.json

The `conditions.schema.json` file defines the structure for conditions that must be met for certain actions or events.

#### Collection object
- **`Conditions`** (array, required): A list of collectible item objects.
  - **Items**: Each item in the array is a `Condition Object`Collection object.

#### Condition object
- **`location`** (string, optional): The ID of the location. Referenced from `common.schema.json`.
- **`zone`** (string, optional): The ID of the zone. Referenced from `common.schema.json`.
- **`zone_not`** (string, optional): The ID of the zone that must not be active. Referenced from `common.schema.json`.
- **`flags_set`** (array, optional): A list of flags that must be set. Defaults to an empty array.
  - **Items**: Each item is a non-empty string.
- **`flags_not_set`** (array, optional): A list of flags that must not be set. Defaults to an empty array.
  - **Items**: Each item is a non-empty string.
- **`inventory_min`** (object, optional): Specifies the minimum inventory requirements. Defaults to an empty object.
  - **Properties**: Keys are item IDs, and values are integers (minimum 0).
- **`visit_count_min`** (object, optional): Specifies the minimum visit counts. Defaults to an empty object.
  - **Properties**: Keys are location IDs, and values are integers (minimum 0).
- **`seen_interactions_min`** (object, optional): Specifies the minimum number of interactions seen. Defaults to an empty object.
  - **Properties**: Keys are interaction IDs, and values are integers (minimum 0).
- **`time_of_day`** (array, optional): Specifies the time of day. Defaults to an empty array.
  - **Items**: Each item is a non-empty string.
- **`day_min`** (integer, optional): The minimum day number. Defaults to `0`.
- **`day_max`** (integer, optional): The maximum day number. Defaults to `0`.

---

### interactions.schema.json

The `interactions.schema.json` file defines the structure for interactions that a player can have with NPCs.

#### Collection object
- **`interactions`** (array, required): A list of interaction objects.
  - **Items**: Each item in the array is an `Interaction object`Collection object.

#### Interaction Object
- **`interaction_id`** (string, required): A unique identifier for the interaction. Referenced from `common.schema.json`.
- **`npc_kind`** (string, required): The kind of NPC. Possible values include `human` and `animal`.
- **`interaction_type`** (string, required): The type of interaction. Possible values include `ambient_ack`, `micro_offer`, `ritual`, `light_request`, and `threshold_adjacent`.
- **`capability`** (string or null, optional): The capability associated with the interaction. Possible values include `shop`, `trade`, `gift`, `quest_giver`, `companion`, `messenger`, `hint`, or `null` (default).
- **`text`** (object, required): Describes the text associated with the interaction. Contains the following fields:
  - **`primary`** (string, required): The primary text. Referenced from `common.schema.json`.
  - **`secondary`** (string or null, optional): The secondary text. Defaults to `null`.
  - **`kind`** (string, optional): The kind of text. Possible values include `spoken` and `observed`. Defaults to `spoken`.
- **`conditions`** (object, optional): Specifies the conditions for the interaction. Contains fields such as `npc_id`, `place_id`, `zone_id`, `time_of_day`, `weather`, `season`, and more.
- **`selection`** (object, required): Specifies the selection criteria for the interaction. Contains fields such as `weight`, `variant_group_id`, and `priority`.
- **`effects`** (object or null, optional): Describes the effects of the interaction. Defaults to `null`.
- **`tags`** (array or null, optional): A list of tags associated with the interaction. Defaults to `null`.

---

### lexicons.schema.json

The `lexicons.schema.json` file defines the structure for lexicons used in the game.

#### Collection object
- **`lexicon`** (array, required): A list of lexicon entries.
  - **Items**: Each item in the array is a `Lexicon Object`.

#### Lexicon object
- **`lexicon_type`** (string, required): The type of lexicon. Possible values include `global` and `location`.
- **`key`** (string, required): A unique key for the lexicon entry.
- **`scope`** (string, required): The scope of the lexicon entry. Possible values include `global`, `zone`, and `location`.
- **`words`** (array, optional): A list of words associated with the lexicon entry. Defaults to an empty array.
- **`extends`** (string or null, optional): Specifies another lexicon entry that this entry extends. Defaults to `null`.

---

### npcs.schema.json

The `npcs.schema.json` file defines the structure for NPCs in the game.

#### Collection object
- **`npcs`** (array, required): A list of NPC objects.
  - **Items**: Each item in the array is an `NPC Object`.

#### NPC object
- **`npc_id`** (string, required): A unique identifier for the NPC.
- **`display_name`** (string, required): The name of the NPC.
- **`npc_kind`** (string, required): The kind of NPC. Possible values include `human` and `animal`.
- **`home_location_id`** (string, required): The ID of the NPC's home location.
- **`spawn_rules`** (object, required): Specifies the spawn rules for the NPC. Contains fields such as `presence` (required) and `frequency` (optional).
- **`interactions`** (array, optional): A list of interactions associated with the NPC. Defaults to an empty array.
- **`species`** (string, required when `npc_kind` == `animal`): The species of the NPC.

---

### places.schema.json

The `places.schema.json` file defines the structure for places in the game.

#### Collection object
- **`zones`** (array, required): A list of zone objects.
  - **Items**: Each item in the array is a `Zone Object`.
- **`places`** (array, required): A list of place objects.
  - **Items**: Each item in the array is a `Place Object`.

#### Zone object
- **`zone_id`** (string, required): A unique identifier for the zone.
- **`display_name`** (string, required): The name of the zone.
- **`mood`** (string, required): The mood associated with the zone.

#### Place object
- **`place_id`** (string, required): A unique identifier for the place.
- **`display_name`** (string, required): The name of the place.
- **`zone_id`** (string, required): The ID of the zone the place belongs to.
- **`mood`** (string, required): The mood associated with the place.
- **`profile`** (object, required): Describes the profile of the place. Contains fields such as `meaning`, `sensory_focus`, `social_level`, `time_sensitivity`, `weather_sensitivity`, `emotional_range`, and `player_need_satisfied`.

---

### players.schema.json

The `players.schema.json` file defines the structure for player data in the game.

#### Collection object
- **`runtime/player`** (object, optional): Represents the player data at runtime.

#### Player object
- **`premise`** (object, optional): Describes the premise of the player. Contains fields such as `facets` (required when `premise` is present).
- **`facets`** (array, required when `premise` is present): A list of facets associated with the player.
- **`inventory`** (array, optional): A list of items in the player's inventory. Defaults to an empty array.
- **`stats`** (object, optional): Describes the player's stats. Contains fields such as `health`, `mana`, and `experience`.
- **`progress`** (object, optional): Tracks the player's progress. Contains fields such as `quests_completed` and `achievements`.

---

### scene.schema.json

The `scene.schema.json` file defines the structure for scenes in the game. Below is a detailed description of the fields in this schema:

#### Collection object
- **`scene`** (object, required): Represents a specific scene in the game.

#### Scene object
- **`scene_id`** (string, required): A unique identifier for the scene.
- **`place_id`** (string, required): The ID of the place where the scene occurs.
- **`entry_node`** (string, required): The ID of the entry node for the scene.
- **`nodes`** (array, required): A list of nodes in the scene.
  - **Items**: Each item in the array is a `Node Object`.

#### Node object
- **`node_id`** (string, required): A unique identifier for the node.
- **`action_ref`** (string, optional): A reference to an action associated with the node.
- **`choices`** (array, optional): A list of choices available at the node. Defaults to an empty array.

---

### scenes_manifest.schema.json

The `scenes_manifest.schema.json` file defines the structure for the scenes manifest in the game. Below is a detailed description of the fields in this schema:

#### Collection object
- **`scenes`** (array, required): A list of scene entries.
  - **Items**: Each item in the array is a `Scene Manifest Entry`.

#### Scene Manifest Entry
- **`scene_id`** (string, required): A unique identifier for the scene.
- **`title`** (string, required): The title of the scene.
- **`description`** (string, optional): A brief description of the scene. Defaults to an empty string.
- **`tags`** (array, optional): A list of tags associated with the scene. Defaults to an empty array.

---

### sessions.schema.json

The `sessions.schema.json` file defines the structure for runtime sessions in the game. Below is a detailed description of the fields in this schema:

#### Collection object
- **`runtime/session`** (object, required): Represents the session data at runtime.

#### Session object
- **`session_id`** (string, required): A unique identifier for the session.
- **`state`** (object, required): Represents the game state during the session.
  - **`current_location`** (string, required): The ID of the current location.
- **`created_at`** (string, required): The timestamp when the session was created.

---

### spells.schema.json

The `spells.schema.json` file defines the structure for spells in the game. Below is a detailed description of the fields in this schema:

#### Collection object
- **`spell_recipes`** (array, required): A list of spell recipe objects.
  - **Items**: Each item in the array is a `Spell Recipe Object`.

#### Spell Recipe Object
- **`spell_id`** (string, required): A unique identifier for the spell.
- **`display_name`** (string, required): The name of the spell.
- **`incantation_style`** (string, required): The style of the incantation.
- **`incantation`** (string, required): The incantation text.
- **`narrative_purpose`** (string, required): The narrative purpose of the spell.
- **`target_need`** (string, required): The player need targeted by the spell.
- **`place_affinity`** (string, required): The place affinity of the spell.
- **`ingredients`** (array, required): A list of ingredients required for the spell.
- **`ritual_steps`** (array, required): A list of steps in the spell ritual.
- **`tone`** (string, required): The tone of the spell.
- **`repeatable`** (boolean, required): Indicates whether the spell is repeatable.
- **`output`** (object, required): Describes the output of the spell.

---

### teas.schema.json

The `teas.schema.json` file defines the structure for teas in the game. Below is a detailed description of the fields in this schema:

#### Collection object
- **`tea_recipes`** (array, required): A list of tea recipe objects.
  - **Items**: Each item in the array is a `Tea Recipe Object`.

#### Tea Recipe Object
- **`recipe_id`** (string, required): A unique identifier for the tea recipe.
- **`display_name`** (string, required): The name of the tea recipe.
- **`intent`** (string, required): The intent of the tea recipe.
- **`target_need`** (string, required): The player need targeted by the tea.
- **`allowed_times`** (array, required): A list of times when the tea can be consumed.
- **`base_liquid`** (string, required): The base liquid for the tea.
- **`ingredients`** (array, required): A list of ingredients required for the tea.
- **`steps`** (array, required): A list of steps to prepare the tea.
- **`serves`** (integer, required): The number of servings the recipe makes.
- **`repeatable`** (boolean, required): Indicates whether the tea recipe is repeatable.

