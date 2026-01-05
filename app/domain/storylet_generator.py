# TODO:

#     ### 2.3 Implement procedural storylet generator (core v1 feature)

# File: `app/domain/storylet_generator.py`

# Responsibilities:

# - Inputs:
#   - `state` (place_id, inventory, flags, time_tick)
#   - `repo` (places/npcs/items/recipes/interactions/templates/lexicons)
#   - `seed` (optional)

# - Output:
#   - one valid Storylet (or N candidates)

# Implementation steps:

# 1) **Pick an entry_type**
#    - Start rule: default to `tea` unless a place has a “threshold” tag for `spell`.
#    - Later: weight by time_tick or recent history.

# 2) **Pick a template family** (not the journal template; a storylet “shape”)
#    - Example families: `arrival`, `small_find`, `offer_help`, `quiet_notice`, `threshold_call`.

# 3) **Construct a prompt/title seed**
#    - Use descriptive lexicon for sensory anchors; avoid not_allowed lexicon.
#    - Keep the prompt short; journal templates can expand it.

# 4) **Construct 3 choices**
#    - Each choice has:
#      - `choice_id` ("1","2","3")
#      - `label` (short text)
#      - `effects` (small reducers)
#    - Keep effects conservative in v1:
#      - add/remove 0–2 items
#      - set/clear at most 1 flag
#      - optional move location (rare)

# 5) **Attach journal hints**
#    - `need_hint`, `mood_hint`, `tags` consistent with entry_type.

# 6) **Attach debug metadata**
#    - seed used
#    - family/template id
#    - key constraint decisions (e.g., “spell disallowed: not a threshold place”)

# 7) **Validate**
#    - Validate the generated object against `storylet.schema.yaml`.
#    - If invalid, fail fast with readable error (this is portfolio-grade).