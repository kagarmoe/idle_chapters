from pathlib import Path


def test_content_manifest_paths(repo_root: Path) -> None:
    from app.content.manifest import ContentManifest

    manifest = ContentManifest()

    for label, path in manifest.schemas.items():
        assert (repo_root / path).is_file(), f"Missing schema path for {label}: {path}"

    for label, path in manifest.assets.items():
        assert (repo_root / path).is_file(), f"Missing asset path for {label}: {path}"

    for label, path in manifest.lexicons.items():
        assert (repo_root / path).is_file(), f"Missing lexicon path for {label}: {path}"


def test_manifest_lists_core_assets() -> None:
    from app.content.manifest import ContentManifest

    manifest = ContentManifest()
    expected_assets = {
        "places",
        "npcs",
        "collectibles",
        "interactions",
        "tea",
        "spells",
        "storylets",
        "journal_templates",
    }

    assert expected_assets.issubset(set(manifest.assets.keys()))
