"""
Base scene class with shared utilities for C4D scene operations.
Code by Semyon Shapoval, 2026
"""

import os
import tempfile

import c4d


class JbSceneBase:
    """Base class for scene operations, providing shared utilities."""

    def __init__(self):
        base = os.path.join(tempfile.gettempdir(), "jiko-bridge")
        os.makedirs(base, exist_ok=True)
        self.cache_path = base

    @property
    def doc(self) -> c4d.documents.BaseDocument:
        """Return the active document."""
        return c4d.documents.GetActiveDocument()
