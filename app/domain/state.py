# TODO:

#     ### 4.1 Define core state model

# File: `app/domain/state.py`

# - PlayerState (Pydantic or dataclass):
#   - session_id
#   - current_place_id
#   - inventory: {item_id: qty}
#   - flags: set[str]
#   - time_tick (optional)