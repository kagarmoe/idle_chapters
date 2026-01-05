# TODO
#
# ### 1.3 Build ContentRepo + indices

# - `ContentProvider` (file-based in V1; loads YAML from the repo)
# - Later (optional): `MongoContentProvider` (only if we need live editing / multi-pack serving)

# File: `app/content/repo.py`

# **V1 decision:** load all validated *asset content* into memory at process start, then serve lookups from indices.
# MongoDB is reserved for *runtime data* (sessions, state, journal pages), not static world content.

# Why this is the right default for V1:
# - **Simplicity**: no migrations, no content database bootstrapping, no dual-source-of-truth.
# - **Speed**: after startup, content access is pure in-process dict lookup.
# - **Fail-fast validation**: schema + cross-file checks run once at boot and crash loudly if broken.
# - **Git-native workflow**: edit YAML → run tests → commit. No admin UI required.
# - **Determinism & testability**: generator behavior depends on versioned content, not mutable DB rows.

# Tradeoffs and when Mongo-backed content becomes worth it:
# - **Pros of putting content in Mongo**
#   - Live editing via UI (non-dev authoring)
#   - Hot reload without process restart
#   - Serving multiple content packs or per-tenant worlds from a single service
#   - Potentially less startup time for very large content sets (at the cost of runtime queries)
# - **Cons (and why we avoid it in V1)**
#   - Introduces migrations/versioning problems for content
#   - Requires seeding and environment coordination (dev/stage/prod drift)
#   - Adds runtime dependency and query paths for every generation step unless carefully cached
#   - Makes debugging harder (“why did this happen?” can become “which version of content was in DB?”)

# **Design for future flexibility (without paying the cost now):**
# - Keep `ContentProvider` as the abstraction boundary.
# - `ContentRepo` is an in-memory cache + index layer; it should not care where the raw docs came from.
# - If we ever add `MongoContentProvider`, it should still produce the same validated in-memory structures
#   (and ideally the same indices) to keep the engine unchanged.

# #### Indices built by ContentRepo

# Load all validated assets into memory and build indices:

# - places_by_id
# - zones_by_id (if needed)
# - collectibles_by_id
# - npcs_by_id
# - interactions_by_id
# - interactions_by_npc_kind
# - interactions_by_place_id
# - tea_by_id
# - spells_by_id
# - storylets_by_id (placeholder until file exists)
# - storylets_by_place_id (when authored anchors are added)
# - journal_templates_by_entry_type
# - lexicon_by_key

# Implementation notes (practical):
# - Normalize IDs to strings and enforce uniqueness per file (fail fast).
# - Consider storing `source_file`/`source_line` metadata for better validation errors (optional but very helpful).
# - Indices should be plain dicts/DefaultDicts—keep them boring and transparent.

# ### 2.6 Add storylets to ContentRepo (authored anchors)

# File: `app/content/repo.py`

# - Load and index authored storylets if `assets/storylets.yaml` exists.
# - Index by `place_id`.

# ### 3.1 Confirm journal template loading

# File: `app/content/repo.py`

# - load `journal_templates.yaml`
# - index templates by entry_type (and optionally by tags)