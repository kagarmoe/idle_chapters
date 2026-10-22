#!/usr/bin/env sh
# Same setup on every machine that runs idle-chapters (laptops, worktrees, hestia's serve checkout).
# Secrets are not here: each clone's `default` vault starts empty with its own key.
set -eu
cd "$(dirname "$0")/.."

swamp extension install          # locked extensions + their skills, from upstream_extensions.json
bd bootstrap --yes               # beads DB from refs/dolt/data on origin; never deletes issues
bd hooks install --beads         # core.hooksPath = .beads/hooks
npm ci --prefix apps/web
# Python needs no install: gates run `uv run --with-requirements requirements.txt` (ic-checks).

swamp doctor datastores
swamp doctor vaults
