from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import get_content_repo
from app.content.repo import ContentRepo


router = APIRouter(prefix="/v1/world", tags=["world"])


@router.get("/manifest")
def get_manifest(repo: ContentRepo = Depends(get_content_repo)) -> dict[str, object]:
    manifest = repo.manifest
    return {
        "schemas": dict(manifest.schemas),
        "assets": dict(manifest.assets),
        "lexicons": dict(manifest.lexicons),
    }


@router.get("/places")
def get_places(repo: ContentRepo = Depends(get_content_repo)) -> list[dict]:
    return list(repo.places_by_id.values())


@router.get("/scenes")
def get_scenes(repo: ContentRepo = Depends(get_content_repo)) -> list[dict]:
    return list(repo.scenes_by_id.values())


@router.get("/actions")
def get_actions(repo: ContentRepo = Depends(get_content_repo)) -> list[dict]:
    return list(repo.actions_by_id.values())


@router.get("/collectibles")
def get_collectibles(repo: ContentRepo = Depends(get_content_repo)) -> list[dict]:
    return list(repo.collectibles_by_id.values())


@router.get("/npcs")
def get_npcs(repo: ContentRepo = Depends(get_content_repo)) -> list[dict]:
    return list(repo.npcs_by_id.values())
