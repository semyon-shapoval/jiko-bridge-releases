"""
Temporary scene helpers for Jiko Bridge Blender plugin
Code by Semyon Shapoval, 2026
"""

from contextlib import contextmanager

import bpy

from .jb_scene_file import JbSceneFile


class JBSceneTemp(JbSceneFile):
    """Scene-level operations: temporary scene contexts."""

    @contextmanager
    def temp_source(self, objects=None, unit_scale=1.0, debug=False):
        ctx = self.source
        temp = bpy.data.scenes.new("_jb_temp_scene")

        if not isinstance(temp, bpy.types.Scene):
            raise TypeError("temp must be a Scene")

        settings = temp.unit_settings
        if settings is not None:
            settings.system = "METRIC"
            settings.scale_length = unit_scale

        new_objects = []
        try:
            with ctx.temp_override(scene=temp):
                col = temp.collection
                if objects is not None and col is not None:
                    new_objects = self._copy_source(objects, col)
                yield temp
        finally:
            if not debug:
                self._cleanup_temp_scene(temp, new_objects)
            else:
                self.logger.debug("Debug: temp scene '%s', %d objects", temp.name, len(new_objects))

    def _cleanup_temp_scene(self, temp, objects) -> None:
        for obj in objects:
            try:
                if obj.name in bpy.data.objects:
                    bpy.data.objects.remove(obj, do_unlink=True)
            except ReferenceError:
                continue

        try:
            if temp.name in bpy.data.scenes:
                bpy.data.scenes.remove(temp, do_unlink=True)
        except RuntimeError:
            pass

    def _copy_source(
        self,
        src: bpy.types.Collection | list[bpy.types.Object],
        dst: bpy.types.Collection,
    ) -> list[bpy.types.Object]:
        objects = list(src.all_objects) if isinstance(src, bpy.types.Collection) else src

        object_set = set(objects)
        roots = [obj for obj in objects if obj.parent is None or obj.parent not in object_set]

        new_objects: list[bpy.types.Object] = []

        def copy_tree(obj: bpy.types.Object, parent: bpy.types.Object | None = None):
            new_obj = obj.copy()
            if new_obj.data is not None:
                try:
                    data = obj.data
                    if data is not None:
                        new_obj.data = data.copy()
                except RuntimeError as e:
                    self.logger.warning("Failed to copy data for object '%s': %s", obj.name, e)

            dst.objects.link(new_obj)
            if parent is not None:
                new_obj.parent = parent
                new_obj.parent_type = obj.parent_type
                new_obj.parent_bone = obj.parent_bone
                new_obj.matrix_parent_inverse = obj.matrix_parent_inverse.copy()

            new_objects.append(new_obj)

            for child in obj.children:
                if child in object_set:
                    copy_tree(child, new_obj)

        for root in roots:
            copy_tree(root)

        return new_objects
