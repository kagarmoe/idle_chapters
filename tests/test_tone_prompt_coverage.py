"""Verify tone_system_prompt.md covers all sections of the tone contract."""

from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
TONE_CONTRACT = REPO / "design-docs" / "game_design" / "tone_contract.md"
TONE_SYSTEM_PROMPT = REPO / "prompts_ai" / "tone_system_prompt.md"


# Metadata headings in the contract that aren't content sections
_META_HEADINGS = {"status"}


def _extract_headings(text: str) -> set[str]:
    """Return normalised ## headings from markdown text."""
    headings = set()
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("## "):
            heading = stripped.removeprefix("## ").strip()
            # Remove leading "N. " numbering
            parts = heading.split(". ", 1)
            if len(parts) == 2 and parts[0].strip().isdigit():
                heading = parts[1]
            normalised = heading.lower()
            if normalised not in _META_HEADINGS:
                headings.add(normalised)
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
