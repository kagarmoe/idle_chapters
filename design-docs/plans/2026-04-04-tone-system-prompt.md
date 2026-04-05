# Tone System Prompt Layer — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make the tone contract the single source of truth for all generation prompts, eliminating duplicated tone rules and ensuring full coverage.

**Architecture:** Create a `tone_system_prompt.md` that reformats the full tone contract for LLM system-message use. Strip duplicated tone rules from each generation prompt. Add a sync test to prevent drift between the contract and the system prompt.

**Tech Stack:** Markdown, pytest

---

### Task 1: Create `prompts_ai/tone_system_prompt.md`

**Files:**
- Create: `prompts_ai/tone_system_prompt.md`

**Step 1: Write the tone system prompt**

This file reformats `design-docs/game_design/tone_contract.md` into a directive system message. It must cover all 11 sections of the contract. Structure:

```markdown
# System: Tone Contract

You are generating content for a cozy game. This tone contract governs all output. It overrides any conflicting instructions in the user prompt.

## Purpose

This game provides emotional safety, gentle curiosity, and restorative presence. The player is never tested, judged, rushed, or placed at risk. Restoration over progression.

## Core Promise

- The player is allowed to be where they are.
- Nothing bad will happen because they waited, looked, or chose slowly.
- There is no "right" way to experience a place.
- Small moments are sufficient.

The game does not require completion, mastery, or optimization.

## Never Ask of the Player

Do not generate content involving:

- Urgency or speed
- Optimization, evaluation, or comparison
- Fear, threat, or vigilance
- Social performance or embarrassment
- Resource anxiety or scarcity management
- Irreversible loss
- Moral judgment or correctness

The player is never behind, at fault, or at risk.

## Place Design

Each place satisfies one gentle human need (`player_need_satisfied`). Places offer emotional states, not outcomes. They do not escalate, resolve conflicts, or unlock consequences. A place is complete the moment the player enters it.

## Hard Constraints (globally disallowed)

### Threat & Danger
No threat, danger, peril, violence, injury, or menacing animals/environments.

### Urgency & Pressure
No deadlines, rushing, time pressure. No "must," "urgent," or failure framing.

### Scarcity & Loss
No shortage, depletion, "last chance." No irreversible loss or destruction.

### Social Tension
No judgment, scrutiny, embarrassment. No authority, enforcement, punishment.

### Harsh Sensory Language
No screeching, crashing, sharpness. No extreme weather or bodily discomfort.

If language violates these constraints, omit it. Do not replace with contrast or drama.

## Soft Constraints

Tone is enforced through lexicon weighting, not scripting:

- Language is biased probabilistically, not dictated.
- Word choice subtly aligns with `player_need_satisfied`.
- Emotional drift is corrected gently over time.

Prioritize consistency of feeling over textual novelty.

## Allowed Emotional Range

Allowed: calm, curiosity, nostalgia, quiet reflection, gentle melancholy.

Not allowed: despair, anxiety about the future, regret framed as error, grief requiring resolution.

## Melancholy Rules

### Allowed ("Settled")
Melancholy is permitted when it is past-facing (not future-facing), accepting (not yearning), quiet (not sharp), and observational (not participatory). Examples: wear, fading, distance, time having passed. Melancholy must settle, not pull.

### Disallowed ("Pulling")
No regret framed as mistake. No longing framed as loss. No sadness implying action is required. No "if only," "too late," or "missed chance" language.

If an emotion asks the player to act, fix, or resolve — it breaks the tone contract.

## Player Trust

The world is emotionally safe. The system never surprises the player with threat or obligation. Variation reinforces familiarity, not disruption. The player should learn: nothing bad will happen if they stay.

## Validation

Before returning output, confirm:

1. Is the player emotionally safe?
2. Is nothing required of them?
3. Does the moment feel complete as-is?

If any answer is no, revise. Remove or soften violating language. Do not add contrast or drama. Preserve calm and presence.

## Authority

This contract overrides individual prose choices, local narrative flavor, and isolated generation outputs. All output must conform.
```

**Step 2: Commit**

```bash
git add prompts_ai/tone_system_prompt.md
git commit -m "feat(prompts): add tone system prompt derived from tone contract"
```

---

### Task 2: Strip duplicated tone rules from generation prompts

**Files:**
- Modify: `prompts_ai/base_generation_prompt.md`
- Modify: `prompts_ai/melancholy_safe_prompt.md`
- Modify: `prompts_ai/minimal_moment_prompt.md`
- Modify: `prompts_ai/moment_generation_prompt.md`
- Modify: `prompts_ai/place_generation_prompt.md`
- Modify: `prompts_ai/incantation_prompt.md`

Each prompt gets:
- A header line: `<!-- Requires tone_system_prompt.md as system message -->`
- All tone-rule content removed (constraints, emotional safety, disallowed lists)
- Only task-specific instructions retained (what to generate, template vars, format, examples)

**Step 1: Edit `base_generation_prompt.md`**

Replace entire file with:

```markdown
<!-- Requires tone_system_prompt.md as system message -->

Generate a short descriptive passage for the game.

- Use gentle, concrete sensory details.
- Prefer observation over action.
- If uncertain, omit rather than dramatize.

Write 2-4 sentences.
```

**Step 2: Edit `melancholy_safe_prompt.md`**

Replace entire file with:

```markdown
<!-- Requires tone_system_prompt.md as system message -->

# Melancholy-Safe Prompt Template

Use this only when a place allows melancholy. The tone system prompt defines which forms of melancholy are allowed ("settled") and disallowed ("pulling"). This prompt enables the settled form.

```text
This passage may include gentle melancholy.
Use language that feels accepting and complete.
```

## Example: meadow_shrine

```text
This passage may include gentle melancholy.
Use language that feels accepting and complete.
```
```

**Step 3: Edit `minimal_moment_prompt.md`**

Replace entire file with:

```markdown
<!-- Requires tone_system_prompt.md as system message -->

Generate a cozy, observational moment for {{Place_Display_Name}}.
Fulfill this need: {{Player_Need_Satisfied}}.
```

**Step 4: Edit `moment_generation_prompt.md`**

Replace entire file with:

````markdown
<!-- Requires tone_system_prompt.md as system message -->

# Moment scenes

Keeps moments from turning into micro-stories.

```text
Moment type: {{Moment_Description}}
Location: {{Place_Display_Name}}

Constraints:

- This moment does not advance a plot.
- It does not resolve or introduce conflict.
- It does not require a response.

Focus on:

- One sensory impression
- One emotional shift within the allowed range

End the passage without implying continuation.
```

## Example — bakery pause

```text
Moment type: A quiet moment of arrival
Location: Bakery

Focus on:
- Warmth and familiarity
- The comfort of being unhurried
```
````

**Step 5: Edit `place_generation_prompt.md`**

Replace entire file with:

```markdown
<!-- Requires tone_system_prompt.md as system message -->

Location: {{Place_Display_Name}}

This place exists to satisfy the following player need:
{{Player_Need_Satisfied}}

Emotional range:
{{Emotional_Range}}

Guidance:

- Let the language gently support the player need.
- Favor sensory details aligned with this place.
- The player may pause, notice, or simply be present.
- Do not introduce goals or change.

Write a calm, observational passage that fulfills this purpose.

## Example: beach_tidepool

Location: Tide Pools

This place exists to satisfy the following player need:
Permission to notice small wonders

Emotional range:
Curiosity -> Peace

Guidance:
- Favor small-scale, close-up details.
- Emphasize stillness and quiet presence.

Write a calm, observational passage.
```

**Step 6: Edit `incantation_prompt.md`**

Replace entire file with:

```markdown
<!-- Requires tone_system_prompt.md as system message -->

Incantation generation guidance (rhymed couplet default):
- Write 2-6 lines as rhyming couplets (AABB...).
- Keep an accentual feel (about 4 strong beats per line); syllable count may vary slightly.
- Allow the final line of each couplet to vary in length or cadence (extra syllable or clipped ending) for comic timing.
- Tone should match the spell's `tone` and `narrative_purpose`.
- MUST pass lexicon validation: avoid any disallowed terms from the project's not_allowed_lexicon.
```

**Step 7: Commit**

```bash
git add prompts_ai/base_generation_prompt.md prompts_ai/melancholy_safe_prompt.md prompts_ai/minimal_moment_prompt.md prompts_ai/moment_generation_prompt.md prompts_ai/place_generation_prompt.md prompts_ai/incantation_prompt.md
git commit -m "refactor(prompts): strip duplicated tone rules, defer to tone system prompt"
```

---

### Task 3: Replace `self_check_prompt.md` with full validation prompt

**Files:**
- Modify: `prompts_ai/self_check_prompt.md`

**Step 1: Replace `self_check_prompt.md`**

```markdown
<!-- Requires tone_system_prompt.md as system message -->

# Tone Validation Prompt

Review the following passage against the tone contract provided in the system message.

Check each category and report violations:

1. **Safety:** Is the player emotionally safe?
2. **Agency:** Is nothing required of them?
3. **Completeness:** Does the moment feel complete as-is?
4. **Hard constraints:** Any threat, urgency, scarcity, social tension, or harsh sensory language?
5. **Emotional range:** Only calm, curiosity, nostalgia, quiet reflection, or settled melancholy?
6. **Melancholy:** If present, is it settled (not pulling)?

For each violation found:
- Quote the offending text.
- Name the contract section it violates.
- Suggest a revision that preserves calm and presence.

If no violations, return: "Tone contract upheld."
```

**Step 2: Commit**

```bash
git add prompts_ai/self_check_prompt.md
git commit -m "refactor(prompts): replace self-check with full tone validation prompt"
```

---

### Task 4: Write the sync test

**Files:**
- Create: `tests/test_tone_prompt_coverage.py`

**Step 1: Write the test**

```python
"""Verify tone_system_prompt.md covers all sections of the tone contract."""

from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
TONE_CONTRACT = REPO / "design-docs" / "game_design" / "tone_contract.md"
TONE_SYSTEM_PROMPT = REPO / "prompts_ai" / "tone_system_prompt.md"


def _extract_headings(text: str) -> set[str]:
    """Return normalised ## headings from markdown text."""
    headings = set()
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("## "):
            # Normalise: lowercase, strip numbering like "## 5. Foo" -> "foo"
            heading = stripped.removeprefix("## ").strip()
            # Remove leading "N. " numbering
            parts = heading.split(". ", 1)
            if len(parts) == 2 and parts[0].strip().isdigit():
                heading = parts[1]
            headings.add(heading.lower())
    return headings


def test_system_prompt_covers_all_contract_sections():
    contract = TONE_CONTRACT.read_text()
    system_prompt = TONE_SYSTEM_PROMPT.read_text()

    contract_headings = _extract_headings(contract)
    prompt_text_lower = system_prompt.lower()

    missing = []
    for heading in sorted(contract_headings):
        if heading not in prompt_text_lower:
            missing.append(heading)

    assert not missing, (
        f"tone_system_prompt.md is missing coverage for contract sections: {missing}"
    )


def test_all_prompts_require_tone_system():
    """Every generation prompt must declare dependency on tone_system_prompt."""
    prompts_dir = REPO / "prompts_ai"
    header = "tone_system_prompt.md"

    for prompt_file in sorted(prompts_dir.glob("*.md")):
        if prompt_file.name == "tone_system_prompt.md":
            continue
        content = prompt_file.read_text()
        assert header in content, (
            f"{prompt_file.name} does not reference {header}"
        )
```

**Step 2: Run the tests**

```bash
pytest tests/test_tone_prompt_coverage.py -v
```

Expected: both tests PASS.

**Step 3: Commit**

```bash
git add tests/test_tone_prompt_coverage.py
git commit -m "test(prompts): add tone contract coverage and prompt dependency tests"
```

---

### Task 5: Update CLAUDE.md tone contract path

**Files:**
- Modify: `CLAUDE.md`

**Step 1: Update the path**

Change `dev/game_design/tone_contract.md` to `design-docs/game_design/tone_contract.md` (two occurrences).

**Step 2: Commit**

```bash
git add CLAUDE.md
git commit -m "fix(config): update tone contract path in CLAUDE.md"
```

---

Plan saved. Two execution options:

**1. Subagent-Driven (this session)** — I dispatch a fresh agent per task, review between tasks, fast iteration.

**2. Parallel Session (separate)** — Open a new session with executing-plans, batch execution with checkpoints.

Which approach?