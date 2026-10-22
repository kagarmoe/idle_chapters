# Cottage scene graphs

Two authored scenes live at `cottage_home`. A scene opens when its entry node's
action passes its `when` (the scene schema has no `when` of its own), and the two
entry actions gate on opposite sides of `left_cottage_first`, so exactly one is
open at a time.

After every step the engine also offers each eligible path (an action with
`effects.move_to`) after the scene's own choices, so a way out of the cottage is
always on offer.

## First morning: `cottage_wake_v1`

Opens while `left_cottage_first` is not set.

| Node | Choices |
|---|---|
| `cottage_wake` (entry) | `rest_longer`, `look_around`, `make_tea`, `pick_up_journal` |
| `rest_longer` | `look_around`, `make_tea`, `pick_up_journal` |
| `look_around` | `make_tea`, `pick_up_journal`, `head_to_town` |
| `make_tea` | `look_around`, `pick_up_journal`, `head_to_town` |
| `pick_up_journal` | `look_around`, `make_tea`, `head_to_town` |
| `head_to_town` | (none; it is a path to `town`) |

## Coming home: `cottage_home_return_v1`

Opens once `left_cottage_first` is set.

| Node | Choices |
|---|---|
| `settle_in` (entry) | `sit_by_the_fire`, `look_around`, `make_tea`, `pick_up_journal` |
| each of those four | the other three |

Arriving by a path writes one journal page that tells the walk and then the
`settle_in` text (ic-23), so no extra enter is needed to see it.

## Once-only actions

Each starting item comes from exactly one action, once:

- `look_around`: `bag`, `water_bottle`, `water`, `mirror`; sets `looked_around`.
- `make_tea`: `chamomile_flowers`, `black_tea`, `biscuits`; sets `made_tea`.
- `pick_up_journal`: `journal`; sets `journal_available`.
- `head_to_town`: no items; moves to `town` and sets `left_cottage_first`. After that, `walk_to_town` is the way into town.

A choice whose flag is already set is not offered, so leaving early never closes
anything off: the cottage offers what is left whenever you come home.
