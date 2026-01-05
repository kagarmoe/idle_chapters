# Generate content with LLM

## Model

[ LLM Generator ]
        ↓
[ Generator Interface ]
        ↓
[ Content Repository ]
        ↓
[ Engine ]

The LLM never sees:

- The full state object (only a sanitized view)
- Engine internals
- Other content, unless explicitly allowed

This protects:

- Tone
- Coherence
- Debuggability
- Sanity
