"""
Scene tree traversal and querying.
Code by Semyon Shapoval, 2026
"""

from __future__ import annotations
from typing import Callable, Literal

import c4d
from src.scene.jb_scene_base import JbSceneBase


class JbSceneTree(JbSceneBase):
    """Traversal and querying of Cinema 4D object hierarchies.

    Implements the traversal group of JBSceneBase.
    Responsible only for reading the object tree — no mutations,
    no document management, no user data.
    """

    def get_selection(
        self, selection_type: Literal["objects", "materials"] = "objects"
    ) -> list[c4d.BaseObject | c4d.BaseMaterial]:
        """Return the currently selected objects or materials."""
        if selection_type == "objects":
            return self.source.GetActiveObjects(c4d.GETACTIVEOBJECTFLAGS_0)
        if selection_type == "materials":
            return self.source.GetActiveMaterials()
        return []

    def walk(
        self,
        obj: c4d.BaseObject | list[c4d.BaseObject] | None,
        fn: Callable[[c4d.BaseObject], None],
    ) -> None:
        """Call *fn* for every node in the hierarchy rooted at *obj*.

        Accepts a single object, a list of root objects, or None (no-op).
        Traversal order: pre-order (parent before children).
        """
        if obj is None:
            return

        if isinstance(obj, (list, tuple)):
            for o in obj:
                self.walk(o, fn)
            return

        fn(obj)
        child = obj.GetDown()
        while child:
            self.walk(child, fn)
            child = child.GetNext()

    def get_children(self, obj: c4d.BaseObject | list[c4d.BaseObject]) -> list[c4d.BaseObject]:
        """Return a flat list of *obj* and all its descendants."""
        result: list[c4d.BaseObject] = []
        self.walk(obj, result.append)
        return result

    def get_top_objects(self, doc: c4d.documents.BaseDocument) -> list[c4d.BaseObject]:
        """Return the direct children of the document root (no recursion)."""
        result: list[c4d.BaseObject] = []
        obj = doc.GetFirstObject()
        while obj:
            result.append(obj)
            obj = obj.GetNext()
        return result

    def get_all_objects(self, doc: c4d.documents.BaseDocument) -> list[c4d.BaseObject]:
        """Return every object in *doc* as a flat list."""
        result: list[c4d.BaseObject] = []
        self.walk(self.get_top_objects(doc), result.append)
        return result
