from __future__ import annotations

from typing import Callable

import bpy

from .jb_scene_base import JBSceneBase


class JBTree(JBSceneBase):
    """Traversal and querying of Blender collection/object hierarchies.

    Implements the traversal group of JBSceneBase.
    Mirrors the C4D JBTree interface so that scene_manager code is symmetric.
    """

    def walk(
        self,
        collection: bpy.types.Collection,
        fn: Callable[[bpy.types.Object], None],
    ) -> None:
        """Call *fn* for every object in the collection hierarchy (pre-order)."""
        for obj in collection.objects:
            fn(obj)
        for child_col in collection.children:
            self.walk(child_col, fn)

    def get_children(self, collection: bpy.types.Collection) -> list:
        """Return a flat list of all objects in collection and sub-collections."""
        result: list = []
        self.walk(collection, result.append)
        return result

    def get_top_objects(self, scene: bpy.types.Scene) -> list:
        """Return direct objects of the scene root collection."""
        return list(scene.collection.objects)

    def get_all_objects(self, scene: bpy.types.Scene) -> list:
        """Return every object in the scene as a flat list."""
        return list(scene.objects)
