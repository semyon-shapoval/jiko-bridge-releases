"""
Base scene for Blender
Code by Semyon Shapoval, 2026
"""

import os
import tempfile

import bpy

from ..jb_types import JbSource


class JbSceneBase:
    """Base class for scene."""

    def __init__(self, source: JbSource):
        self._source = source
        base = os.path.join(tempfile.gettempdir(), "jiko-bridge")
        os.makedirs(base, exist_ok=True)
        self.cache_path = base

    def source(self) -> JbSource:
        """Return the context to operate in."""
        if self._source is not None:
            return self._source
        return bpy.context
