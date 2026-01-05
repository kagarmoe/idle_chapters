One player, one notebook, many locations, many items in inventory.

The player notebook has 2 kinds of recipies: spells and tea/food.
Spells create some kind of event (like use the portal to return home)
Drining tea, having a meal, and taking a nap all help a player restore their energy.
Not that a player's energy ever gets too low, but the game is basically about
feeling better.
Players can also leave notes (when the action is available), or write in their journals
(respond to cozy, feel-good prompts?)
Players need to visit locations to cast spells.
Once a player uses a location in a spell, then they need to re-visit that location before using it in another spell. (locations.show (list all possible locations); locations.visited; locations.available; locations.used) (really need a better word for "you need to revisit this location before you can use it in a spell again)

## Players

player.id (session)
player.inventory (chamomile, bergamot, kettle, etc)
player.time (one of
[early-morning, mid-morning, noon, early-afternoon, mid-afternoon, evening, night])
player.mood
player.action
player.energy

### Energy

A player's always has some energy, it rarely blocks activity.
It exists mostly for narrative color, to influence available storylets, and encourage naps and snacks.

### Time

Is one of: early-morning, mid-morning, noon, early-afternoon, mid-afternoon, evening, night
Time advances by action, not by a clock. So getting out of bed starts the day, but the day doesn't advance until you leave the house. There's no bed-rotting in idle_chapters.
Some actions take less time, like `going to the store`.
Some actions take more time, like `walking to the meadow`.
Some actions take no time, like `pet the cat` or `watch the cows`
Taking a nap can take either less or more time. That's a random event.
Snacks and meals take less time.

## Notebook

The notebook contains ways of acting in the world.
It is a special type of item.
Your notebook cannot be lost or given away.
The notebook starts with a few spells and recipes

notebook.tea("chamomile")
notebook.spell("portal")
notebook.snack("charcuterie")
notebook.meal("dinner[potpie]")
notebook.inventory
notebook.journal

### Spells

Spells are listed in the notebook.

Spells are a kind of enhanced action with explicit constraints.

Spells have prerequisites:
`spell.portal[location[forest.waterfall], items[mirror,crystal]]`

Spells produce:

- a narrative
- a state change
- maybe a location change

spell.portal(requires that the player is at the top of the forest waterfall and has a mirror and a crystal)
spell.description
spell.items

### Tea

Tea recipies are listed in the notebook.
Teas are a kind of enhanced action with explicit constraints.

Tea takes ingredients and produces:
- a narrative
- a state change

### Inventory

The inventory is a magic bag without limit.
You start with a few things in your inventory.
To make tea or cast a spell, you must have the reqired items.
Making the tea or spell automatically removes the ingredients from your inventory.

inventory.list
inventory.add
inventory.use

### Items

item.notebook
item.chamomile
item.mirror
item...

## Actions

can_pickup: returns items that the player can pick up in a location. maybe "seek?"
cast_spell
go_home
list_actions: returns possible actions for player in location
make_tea
meal
nap
pet (cat/dog/bunny/etc)
pickup[item]
  - can_pickup: returns items that the player can pick up in a location. maybe "seek?"
shop
snack
talk
wander
write (in notebook, or leave a note at home, at a store, some other location)

### cast_spell

Requirements: a spell and ingredients.
Produces a story, change of state, and possibly a change of location

### float

Requirements: Must be in water
Produces: A narrative an maybe a change of state

### go_home

Requirements: None
Produces: A narrative and a change of location to "home"

### list_actions: returns possible actions for player in location

### make_tea

Requirements: Ingredients
Produces: A narrative and a change of inventory state and player energy

### meal

Requirements: Ingredients
Produces: A narrative and a change of inventory state and player energy

### nap

Requirements: Location (you can't nap in a store or in the water, for example.)
Produces: A narrative and a change of inventory state and player energy

### pet (cat/dog/bunny/etc)

Requirements: Specific NPC in narrative
Produces: A narrative

### pickup[item]

Requirements: Must be in a location with avaliable items
Produces: A narrative adds item to inventory

### shop

Requirements: Must be in a location with avaliable items
Produces: A narrative adds item to inventory, spends money

### snack

Requirements: Location, inventory
Produces: A narrative and a change of inventory state and increases player energy

### talk

Requirements: Location, NPC
Produces: A narrative

### wander

Is wandering the same as walking to a specific location?

Requirements: Energy
Produces: A narrative and change of location.

### write

Writing is one way of interacting in the world.
You can write in the notebook, leave notes in locations, and respond to cozy prompts.
This is player-authored content, tied to state and location, and observable

Requirements: Writing implement (you have a pencil and paper by default)
Produces: ???
  Leaving a note could cause an action later on in the game.
  Journaling adds energy.

Need: journaling endpoints.

## Storylets

story.id
story.location
story.ambiance
story.narrative

### Locations

Locations are context, not collectibles.
Players discover locations
Locations become available as context for a spell
Using a location in spell spends its immediacy
You will have to re-visit a location to use it again in a different spell.

## NPCs

Shop owner
Friend
Cat
Dog
Bunny
