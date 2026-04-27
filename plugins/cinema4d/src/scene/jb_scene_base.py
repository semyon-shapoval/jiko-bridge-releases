"""
Base scene class with shared utilities for C4D scene operations.
Code by Semyon Shapoval, 2026
"""

import c4d

class JbSceneBase:
    """Base class for scene operations, providing shared utilities."""

    @property
    def doc(self) -> c4d.documents.BaseDocument:
        """Return the active document."""
        return c4d.documents.GetActiveDocument()