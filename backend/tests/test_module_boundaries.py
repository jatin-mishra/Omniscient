"""Case 20: business modules may import the global layer, never each other."""

import ast
from pathlib import Path

import pytest

APP = Path(__file__).parent.parent / "app"
MODULES = ["onboarding", "policy_engine", "retrieval", "audit", "tracker"]


def imported_modules(path: Path) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text())):
        if isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
        elif isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
    return names


@pytest.mark.parametrize("module", MODULES)
def test_module_does_not_import_other_business_modules(module: str) -> None:
    forbidden = {f"app.{other}" for other in MODULES if other != module}
    violations = [
        f"{path.relative_to(APP)} imports {name}"
        for path in (APP / module).rglob("*.py")
        for name in imported_modules(path)
        if any(name == f or name.startswith(f + ".") for f in forbidden)
    ]
    assert violations == []
