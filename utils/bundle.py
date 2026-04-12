#!/usr/bin/env python3
"""
bundle.py — Universal plugin bundler

Concatenates all local modules into a single file in dependency order.
Duplicate imports are removed in-place; the first occurrence of each import
is kept exactly where it appears. No imports are moved to the top.

Usage:
    python bundle.py --entry <entry_file> --out <output_file> [--name <name>]
"""

import argparse
import ast
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# Step 1 — collect all .py files from src_dir
# ---------------------------------------------------------------------------


class Module:
    __slots__ = ("name", "path", "source")

    def __init__(self, name: str, path: Path, source: str):
        self.name = name
        self.path = path
        self.source = source


def collect(src_dir: Path) -> dict:
    result = {}

    for py in sorted(src_dir.rglob("*.py")):
        parts = py.relative_to(src_dir).parts
        if "__pycache__" in parts:
            continue

        name_parts = list(Path(*parts).with_suffix("").parts)

        if name_parts[-1] == "__init__":
            if len(name_parts) == 1:
                key = "__init__"
            else:
                src = py.read_text(encoding="utf-8").strip()
                if not src:
                    continue
                key = ".".join(name_parts[:-1]) + ".__init__"
        else:
            key = ".".join(name_parts)

        result[key] = Module(key, py, py.read_text(encoding="utf-8"))

    return result


# ---------------------------------------------------------------------------
# Step 2 — find local imports
# ---------------------------------------------------------------------------


def local_deps(source: str, known: set) -> list:
    deps = []
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return deps

    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            if node.level > 0:
                candidates = [mod] + [a.name for a in node.names]
            else:
                candidates = [mod, mod.split(".")[0]]
            for c in candidates:
                if c in known:
                    deps.append(c)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                root = alias.name.split(".")[0]
                if root in known:
                    deps.append(root)

    return list(dict.fromkeys(deps))


# ---------------------------------------------------------------------------
# Step 3 — topological sort
# ---------------------------------------------------------------------------


def topo_sort(modules: dict) -> list:
    known = set(modules)
    visited = set()
    order = []

    def visit(name, stack):
        if name in visited or name not in modules:
            return
        if name in stack:
            order.append(name)
            return
        stack.add(name)
        for dep in local_deps(modules[name].source, known):
            visit(dep, stack)
        stack.discard(name)
        visited.add(name)
        order.append(name)

    for name in modules:
        visit(name, set())

    return order


# ---------------------------------------------------------------------------
# Step 4 — rewrite: strip local imports, drop duplicate external imports
#           in-place (first occurrence wins, order preserved)
# ---------------------------------------------------------------------------


def rewrite(source: str, known: set, seen_imports: set) -> str:
    """
    Remove local imports entirely.
    Keep external imports only if they haven't been emitted yet;
    track them in `seen_imports` (mutated in place).
    Strip docstrings and blank comment lines.
    """
    try:
        tree = ast.parse(source)

        class Cleaner(ast.NodeTransformer):
            def _strip_docstring(self, node):
                if (
                    node.body
                    and isinstance(node.body[0], ast.Expr)
                    and isinstance(node.body[0].value, ast.Constant)
                    and isinstance(node.body[0].value.value, str)
                ):
                    node.body.pop(0)
                if not node.body:
                    node.body.append(ast.Pass())
                return node

            def visit_FunctionDef(self, node):
                self.generic_visit(node)
                return self._strip_docstring(node)

            def visit_AsyncFunctionDef(self, node):
                self.generic_visit(node)
                return self._strip_docstring(node)

            def visit_ClassDef(self, node):
                self.generic_visit(node)
                return self._strip_docstring(node)

            def visit_Module(self, node):
                self.generic_visit(node)
                return self._strip_docstring(node)

        tree = Cleaner().visit(tree)
        ast.fix_missing_locations(tree)
        source = ast.unparse(tree)
    except SyntaxError:
        pass

    out = []
    for line in source.splitlines(keepends=True):
        stripped = line.strip()

        # Drop blank comment lines
        if stripped.startswith("#"):
            continue

        # Check if this line is an import statement
        if stripped.startswith("from ") or stripped.startswith("import "):
            # Try to parse it to determine if it's local
            try:
                mini_tree = ast.parse(stripped, mode="single")
            except SyntaxError:
                out.append(line)
                continue

            is_local = False
            for node in ast.walk(mini_tree):
                if isinstance(node, ast.ImportFrom):
                    mod = node.module or ""
                    if node.level > 0 or mod.split(".")[0] in known or mod in known:
                        is_local = True
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name.split(".")[0] in known:
                            is_local = True

            if is_local:
                # Local import — drop entirely
                continue

            # External import — keep only if not seen before
            key = stripped
            if key in seen_imports:
                continue
            seen_imports.add(key)

        out.append(line)

    return "".join(out)


# ---------------------------------------------------------------------------
# Step 5 — assemble
# ---------------------------------------------------------------------------

_HEADER = """\
# =============================================================================
# {plugin_name} — BUNDLED SINGLE-FILE BUILD
# Generated by bundle.py  |  do not edit manually
# =============================================================================

"""

_SECTION = """\
# =============================================================================
# {name}
# =============================================================================
{source}
"""


def bundle(src_dir: Path, entry_file: Path, plugin_name: str) -> str:
    modules = collect(src_dir)

    init_src = ""
    if "__init__" in modules:
        init_src = modules.pop("__init__").source

    try:
        entry_key = ".".join(entry_file.relative_to(src_dir).with_suffix("").parts)
        modules.pop(entry_key, None)
    except ValueError:
        pass

    known = set(modules)
    order = topo_sort(modules)

    entry_src = entry_file.read_text(encoding="utf-8")

    # Shared set — tracks every external import already emitted
    seen_imports: set = set()

    parts = [_HEADER.format(plugin_name=plugin_name)]

    if init_src:
        parts.append(
            _SECTION.format(
                name="__init__.py",
                source=rewrite(init_src, known, seen_imports),
            )
        )

    for name in order:
        if name not in modules:
            continue
        mod = modules[name]
        parts.append(
            _SECTION.format(
                name=mod.path.name,
                source=rewrite(mod.source, known, seen_imports),
            )
        )

    parts.append(
        _SECTION.format(
            name=entry_file.name,
            source=rewrite(entry_src, known, seen_imports),
        )
    )

    return "".join(parts)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(
        description="Bundle a plugin into a single self-contained file",
    )
    parser.add_argument(
        "--entry", type=Path, required=True, help="Entry-point file (.py or .pyp)"
    )
    parser.add_argument("--out", type=Path, required=True, help="Output bundled file")
    parser.add_argument(
        "--name", default="", help="Display name (defaults to entry stem)"
    )

    args = parser.parse_args()

    if not args.entry.exists():
        print(f"[ERROR] --entry not found: {args.entry}")
        sys.exit(1)

    src_dir = args.entry.parent
    plugin_name = args.name or args.entry.stem
    result = bundle(src_dir, args.entry, plugin_name)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(result, encoding="utf-8")
    print(f"[OK] {args.out}  ({args.out.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
