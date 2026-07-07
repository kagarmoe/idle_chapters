# Structured Error Model — CLI (Phase C) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Bead:** `chapters-vxv`
**Design:** `design-docs/plans/2026-04-04-structured-errors-design.md` (§ CLI Projection) and `design-docs/game_design/errors.md` (§ What Phase C will change)

**Goal:** Route CLI error paths through `GameError` so the terminal shows the same tone-contract templates as the API, with Z535 signal words and WHAT/MEANS/DO detail behind a `--verbose` flag.

**Architecture:** `GameError` (in `idle_chapters/services/errors.py`) already computes the player message, signal word, and detail. Phase C adds: a `player_message` property extracted from `project_player()`; a new terminal renderer `idle_chapters/ui/errors.py` (`print_error`, `set_verbose`); an argparse `--verbose` flag in `main.py`; and reroutes six legacy `print()` error sites in `scenes/welcome.py` and `scenes/cottage.py`.

**Tech Stack:** Python (stdlib only — `argparse`, `sys`), pytest with `capsys`/`monkeypatch`, existing `ui/text.py` wrapping helpers.

## Global Constraints

- **Tone contract governs all player-facing text** (`design-docs/game_design/tone_contract.md`). Player-facing error prose comes ONLY from `assets/error_templates.json` — never hardcode error messages in scene code. New non-error recovery copy (Task 5 Step 6) must pass the contract's three-question checklist.
- **No new dependencies.** stdlib `argparse` for the flag; nothing added to `requirements.txt`/`pyproject.toml`.
- **No ANSI colors.** The design doc leaves colors to implementation; we skip them (YAGNI). The signal word text prefix (`CAUTION: …`) is the whole feature. Note this as future work in `errors.md`.
- **Signal words and detail are verbose-only.** Default output stays purely tone-contract. Verbose detail goes to **stderr**; the signal-prefixed message goes to stdout.
- **Tests run in CI automatically.** All new tests live under `tests/` (collected by `pytest.ini` `testpaths = tests`); none are skipped or manual.
- Run tests with `uv run pytest …` (the `.venv` was rebuilt on a new Python and packages may be missing — Task 1 fixes this first).

---

### Task 1: Repair the virtualenv and establish a green baseline

The bd memory `api-default-developer-projection` records that `.venv` switched Python versions and lost its packages. Nothing else can proceed until pytest runs.

**Files:** none created or modified (environment only).

**Interfaces:**
- Consumes: `uv.lock`, `pyproject.toml` at repo root.
- Produces: a working `uv run pytest` for all later tasks.

- [ ] **Step 1: Sync the environment**

```bash
uv sync
```

Expected: uv resolves from `uv.lock` and installs the project + dev deps into `.venv`. If `uv sync` fails because dev deps aren't in the lock, fall back to:

```bash
uv venv && uv pip install -r requirements.txt -e .
```

- [ ] **Step 2: Verify the existing error-model tests pass**

Run: `uv run pytest tests/services tests/domain tests/content -q`
Expected: all PASS, 0 failures. If anything fails here, STOP and report — the baseline is broken and Phase C must not start on a red suite.

- [ ] **Step 3: Nothing to commit** (no files changed).

---

### Task 2: Extract `player_message` property on `GameError`

The player-template rendering currently lives inline in `project_player()` (`idle_chapters/services/errors.py:161-175`). The CLI needs the same rendered message without the RFC 9457 envelope. Extract it as a property; `project_player()` becomes a thin wrapper.

**Files:**
- Modify: `idle_chapters/services/errors.py:161-175`
- Test: `tests/services/test_game_error.py` (append)

**Interfaces:**
- Consumes: existing `GameError.__init__(kind: ErrorKind, effect: Effect, recovery: Recovery, detail: str = "", context: dict | None = None)`, `_load_templates()`.
- Produces: `GameError.player_message -> str` property (rendered tone-contract message: template formatted with `self.context`, falling back to the template's `fallback` on missing keys, or `"Something unexpected happened."` if the kind has no entry). Tasks 3, 5, 6 rely on this exact name.

- [ ] **Step 1: Write the failing tests**

Append to `tests/services/test_game_error.py`:

```python
from idle_chapters.services.errors import Effect, ErrorKind, GameError, Recovery


class TestPlayerMessage:
    def test_renders_template_with_context(self):
        err = GameError(
            kind=ErrorKind.INTENT_NO_MATCH,
            effect=Effect.NONE,
            recovery=Recovery.CORRECTABLE,
            context={"input": "dance", "available_actions": "make tea, sit by the fire"},
        )
        assert err.player_message == (
            'Hmm, I\'m not sure what you mean by "dance". '
            "These are the things you could do here: make tea, sit by the fire."
        )

    def test_missing_context_key_uses_fallback(self):
        err = GameError(
            kind=ErrorKind.INTENT_NO_MATCH,
            effect=Effect.NONE,
            recovery=Recovery.CORRECTABLE,
            context={},
        )
        assert err.player_message == "I didn't quite catch that. What would you like to do?"

    def test_project_player_title_equals_player_message(self):
        err = GameError(
            kind=ErrorKind.SESSION_NOT_FOUND,
            effect=Effect.NONE,
            recovery=Recovery.TERMINAL,
        )
        assert err.project_player()["title"] == err.player_message
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/services/test_game_error.py -q`
Expected: FAIL with `AttributeError: 'GameError' object has no attribute 'player_message'`

- [ ] **Step 3: Implement the property**

In `idle_chapters/services/errors.py`, replace the body of `project_player()` (lines 161-175) with:

```python
    @property
    def player_message(self) -> str:
        """Tone-contract message rendered from assets/error_templates.json."""
        templates = _load_templates()
        entry = templates.get(self.kind.value, {})
        template = entry.get("template", "")
        fallback = entry.get("fallback", "Something unexpected happened.")
        try:
            return template.format(**self.context) if template else fallback
        except (KeyError, IndexError):
            return fallback

    def project_player(self) -> dict[str, Any]:
        """Minimal RFC 9457: type, title (rendered template), status."""
        return {
            "type": self.type_uri,
            "title": self.player_message,
            "status": self.http_status,
        }
```

- [ ] **Step 4: Run the full services + API test suites to verify no regression**

Run: `uv run pytest tests/services tests/api -q`
Expected: all PASS (the API player-projection tests exercise the same rendering path).

- [ ] **Step 5: Commit**

```bash
git add idle_chapters/services/errors.py tests/services/test_game_error.py
git commit -m "refactor: extract GameError.player_message for CLI projection"
```

---

### Task 3: Terminal renderer `idle_chapters/ui/errors.py`

The CLI projection from the design doc: default mode prints the player message via `print_block` (same padding/wrapping as all game text); verbose mode prepends the Z535 signal word and writes the WHAT/MEANS/DO detail to stderr. A module-level verbose flag avoids threading a boolean through every scene function.

**Files:**
- Create: `idle_chapters/ui/errors.py`
- Create: `tests/ui/__init__.py` (empty)
- Test: `tests/ui/test_cli_errors.py`

**Interfaces:**
- Consumes: `GameError.player_message` (Task 2), `GameError.signal: Signal`, `GameError.detail: str`; `print_block(text)` and `wrap_text(text)` from `idle_chapters/ui/text.py`.
- Produces (Tasks 4, 5, 6 rely on these exact names):
  - `set_verbose(value: bool) -> None`
  - `is_verbose() -> bool`
  - `print_error(err: GameError) -> None`
  - `invalid_choice(selection: str, labels: list[str]) -> GameError` — shared constructor for menu-input misses (`intent_no_match`, effect `none`, recovery `correctable`; context `{"input": selection, "available_actions": ", ".join(labels)}`).

- [ ] **Step 1: Write the failing tests**

Create `tests/ui/__init__.py` (empty file), then `tests/ui/test_cli_errors.py`:

```python
import pytest

from idle_chapters.services.errors import Effect, ErrorKind, GameError, Recovery
from idle_chapters.ui import errors as ui_errors


@pytest.fixture(autouse=True)
def reset_verbose():
    yield
    ui_errors.set_verbose(False)


def _caution_error():
    return GameError(
        kind=ErrorKind.ACTION_NOT_ELIGIBLE,
        effect=Effect.NONE,
        recovery=Recovery.CORRECTABLE,
        detail=(
            "WHAT: Action gather_herbs failed conditions.\n"
            "MEANS: State unchanged.\n"
            "DO: Choose an eligible action."
        ),
    )


def test_default_prints_player_message_only(capsys):
    ui_errors.print_error(_caution_error())
    out, err = capsys.readouterr()
    assert "That doesn't seem possible right now" in out
    assert "CAUTION" not in out
    assert err == ""


def test_verbose_prepends_signal_word(capsys):
    ui_errors.set_verbose(True)
    ui_errors.print_error(_caution_error())
    out, _ = capsys.readouterr()
    assert "CAUTION: That doesn't seem possible right now" in out


def test_verbose_writes_three_panel_detail_to_stderr(capsys):
    ui_errors.set_verbose(True)
    ui_errors.print_error(_caution_error())
    _, err = capsys.readouterr()
    assert "WHAT:" in err
    assert "MEANS:" in err
    assert "DO:" in err


def test_verbose_without_detail_writes_nothing_to_stderr(capsys):
    ui_errors.set_verbose(True)
    err_obj = GameError(
        kind=ErrorKind.SESSION_NOT_FOUND, effect=Effect.NONE, recovery=Recovery.TERMINAL
    )
    ui_errors.print_error(err_obj)
    _, err = capsys.readouterr()
    assert err == ""


def test_invalid_choice_builds_intent_no_match(capsys):
    err_obj = ui_errors.invalid_choice("7", ["make tea", "sit by the fire"])
    assert err_obj.kind == ErrorKind.INTENT_NO_MATCH
    assert err_obj.effect == Effect.NONE
    assert err_obj.recovery == Recovery.CORRECTABLE
    ui_errors.print_error(err_obj)
    out, _ = capsys.readouterr()
    assert '"7"' in out
    assert "make tea, sit by the fire" in out
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/ui -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'idle_chapters.ui.errors'`

- [ ] **Step 3: Implement the module**

Create `idle_chapters/ui/errors.py`:

```python
"""CLI projection of GameError: player templates + optional Z535 detail.

Default output is purely tone-contract (the player message). Verbose mode
prepends the Z535 signal word on stdout and writes the WHAT/MEANS/DO
three-panel detail to stderr.
"""

from __future__ import annotations

import sys

from idle_chapters.services.errors import Effect, ErrorKind, GameError, Recovery
from idle_chapters.ui.text import print_block, wrap_text

# ponytail: module-level flag, not threaded through scene signatures;
# revisit if the CLI ever grows per-command verbosity.
_verbose = False


def set_verbose(value: bool) -> None:
    global _verbose
    _verbose = value


def is_verbose() -> bool:
    return _verbose


def invalid_choice(selection: str, labels: list[str]) -> GameError:
    """A menu input that matched nothing the scene offered."""
    return GameError(
        kind=ErrorKind.INTENT_NO_MATCH,
        effect=Effect.NONE,
        recovery=Recovery.CORRECTABLE,
        context={"input": selection, "available_actions": ", ".join(labels)},
    )


def print_error(err: GameError) -> None:
    """Render a GameError for the terminal (the CLI projection)."""
    if not _verbose:
        print_block(err.player_message)
        return
    print_block(f"{err.signal.value}: {err.player_message}")
    if err.detail:
        print(wrap_text(err.detail), file=sys.stderr)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/ui -q`
Expected: 5 PASS

- [ ] **Step 5: Commit**

```bash
git add idle_chapters/ui/errors.py tests/ui/__init__.py tests/ui/test_cli_errors.py
git commit -m "feat: CLI error projection with Z535 verbose mode"
```

---

### Task 4: `--verbose` flag in `main.py`

`main()` (`idle_chapters/main.py:22`) takes no arguments today and `__main__.py` just calls it. Add argparse so `python -m idle_chapters --verbose` (or `-v`) enables verbose error rendering. Extract `parse_args(argv)` so the parsing is testable without launching the interactive game.

**Files:**
- Modify: `idle_chapters/main.py:1-31`
- Test: `tests/test_cli_args.py`

**Interfaces:**
- Consumes: `set_verbose(value: bool)` from Task 3.
- Produces: `parse_args(argv: list[str] | None = None) -> argparse.Namespace` with a `.verbose: bool` attribute; `main()` unchanged in behavior otherwise.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_cli_args.py`:

```python
from idle_chapters.main import parse_args


def test_default_is_not_verbose():
    assert parse_args([]).verbose is False


def test_long_flag():
    assert parse_args(["--verbose"]).verbose is True


def test_short_flag():
    assert parse_args(["-v"]).verbose is True
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_cli_args.py -q`
Expected: FAIL with `ImportError: cannot import name 'parse_args'`

- [ ] **Step 3: Implement**

In `idle_chapters/main.py`, add the import block at the top and replace `main()`:

```python
import argparse

from idle_chapters.ui.errors import set_verbose
from idle_chapters.ui.text import print_block
from idle_chapters.scenes.cottage import run_cottage
from idle_chapters.scenes.inventory import load_inventory, save_inventory
from idle_chapters.scenes.welcome import player_menu, save_player, welcome
```

```python
def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="idle_chapters", description="A cozy text-based adventure."
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="show Z535 signal words and WHAT/MEANS/DO error detail",
    )
    return parser.parse_args(argv)


def main() -> None:
    args = parse_args()
    set_verbose(args.verbose)
    try:
        print_block(welcome)
        player = player_menu()
        if player is None:
            return
        run_cottage(player, add_collectible)
    except KeyboardInterrupt:
        print("\nGoodbye.")
        raise SystemExit(0)
```

(`add_collectible` stays exactly as it is at `idle_chapters/main.py:6-19`.)

- [ ] **Step 4: Run tests and a smoke check**

Run: `uv run pytest tests/test_cli_args.py -q`
Expected: 3 PASS

Run: `uv run python -m idle_chapters --help`
Expected: usage text showing `-v, --verbose`, exit code 0.

- [ ] **Step 5: Commit**

```bash
git add idle_chapters/main.py tests/test_cli_args.py
git commit -m "feat: add --verbose flag wiring for CLI error detail"
```

---

### Task 5: Reroute `scenes/welcome.py` error paths

Per `errors.md`, not every `print()` is an error. The decision this task implements:

| Site | Treatment |
|---|---|
| `welcome.py:105` `"Please choose a valid option (1-6)."` | `print_error(invalid_choice(...))` — menu miss |
| `welcome.py:178` `"Hmm, that doesn't seem like one of the choices..."` | `print_error(invalid_choice(...))` — menu miss |
| `welcome.py:31` and `:38` `"Error saving file: {e}"` | `print_error(GameError(PERSISTENCE_FAILURE, ...))` — real error |
| `welcome.py:48,54,64,72` load-failure notices | Stay inline; reword to tone-compliant recovery copy (the game auto-recovers; nothing is asked of the player) |
| `welcome.py:120` schema-validation detail | Developer info: write to stderr only when `is_verbose()` |

**Files:**
- Modify: `idle_chapters/scenes/welcome.py`
- Test: `tests/player/test_welcome_errors.py`

**Interfaces:**
- Consumes: `print_error`, `invalid_choice`, `is_verbose` (Task 3); `GameError`, `ErrorKind`, `Effect`, `Recovery` from `idle_chapters/services/errors.py`.
- Produces: no new public API; behavior change only.

- [ ] **Step 1: Write the failing tests**

Create `tests/player/test_welcome_errors.py`:

```python
from idle_chapters.scenes import welcome


def test_invalid_pronoun_choice_uses_tone_template(monkeypatch, capsys):
    answers = iter(["9", "6"])  # one bad choice, then exit
    monkeypatch.setattr("builtins.input", lambda _: next(answers))
    result = welcome._select_pronouns()
    assert result is None
    out, _ = capsys.readouterr()
    assert 'Hmm, I\'m not sure what you mean by "9"' in out
    assert "Please choose a valid option" not in out


def test_save_player_io_error_uses_persistence_template(monkeypatch, capsys):
    def boom(*args, **kwargs):
        raise IOError("disk full")

    monkeypatch.setattr("builtins.open", boom)
    welcome.save_player({"player_info": {"display_name": "Fern"}})
    out, _ = capsys.readouterr()
    assert "Your story was briefly interrupted" in out
    assert "Error saving file" not in out
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/player/test_welcome_errors.py -q`
Expected: FAIL — output still contains the legacy strings.

- [ ] **Step 3: Implement the reroutes**

In `idle_chapters/scenes/welcome.py`, add imports after the existing ones (line 14):

```python
import sys

from idle_chapters.services.errors import Effect, ErrorKind, GameError, Recovery
from idle_chapters.ui.errors import invalid_choice, is_verbose, print_error
```

Replace `save_player`'s except clause (lines 30-31) — same pattern in `_save_players` (lines 38-39), with `PLAYERS_FILE` in place of `PLAYER_FILE`:

```python
    except IOError as e:
        print_error(GameError(
            kind=ErrorKind.PERSISTENCE_FAILURE,
            effect=Effect.PARTIAL,
            recovery=Recovery.RETRYABLE,
            detail=(
                f"WHAT: Failed to write {PLAYER_FILE}: {e}.\n"
                "MEANS: Player progress exists in memory but was not saved to disk.\n"
                "DO: Check file permissions and free disk space, then try again."
            ),
            context={"path": PLAYER_FILE},
        ))
```

In `_select_pronouns`, replace line 105 `print("Please choose a valid option (1-6).")`:

```python
        print_error(invalid_choice(
            choice,
            ["she/her", "he/him", "they/them", "ze/hir", "you/your", "exit"],
        ))
```

In `select_player`, replace line 178 `print("\nHmm, that doesn't seem like one of the choices. Try again?\n")`:

```python
        labels = [
            p.get("player_info", {}).get("display_name") or "friend" for p in players
        ] + ["create a new player", "exit"]
        print_error(invalid_choice(choice, labels))
```

In `_validate_player`, replace line 120 `print(f"Player data failed schema validation: {exc.message}")`:

```python
        if is_verbose():
            print(f"Player data failed schema validation: {exc.message}", file=sys.stderr)
```

Reword the four inline recovery notices (tone-contract copy; the game recovers on its own):
- line 48: `print("Existing player data is invalid. Creating a new player.")` → `print_block("Those pages seem to belong to a different story. Let's begin a new one.")`
- line 54: `print("Error loading player file. Creating a new player.")` → `print_block("Your earlier pages are resting somewhere else. A fresh page is ready.")`
- line 64: `print("Existing players data is invalid. Creating a new list.")` → same copy as line 48
- line 72: `print("Error loading players file. Creating a new list.")` → same copy as line 54

Add `print_block` to the imports from `idle_chapters.ui.text`:

```python
from idle_chapters.ui.text import print_block
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/player -q`
Expected: all PASS (new tests plus any existing player tests).

- [ ] **Step 5: Commit**

```bash
git add idle_chapters/scenes/welcome.py tests/player/test_welcome_errors.py
git commit -m "feat: route welcome scene errors through GameError CLI projection"
```

---

### Task 6: Reroute `scenes/cottage.py` invalid-choice path

One site: `cottage.py:260` `print("Please choose a valid option.")` in `_run_interaction`'s selection loop.

**Files:**
- Modify: `idle_chapters/scenes/cottage.py:260` (plus import)
- Test: `tests/player/test_cottage_errors.py`

**Interfaces:**
- Consumes: `print_error`, `invalid_choice` (Task 3); `_run_interaction(interaction: dict, state: dict, add_collectible) -> str | None` at `cottage.py:211`.
- Produces: no new public API.

- [ ] **Step 1: Write the failing test**

Create `tests/player/test_cottage_errors.py`:

```python
from idle_chapters.scenes.cottage import _run_interaction


def test_invalid_selection_uses_tone_template(monkeypatch, capsys):
    interaction = {
        "prompt": "The kettle hums softly.",
        "choices": [
            {"choice_id": "look", "label": "Look around", "result": "You look around."}
        ],
    }
    answers = iter(["5", "1"])  # one bad selection, then the valid one
    monkeypatch.setattr("builtins.input", lambda _: next(answers))
    result = _run_interaction(interaction, {"player": {}}, lambda p, i: False)
    assert result is None
    out, _ = capsys.readouterr()
    assert 'Hmm, I\'m not sure what you mean by "5"' in out
    assert "Look around" in out
    assert "Please choose a valid option" not in out
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/player/test_cottage_errors.py -q`
Expected: FAIL — output contains "Please choose a valid option."

- [ ] **Step 3: Implement**

In `idle_chapters/scenes/cottage.py`, add to the imports (near line 5):

```python
from idle_chapters.ui.errors import invalid_choice, print_error
```

Replace line 260 `print("Please choose a valid option.")`:

```python
            print_error(invalid_choice(selection, [c["label"] for c in choices]))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/player/test_cottage_errors.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add idle_chapters/scenes/cottage.py tests/player/test_cottage_errors.py
git commit -m "feat: route cottage scene invalid choices through CLI projection"
```

---

### Task 7: Docs, full gate, and hand-off

**Files:**
- Modify: `design-docs/game_design/errors.md:104-121` (implementation-status table + Phase C section)

**Interfaces:**
- Consumes: everything above, complete.
- Produces: docs consistent with shipped behavior; branch ready for review.

- [ ] **Step 1: Update `errors.md`**

In the Implementation status table (line 111), change the CLI row:

```markdown
| CLI projection (Phase C) | Done | `idle_chapters/ui/errors.py` (`print_error`), `--verbose` flag in `main.py` |
```

Replace the "What Phase C will change" section (lines 114-120) with a short "What Phase C changed" summary: menu misses render `intent_no_match`, save failures render `persistence_failure`, auto-recovering load notices stayed inline with tone-compliant copy, schema-validation detail is verbose-only stderr. Add one line: "ANSI colors for signal words were deliberately skipped; add if terminal output grows richer."

- [ ] **Step 2: Run the full test suite**

Run: `uv run pytest -q`
Expected: all PASS, no skips introduced by this branch.

- [ ] **Step 3: Manual verbose smoke check**

Run: `uv run python -m idle_chapters --verbose`, enter an invalid menu choice at the player menu, then exit.
Expected: stdout shows `CAUTION: Hmm, I'm not sure what you mean by …`; no traceback.

- [ ] **Step 4: Commit docs**

```bash
git add design-docs/game_design/errors.md
git commit -m "docs: record Phase C CLI projection as shipped"
```

- [ ] **Step 5: Review gate and close-out (per repo workflow)**

- Run the whole-branch `adversarial-review` (Craftsman/ponytail + QA lenses at minimum; no API surface changed, so Security/Data lenses are optional).
- Open the PR; after merge, `bd close chapters-vxv` and update the `errors.md` pointer memory if any (per `/close-out`).

---

## Self-Review

- **Spec coverage:** design doc CLI section — player templates reused (Tasks 2/3), signal word prepended in verbose (Task 3), three-panel detail to stderr via `--verbose` (Tasks 3/4), colors explicitly skipped (Global Constraints); `errors.md` Phase C items 1-3 — reroute (Tasks 5/6), verbose flag (Task 4), the "which prints warrant GameError" decision (Task 5 table). ✓
- **Placeholder scan:** none — every step carries runnable code or an exact command. ✓
- **Type consistency:** `player_message` (Task 2) consumed by Task 3; `print_error(err)`, `invalid_choice(selection, labels)`, `set_verbose(bool)`, `is_verbose()` (Task 3) consumed by Tasks 4-6 with matching signatures. ✓
