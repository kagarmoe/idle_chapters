# TODO:
#     ### 3.0 Define JournalPage as the step output

# File: `app/domain/step_result.py`

# - Define `StepResult` to include:
#   - `journal_page` (frontmatter dict + markdown body)
#   - `choices` (exactly 3)
#   - `debug` (seed, selected_storylet_id, eligible_count)

# This keeps the API/CLI thin: they render the returned journal page.