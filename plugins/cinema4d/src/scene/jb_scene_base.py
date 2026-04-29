"""
Base scene class with shared utilities for C4D scene operations.
Code by Semyon Shapoval, 2026
"""

import os
import tempfile

import c4d
from src.jb_types import JbSource


class JbSceneBase:
    """Base class for scene operations, providing shared utilities."""

    def __init__(self, source: JbSource = None):
        base = os.path.join(tempfile.gettempdir(), "jiko-bridge")
        os.makedirs(base, exist_ok=True)
        self.cache_path = base
        self._source = source

    @property
    def source(self) -> c4d.documents.BaseDocument:
        """Return the active document."""
        if not self._source:
            self._source = c4d.documents.GetActiveDocument()
        return self._source
