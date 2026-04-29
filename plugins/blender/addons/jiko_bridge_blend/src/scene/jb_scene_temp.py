"""
Temporary scene helpers for Jiko Bridge Blender plugin
Code by Semyon Shapoval, 2026
"""

from typing import Any, Generator, Optional
from contextlib import contextmanager

import bpy
from .jb_scene_file import JBSceneFile
from ..jb_utils import get_logger


logger = get_logger(__name__)


class JBSceneTemp(JBSceneFile):
    """Scene-level operations: temporary scene contexts."""

    # ------------------------------------------------------------------
    # Temporary scene contexts
    # ------------------------------------------------------------------
    @contextmanager
    def temp_scene(
        self,
        src: Optional[bpy.types.Collection | list[bpy.types.Object]] = None,
        unit_scale: float = 1.0,
        debug: bool = False,
    ) -> Generator[bpy.types.Scene, None, None]:
        """Context manager for temporary scenes."""
        temp: bpy.types.Scene = bpy.data.scenes.new("_jb_temp_scene")
        settings = temp.unit_settings
        if settings is not None:
            settings.system = "METRIC"
            settings.scale_length = unit_scale

        new_objects: list[bpy.types.Object] = []
        try:
            ctx = self._make_temp_scene_context(temp)
            with bpy.context.temp_override(**ctx):
                view_layer = temp.view_layers[0]
                col = temp.collection
                if src is not None and col is not None:
                    new_objects = self.copy_recursive(src, col)
                view_layer.update()
                yield temp
        finally:
            if not debug:
                self._cleanup_temp_scene(temp, new_objects)
            else:
                logger.debug("Debug: temp scene '%s', %d objects", temp.name, len(new_objects))

    def _cleanup_temp_scene(
        self,
        temp: bpy.types.Scene,
        objects: list[bpy.types.Object],
    ) -> None:
        """Remove temp scene and all copied objects."""
        try:
            for obj in list(objects):
                obj.use_fake_user = False
            for obj in list(objects):
                data = obj.data
                bpy.data.objects.remove(obj, do_unlink=True)
                if data is not None and data.users == 0:
                    try:
                        bpy.data.meshes.remove(data)
                    except RuntimeError as exc:
                        logger.warning("Mesh cleanup failed: %s", exc)
            bpy.data.scenes.remove(temp)
            bpy.data.orphans_purge()
        except RuntimeError as exc:
            logger.error("Cleanup failed '%s': %s", getattr(temp, "name", ""), exc)

    def _make_temp_scene_context(self, scene: bpy.types.Scene) -> dict:
        """Build a valid Blender override context for temp scene operations."""
        view_layer: bpy.types.ViewLayer = scene.view_layers[0]
        context: dict[str, Any] = {
            "scene": scene,
            "view_layer": view_layer,
            "collection": scene.collection,
            "layer_collection": view_layer.layer_collection,
            "active_layer_collection": view_layer.active_layer_collection,
            "active_object": None,
            "selected_objects": [],
            "active_base": None,
            "selected_editable_bases": [],
        }

        depsgraph = getattr(view_layer, "depsgraph", None)
        if depsgraph is not None:
            context["depsgraph"] = depsgraph

        try:
            wm = bpy.context.window_manager
        except RuntimeError:
            return context

        if wm is None:
            return context

        context["window_manager"] = wm
        try:
            window = wm.windows[0] if len(wm.windows) > 0 else None
        except RuntimeError:
            window = None

        if window is None:
            return context

        context["window"] = window
        screen = window.screen
        if screen is None or len(screen.areas) == 0:
            return context

        area = next((a for a in screen.areas if a.type == "VIEW_3D"), screen.areas[0])
        if area is not None:
            context["area"] = area
            region = next((r for r in area.regions if r.type == "WINDOW"), area.regions[0])
            if region is not None:
                context["region"] = region

        try:
            workspace = window.workspace
        except RuntimeError:
            workspace = None

        if workspace is not None:
            context["workspace"] = workspace

        return context

    def copy_recursive(
        self,
        src: bpy.types.Collection | list[bpy.types.Object],
        dst: bpy.types.Collection,
    ) -> list[bpy.types.Object]:
        """Copy imported objects from a collection or object list into the destination."""
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
                    logger.warning("Failed to copy data for object '%s': %s", obj.name, e)

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
