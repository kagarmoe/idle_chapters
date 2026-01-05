# ### 5.2 Stores

# File: `app/persistence/state_store.py`

# - get_state(session_id)
# - upsert_state(session_id, state)

# ### Collections

# - `sessions`
# - `state_snapshots`
# - `journal_pages`
# - (optional) `events`
# - (optional) `content_versions` (pins a session to a content manifest hash/version)

# ### Acceptance criteria

# - create session -> state persists
# - step -> journal page appended
# - reload -> state + pages match
# - session data is portable across app restarts without reloading any content into Mongo
# - (optional) a session can record the content manifest hash used to generate its pages
