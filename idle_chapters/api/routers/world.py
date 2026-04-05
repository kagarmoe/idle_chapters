from __future__ import annotations

from fastapi import APIRouter, Depends

from idle_chapters.api.deps import get_content_repo
from idle_chapters.content.repo import ContentRepo


router = APIRouter(prefix="/v1/world", tags=["world"])


@router.get(
    "/manifest",
    description="""Return metadata about all game content: schemas, assets, and lexicons.

**curl:**
```bash
curl http://localhost:8000/v1/world/manifest
```
""",
)
def get_manifest(repo: ContentRepo = Depends(get_content_repo)) -> dict[str, object]:
    manifest = repo.manifest
    return {
        "schemas": dict(manifest.schemas),
        "assets": dict(manifest.assets),
        "lexicons": dict(manifest.lexicons),
    }


@router.get("/places", description="List all places in the game world with their zone, mood, and player need.")
def get_places(repo: ContentRepo = Depends(get_content_repo)) -> list[dict]:
    return list(repo.places_by_id.values())


@router.get("/scenes", description="List all authored scenes with their entry nodes and choice graphs.")
def get_scenes(repo: ContentRepo = Depends(get_content_repo)) -> list[dict]:
    return list(repo.scenes_by_id.values())


@router.get("/actions", description="List all actions with their labels, conditions, effects, and results.")
def get_actions(repo: ContentRepo = Depends(get_content_repo)) -> list[dict]:
    return list(repo.actions_by_id.values())


@router.get("/collectibles", description="List all collectible items with their types, origins, and symbolic meanings.")
def get_collectibles(repo: ContentRepo = Depends(get_content_repo)) -> list[dict]:
    return list(repo.collectibles_by_id.values())


@router.get("/npcs", description="List all NPCs with their display names, kinds, and home locations.")
def get_npcs(repo: ContentRepo = Depends(get_content_repo)) -> list[dict]:
    return list(repo.npcs_by_id.values())
