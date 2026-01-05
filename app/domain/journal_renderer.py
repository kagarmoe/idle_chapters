# TODO:

#     ### 3.2 Implement journal renderer

# File: `app/domain/journal_renderer.py`

# Inputs:

# - place_id
# - entry_type
# - storylet (selected)
# - state snapshot (inventory/flags as needed)
# - ingredient picks (optional, based on storylet tags)

# Outputs:

# - JournalPage object:
#   - frontmatter fields aligned with journal_page.schema
#   - markdown body assembled from template + storylet context

# ### Acceptance criteria

# - engine can produce a JournalPage for at least one storylet
# - locality works:
#   - same_place used when available
#   - same_zone used only when same_place insufficient
#   - no silent widening beyond any_place unless explicitly configured
# - journal output validates against journal_page.schema (frontmatter object)
