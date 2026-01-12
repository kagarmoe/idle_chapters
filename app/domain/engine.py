# TODO:

#     ### 4.4 Implement Engine.step

# File: `app/domain/engine.py`

# Flow:

# 1) select eligible scene(s) for current place
# 2) if command is “enter” or “continue,” return scene choices without applying effects
# 3) if command is “choose option,” apply chosen effects
# 4) render JournalPage
# 5) return StepResult:
#    - journal_page
#    - choices (next)
#    - debug info

# ### Acceptance criteria

# - step loop works end-to-end with deterministic seed
# - applying a choice changes inventory/flags
# - journal page reflects the step
