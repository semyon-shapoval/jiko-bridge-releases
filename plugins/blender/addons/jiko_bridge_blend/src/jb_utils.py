"""
Utility functions for Jiko Bridge Blender plugin.
Code by Semyon Shapoval, 2026
"""

import sys
import logging

import addon_utils


def get_logger(name: str) -> logging.Logger:
    """Get a logger."""
    logger = logging.getLogger(name)

    if logger.handlers:
        return logger

    logger.setLevel(logging.DEBUG)
    formatter = logging.Formatter(
        "[Jiko Bridge] %(levelname)s [%(name)s] %(message)s", datefmt="%H:%M:%S"
    )

    console = logging.StreamHandler()
    console.setLevel(logging.DEBUG)
    console.setFormatter(formatter)
    logger.addHandler(console)

    return logger


def confirm(_message: str) -> bool:
    """Always returns True until a Blender dialog is implemented.

    TODO: implement a proper Blender invoke()/popup dialog.
    """
    return True


def reload_plugin_modules(addon_module_name: str = "JikoBridgeBlend") -> None:
    """Reload the addon modules by disabling and enabling the addon."""
    addon_utils.disable(addon_module_name)
    to_remove = [k for k in list(sys.modules) if addon_module_name in k]
    for k in to_remove:
        del sys.modules[k]
    addon_utils.enable(addon_module_name)
