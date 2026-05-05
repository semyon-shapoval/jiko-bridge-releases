#!/usr/bin/env python3
"""Universal diff helper for Jiko Bridge Makefile."""

from __future__ import annotations

import difflib
import pathlib
import re
import sys
from typing import Iterable

DIFF_FILES = [
    "jb_protocols.py",
    "jb_api.py",
    "jb_asset_importer.py",
    "jb_asset_exporter.py",
]
IGNORE_RE = re.compile(r"^(?:import |from )")


def read_filtered(path: pathlib.Path) -> list[str]:
    text = path.read_text(encoding="utf-8", errors="replace")
    return [line for line in text.splitlines(keepends=True) if not IGNORE_RE.match(line)]


def find_file(root: pathlib.Path, name: str) -> pathlib.Path | None:
    matches = list(root.rglob(name))
    if not matches:
        return None
    if len(matches) > 1:
        raise ValueError(f"Multiple matches for '{name}' under root '{root}': {matches}")
    return matches[0]


def compare_file(name: str, roots: Iterable[pathlib.Path]) -> bool:
    roots = list(roots)
    files = []

    for root in roots:
        try:
            file_path = find_file(root, name)
        except ValueError as exc:
            print(exc)
            return True

        if file_path is None:
            print(f"Missing file for root '{root}': {name}")
            return True

        files.append((root, file_path, read_filtered(file_path)))

    baseline_lines = files[0][2]
    failed = False

    for root, file_path, lines in files[1:]:
        if lines != baseline_lines:
            print(f"Comparing {name}: {files[0][0]} vs {root}")
            sys.stdout.writelines(
                difflib.unified_diff(
                    baseline_lines,
                    lines,
                    fromfile=str(files[0][1]),
                    tofile=str(file_path),
                )
            )
            failed = True

    return failed


def main(argv: list[str]) -> int:
    if len(argv) < 3:
        print("Usage: check_diff.py <root_path_1> <root_path_2> [<root_path_3> ...]")
        return 2

    roots = [pathlib.Path(arg) for arg in argv[1:]]
    failed = False

    for name in DIFF_FILES:
        failed |= compare_file(name, roots)

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
