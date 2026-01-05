from pathlib import Path


def test_repo_structure(repo_root: Path) -> None:
    expected_dirs = [
        "assets",
        "lexicons",
        "schemas",
        "journal",
        "app",
        "tests",
        "dev/implementation",
    ]

    for rel_path in expected_dirs:
        assert (repo_root / rel_path).is_dir(), f"Missing directory: {rel_path}"


def test_stable_content_locations(repo_root: Path) -> None:
    assets_dir = repo_root / "assets"
    schemas_dir = repo_root / "schemas"
    lexicons_dir = repo_root / "lexicons"

    assert any(assets_dir.iterdir()), "assets/ should contain content files"
    assert any(schemas_dir.iterdir()), "schemas/ should contain schema files"
    assert any(lexicons_dir.iterdir()), "lexicons/ should contain lexicon files"
