# TODO:

# ### 2.2 Implement a Storylet model (internal)

# File: `app/domain/storylet.py`

# - Define a lightweight Storylet type (Pydantic model or dataclass) that matches the schema shape.
# - Include:
#   - `storylet_id: str`
#   - `place_id: str`
#   - `entry_type: str`
#   - `title: str | None` (optional)
#   - `prompt: str | None` (optional)
#   - `tags: list[str]` (optional)
#   - `need_hint: str | None` (optional)
#   - `mood_hint: str | None` (optional)
#   - `conditions: dict` (minimal)
#   - `choices: list[dict]` (exactly 3)
#   - `debug: dict | None` (optional)
