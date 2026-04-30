"""
Tree scene helpers for Jiko Bridge Blender plugin
Code by Semyon Shapoval, 2026
"""

import bpy


from ..jb_types import JbMaterial, JbObject
from ..jb_protocols import JbSceneABC


class JbSceneObjects(JbSceneABC):
    """Object operations for Scene."""

    def walk(self, root, fn) -> None:
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

    def get_objects(self, objects_type="all", root=None) -> list[JbObject]:
        ctx = self.source
        scene = ctx.scene
        if not scene:
            return []
        if objects_type == "all":
            if root:
                objects: list[JbObject] = []
                self.walk(root, objects.append)
                return objects

            return list(scene.objects)

        if objects_type == "top":
            col = root if isinstance(root, bpy.types.Collection) else scene.collection
            if not col:
                return []
            return list(col.objects)
        return []

    def get_selection(self, select_type="objects"):
        ctx = self.source
        view_layer = ctx.view_layer
        if view_layer is None:
            return []

        if select_type == "objects":
            objects = list(view_layer.objects.selected)
        elif select_type == "recursive":
            objects = list(view_layer.objects.selected)
            expanded = []
            self.walk(objects, expanded.append)
            objects = expanded
        elif select_type == "materials":
            return []

        return objects

    def get_materials_from_objects(self, objects) -> list[JbMaterial]:
        materials = set()
        for obj in objects:
            data = obj.data
            if data is None:
                continue
            for mat in getattr(data, "materials", ()):
                if mat is not None:
                    materials.add(mat)
        return list(materials)

    def set_object_transform(self, obj, matrix) -> None:
        obj.matrix_world = matrix
