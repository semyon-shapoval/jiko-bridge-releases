"""
Tree scene helpers for Jiko Bridge Blender plugin
Code by Semyon Shapoval, 2026
"""

from typing import Callable, Literal

import bpy

from .jb_scene_base import JbSceneBase


class JbSceneObjects(JbSceneBase):
    """Traversal and querying of Blender collection/object hierarchies.

    Implements the traversal group of JBSceneBase.
    Mirrors the C4D JBTree interface so that scene_manager code is symmetric.
    """

    def walk(
        self,
        root: bpy.types.Collection | bpy.types.Object | list[bpy.types.Object],
        fn: Callable[[bpy.types.Object], None],
    ) -> None:
        """Call *fn* for every object in the root hierarchy (pre-order)."""
        seen = set()

        def walk_object(obj: bpy.types.Object) -> None:
            if obj in seen:
                return
            seen.add(obj)
            fn(obj)
            for child in obj.children:
                walk_object(child)

        if isinstance(root, bpy.types.Collection):
            for obj in root.objects:
                walk_object(obj)
            for child_col in root.children:
                self.walk(child_col, fn)
            return

        if isinstance(root, (list, tuple)):
            for obj in root:
                self.walk(obj, fn)
            return

        walk_object(root)

    def get_objects(
        self,
        objects_type: Literal["all", "top"] = "all",
        root: bpy.types.Collection | bpy.types.Object | list[bpy.types.Object] | None = None,
    ) -> list:
        """Return objects of the active scene, either all or top-level."""
        ctx = self.source()
        scene = ctx.scene
        if not scene:
            return []
        if objects_type == "all":
            if root:
                objects: list[bpy.types.Object] = []
                self.walk(root, objects.append)
                return objects

            return list(scene.objects)

        if objects_type == "top":
            col = root if isinstance(root, bpy.types.Collection) else scene.collection
            if not col:
                return []
            return list(col.objects)
        return []

    def get_selection(
        self, select_type: Literal["objects", "recursive", "materials"] = "objects"
    ) -> list:
        """Return the currently selected objects or materials."""
        ctx = self.source()
        view_layer = ctx.view_layer
        if view_layer is None:
            return []

        if select_type == "objects":
            objects = list(view_layer.objects.selected)
        elif select_type == "recursive":
            objects = list(view_layer.objects.selected)
            expanded: list[bpy.types.Object] = []
            self.walk(objects, expanded.append)
            objects = expanded
        elif select_type == "materials":
            pass

        return objects

    def get_materials_from_objects(
        self, objects: list[bpy.types.Object]
    ) -> list[bpy.types.Material]:
        """Extract materials from objects and their material slots."""
        materials = set()
        for obj in objects:
            data = obj.data
            if data is None:
                continue
            for mat in getattr(data, "materials", ()):
                if mat is not None:
                    materials.add(mat)
        return list(materials)

    def set_object_transform(self, obj: bpy.types.Object, matrix) -> None:
        """Sets the world transform of the instance."""
        obj.matrix_world = matrix
