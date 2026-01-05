# TODO:
# ### 1.4 Cross-file integrity checks

# File: `app/content/validators.py`

# Validate at load time:

# - every place_id reference exists
# - every npc_id reference exists
# - collectible origin_ref points to a real place (when origin_scope indicates place)
# - interactions dependencies reference real npc/place/time tokens
# - tea/spell ingredient_ref resolves to:
#   - a collectible_id OR
#   - an any: substitution token (allowed)
# - lexicon scope:
#   - Global OR place_id that exists

# ### Acceptance criteria

# - Running a single command loads everything and prints “OK”
# - Any missing place_id/npc_id/item_id fails fast with a clear message
# - Unit tests exist for loader + validators