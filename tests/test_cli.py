import importlib


def test_cli_modules_exist() -> None:
    for module_name in ("cli.main", "cli.render", "cli.client"):
        importlib.import_module(module_name)
