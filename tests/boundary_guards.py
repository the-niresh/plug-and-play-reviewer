"""Shared boundary guard constants and import-graph helpers for tests."""

from __future__ import annotations

import ast
from pathlib import Path

from repo_paths import SRC_ROOT

GUARDED_PACKAGES = frozenset(
    {
        "contracts",
        "control_plane",
        "runner",
        "local_store",
        "reviewer",
        "retrieval",
        "verification",
        "containers",
        "notifications",
        "observability",
        "cli",
        "web",
        "github",
        "connectors",
        "evals",
        "models",
        "prompts",
        "security",
        "workflow",
        "reliability",
    }
)

EXPECTED_EXISTING_PACKAGES = frozenset(
    {
        "contracts",
        "control_plane",
        "runner",
        "local_store",
        "containers",
        "observability",
        "cli",
        "web",
        "github",
        "connectors",
        "evals",
        "models",
        "prompts",
        "reviewer",
        "security",
        "retrieval",
        "verification",
        "notifications",
        "workflow",
        "reliability",
    }
)

CONTROL_PLANE_FORBIDDEN_TARGETS = frozenset(
    {
        "runner",
        "models",
        "local_store",
        "reviewer",
        "retrieval",
        "verification",
        "containers",
        "notifications",
        "workflow",
    }
)

IMPORTS_ONLY_CONTRACTS_PACKAGES = frozenset({"observability"})

RUNNER_SIDE_PACKAGES = frozenset(
    {
        "runner",
        "models",
        "local_store",
        "retrieval",
        "verification",
        "notifications",
        "containers",
        "reviewer",
        "workflow",
    }
)
RUNNER_SIDE_FORBIDDEN_MODULES = frozenset(
    {"pr_reviewer.db", "pr_reviewer.control_plane", "pr_reviewer.cli"}
)

HOSTED_SIDE_PACKAGES = frozenset({"web", "connectors"})
HOSTED_SIDE_FORBIDDEN_TARGETS = CONTROL_PLANE_FORBIDDEN_TARGETS


def _module_name_for_file(file_path: Path) -> str:
    relative = file_path.relative_to(SRC_ROOT.parent).with_suffix("")
    parts = list(relative.parts)
    if parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts)


def _resolve_import(file_path: Path, node: ast.Import | ast.ImportFrom) -> list[str]:
    if isinstance(node, ast.Import):
        return [alias.name for alias in node.names]

    if node.level == 0:
        return [node.module] if node.module else []

    own_module = _module_name_for_file(file_path)
    own_parts = own_module.split(".")
    package_parts = own_parts[:-1] if file_path.name != "__init__.py" else own_parts
    trimmed = (
        package_parts[: len(package_parts) - (node.level - 1)] if node.level > 1 else package_parts
    )
    if node.module:
        trimmed = trimmed + node.module.split(".")
    return [".".join(trimmed)]


def collect_imports(package_dir: Path) -> set[str]:
    """Return every module dotted-path imported under package_dir, via static AST parsing."""
    imports: set[str] = set()
    for file_path in sorted(package_dir.rglob("*.py")):
        if "__pycache__" in file_path.parts:
            continue
        tree = ast.parse(file_path.read_text(encoding="utf-8"), filename=str(file_path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import | ast.ImportFrom):
                imports.update(_resolve_import(file_path, node))
    return imports


def _imports_targeting(imports: set[str], forbidden_package: str) -> set[str]:
    return _imports_matching_prefix(imports, f"pr_reviewer.{forbidden_package}")


def _imports_matching_prefix(imports: set[str], prefix: str) -> set[str]:
    return {module for module in imports if module == prefix or module.startswith(prefix + ".")}
