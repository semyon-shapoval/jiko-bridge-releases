"""
Utility functions for the Jiko Bridge Cinema 4D plugin.
Code by Semyon Shapoval, 2026
"""

import os
import sys
import importlib
from contextlib import contextmanager

import c4d


def is_headless() -> bool:
    """
    Headless-режим: c4dpy или Cinema 4D Commandline.
    """
    # Для c4dpy — имя исполняемого содержит "c4dpy"
    executable = sys.argv[0].lower() if sys.argv else ""
    return "c4dpy" in executable


@contextmanager
def busy_cursor(status_text: str = ""):
    """Context manager to show a busy cursor with optional status text."""
    if status_text:
        c4d.StatusSetText(status_text)
    c4d.gui.SetMousePointer(c4d.MOUSE_BUSY)
    try:
        yield
    finally:
        c4d.gui.SetMousePointer(c4d.MOUSE_NORMAL)
        c4d.StatusClear()


def confirm(message: str) -> bool:
    """Show a confirmation dialog. In headless mode, it always returns True."""
    if is_headless():
        return True
    return c4d.gui.QuestionDialog(message)


def reload_plugin_modules(plugin_dir: str) -> None:
    """Reload plugin modules to ensure the latest code is used."""
    importlib.invalidate_caches()

    plugin_modules = {}
    for name, mod in list(sys.modules.items()):
        mod_file = getattr(mod, "__file__", None)
        if mod_file is not None and os.path.abspath(mod_file).startswith(
            os.path.abspath(plugin_dir)
        ):
            plugin_modules[name] = mod

    for name in plugin_modules:
        del sys.modules[name]


def load_arnold_module():
    """Load Arnold module if it exists in the Cinema 4D library path."""
    try:
        arnold_folder = os.path.join(
            c4d.storage.GeGetC4DPath(c4d.C4D_PATH_LIBRARY), "scripts"
        )
        if os.path.exists(arnold_folder) and arnold_folder not in sys.path:
            sys.path.append(arnold_folder)
    except OSError as e:
        print(f"Failed to load Arnold module: {e}")
