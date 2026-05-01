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

        try:
            with ctx.temp_override(scene=temp):
                col = temp.collection
                if objects is not None and col is not None:
                    self._copy_source(objects, col)
                yield temp
        finally:
            if not debug:
                try:
                    if temp.name in bpy.data.scenes:
                        bpy.data.scenes.remove(temp, do_unlink=True)
                        bpy.data.orphans_purge(do_recursive=True)
                except RuntimeError:
                    pass

    def _copy_source(
        self,
        src: bpy.types.Collection | list[bpy.types.Object],
        dst: bpy.types.Collection,
    ) -> None:
        orig_to_new: dict[bpy.types.Object, bpy.types.Object] = {}

        objects = self.get_objects(src)

        for obj in reversed(objects):
            new_obj = obj.copy()
            dst.objects.link(new_obj)
            if obj.parent and obj.parent in orig_to_new:
                new_obj.parent = orig_to_new[obj.parent]
                new_obj.parent_type = obj.parent_type
                new_obj.parent_bone = obj.parent_bone
                new_obj.matrix_parent_inverse = obj.matrix_parent_inverse.copy()
            orig_to_new[obj] = new_obj
