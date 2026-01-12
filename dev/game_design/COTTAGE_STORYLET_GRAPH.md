# Cottage scene graph (first wake)

## Node: `cottage_wake`
- **Prompt**: waking text
- **Choices**:
  - `rest_longer`
  - `look_around`

## Node: `rest_longer`
- **Prompt/Result**: lingering/rest text
- **Choices**:
  - `look_around`

## Node: `look_around`
- **Prompt/Result**: cottage overview
- **Effects**:
  - add items: `bag`, `water_bottle`, `water`, `mirror`
- **Choices**:
  - `make_tea` (if not already done)
  - `pick_up_journal` (if not already done)
  - `head_to_town`

## Node: `make_tea`
- **Prompt/Result**: tea ritual text (and recipe rendering)
- **Effects**:
  - add items: `chamomile_flower`, `black_tea`, `biscuits`
  - set flag: `made_tea`
- **Choices**:
  - `look_around`
  - `head_to_town`

## Node: `pick_up_journal`
- **Prompt/Result**: journal description
- **Effects**:
  - add item: `journal`
  - set flag: `journal_available`
- **Choices**:
  - `make_tea` (if not already done)
  - `head_to_town`

## Node: `head_to_town`
- **Prompt/Result**: leaving text
- **Effects** (catch‑all, no penalty):
  - add items: `journal`, `bag`, `water_bottle`, `water`, `mirror`, `chamomile_flower`, `black_tea`, `biscuits`
  - set flag: `left_cottage_once`

## Gating / Eligibility (engine)
- `make_tea`: eligible when `made_tea` flag is not set.
- `pick_up_journal`: eligible when `journal_available` flag is not set.
- `head_to_town`: always eligible; adds missing items idempotently.
