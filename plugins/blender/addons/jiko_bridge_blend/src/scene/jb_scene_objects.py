"""
Tree scene helpers for Jiko Bridge Blender plugin
Code by Semyon Shapoval, 2026
"""

from typing import Optional

import bpy


from ..jb_types import JbMaterial, JbObject, JbContainer
from ..jb_protocols import JbSceneABC


class JbSceneObjects(JbSceneABC):
    """Object operations for Scene."""

    @property
    def _outliner(self) -> Optional[tuple[bpy.types.Area, bpy.types.Region]]:
        ctx = self.source
        if not ctx.screen:
            return None
        for area in ctx.screen.areas:
            if area.type == "OUTLINER":
                for region in area.regions:
                    if region.type == "WINDOW":
                        return area, region
        return None

    def walk(self, root):
        seen = set()

        def walk_object(obj: bpy.types.Object):
            if obj in seen:
                return
            seen.add(obj)
            yield obj
            for child in obj.children:
                yield from walk_object(child)

        if isinstance(root, bpy.types.Collection):
            for obj in root.objects:
                yield from walk_object(obj)
            for child_col in root.children:
                yield from self.walk(child_col)
            return

        if isinstance(root, (list, tuple)):
            for obj in root:
                yield from walk_object(obj)
            return

        yield from walk_object(root)

    def get_objects(self, root=None, mode="all") -> list[JbObject]:
        ctx = self.source
        scene = ctx.scene
        if not scene:
            return []
        if mode == "all":
            if root:
                return list(self.walk(root))

            return list(scene.objects)

        if mode == "top":
            col = root if isinstance(root, bpy.types.Collection) else scene.collection
            if not col:
                return []
            top_objects = set(col.objects)
            return [
                obj for obj in col.objects if obj.parent is None or obj.parent not in top_objects
            ]
        return []

    def get_selection(self, select_type="objects") -> list[JbContainer | JbObject | JbMaterial]:
        ctx = self.source
        objects: list[JbContainer | JbObject | JbMaterial] = []

        if select_type in ("objects", "recursive"):
            outliner = self._outliner
            if outliner:
                area, region = outliner
                with ctx.temp_override(area=area, region=region):
                    selected = ctx.selected_ids
                    if selected:
                        for item in selected:
                            if isinstance(
                                item, (bpy.types.Object, bpy.types.Collection, bpy.types.Material)
                            ):
                                objects.append(item)
            else:
                if not (view_layer := ctx.view_layer):
                    return []
                objects = list(view_layer.objects.selected)  # type: ignore[assignment]

            if objects and select_type == "recursive":
                objects = list(self.walk(objects))

        return objects

    def get_materials_from_objects(self, objects) -> list[JbMaterial]:
        materials: set[JbMaterial] = set()
        for obj in objects:
            if isinstance(obj, bpy.types.Material):
                materials.add(obj)
                continue
            if not isinstance(obj, bpy.types.Object):
                continue
            if (data := obj.data) is None:
                continue
            materials.update(mat for mat in getattr(data, "materials", ()) if mat is not None)
        return list(materials)

    def set_object_transform(self, obj, matrix) -> None:
        if not isinstance(obj, bpy.types.Object):
            return
        obj.matrix_world = matrix

    def remove_object(self, obj) -> None:
        bpy.data.objects.remove(obj, do_unlink=True)
