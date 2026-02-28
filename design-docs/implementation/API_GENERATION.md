# API Generation (Spec-First)

## Goal

Adopt a spec-first workflow where `docs/openapi.json` is the canonical API contract.
Server stubs are generated from the spec, then implemented in a separate layer.

## Canonical Spec Location

- `docs/openapi.json` is the source of truth.
- Code generation reads from this file only.

## Recommended Tooling

**OpenAPI Generator** (preferred)

Pros:
- Mature tooling with strong FastAPI support.
- Produces typed models + stubbed routes.
- Works well with large specs.

Cons:
- Generated code can be verbose.
- Regeneration overwrites files in the output folder.

## Folder Strategy

- Generated output goes into `app_generated/`.
- Custom logic stays in `app/` and imports generated types/interfaces as needed.
- Never edit `app_generated/` by hand.

Example layout:

```
app/
  api/
    app.py
    handlers/
      world.py
      sessions.py
app_generated/
  apis/
  models/
  main.py
docs/
  openapi.json
```

## Generation Command

```
openapi-generator-cli generate \
  -i docs/openapi.json \
  -g python-fastapi \
  -o app_generated
```

If using `fastapi-codegen` instead:

```
fastapi-codegen --input docs/openapi.json --output app_generated
```

## Implementation Strategy

1. Generate the server stubs into `app_generated/`.
2. Wire router implementations to call `app/` logic.
3. Keep custom logic in `app/` so regeneration is safe.
4. Treat changes to `docs/openapi.json` as the only API surface edits.

## Regeneration Rules

- Regeneration is allowed at any time.
- Do not edit generated code directly.
- Commit the spec and generated code together.

## Notes

- FastAPI can still serve `/docs`, but it should reflect the spec-first contract.
- If generated router names or paths drift from the spec, fix the spec and regenerate.
