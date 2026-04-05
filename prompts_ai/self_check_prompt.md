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