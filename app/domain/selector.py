# TODO:

# 2.4 Implement storylet candidate selection (generated + authored)

# File: `app/domain/selector.py`

# - Add a function `generate_candidates(state, repo, seed, n=3)`.
# - Add a function `merge_with_authored(candidates, authored)`.
# - Add selection:
#   - deterministic selection by seed
#   - prefer authored anchors if explicitly “pinned” (optional later)

# ### 4.3 Implement storylet selector

# File: `app/domain/selector.py`

# - eligible_storylets(state, repo) -> list[Storylet]
# - choose_storylet(storylets, seed) -> Storylet