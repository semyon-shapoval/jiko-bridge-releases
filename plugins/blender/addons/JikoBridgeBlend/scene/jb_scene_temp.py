from typing import Generator

import bpy
from contextlib import contextmanager

from .jb_scene_file_io import JBSceneFileIO
from ..src.jb_logger import get_logger


logger = get_logger(__name__)


class JBSceneTemp(JBSceneFileIO):
    """Scene-level operations: temporary scene contexts.

    TODO: Port C4D scene utilities:
    - project_scale / geometry scale transforms
    - make_editable_recursive (apply modifiers / convert to mesh)
    """

    # ------------------------------------------------------------------
    # Temporary scene contexts
    # ------------------------------------------------------------------
    @contextmanager
    def temp_scene(
        self,
        src: bpy.types.Collection | list[bpy.types.Object] = None,
        unit_scale: float = 1.0,
        debug: bool = False,
    ) -> Generator[bpy.types.Scene, None, None]:
        # Создаем сцену
        temp: bpy.types.Scene = bpy.data.scenes.new("_jb_temp_scene")
        temp.unit_settings.system = "METRIC"
        temp.unit_settings.scale_length = unit_scale

        new_objects: list[bpy.types.Object] = []
        override_context: dict = {}
        depsgraph = None

        window = None
        area = None
        old_window_scene = None
        old_area_scenes: dict[bpy.types.Space, bpy.types.Scene] = {}

        try:
            override_context = self._make_temp_scene_context(temp)
            window = override_context.get("window")
            area = override_context.get("area")

            if window is not None:
                old_window_scene = window.scene
                window.scene = temp

            if area is not None and hasattr(area, "spaces"):
                for space in area.spaces:
                    try:
                        old_area_scenes[space] = space.scene
                        space.scene = temp
                    except Exception:
                        pass

            with bpy.context.temp_override(**override_context):
                view_layer = temp.view_layers[0]
                if src:
                    new_objects = self.copy_recursive(src, temp.collection)

                depsgraph = getattr(view_layer, "depsgraph", None)
                if depsgraph is None:
                    depsgraph = bpy.context.evaluated_depsgraph_get()
                if depsgraph is not None:
                    override_context["depsgraph"] = depsgraph

                with bpy.context.temp_override(**override_context):
                    if depsgraph is not None:
                        depsgraph.update()
                    else:
                        view_layer.update()

                    yield temp
        finally:
            if not debug:
                try:
                    if window is not None and old_window_scene is not None:
                        window.scene = old_window_scene

                    if area is not None:
                        for space, old_scene in old_area_scenes.items():
                            try:
                                space.scene = old_scene
                            except Exception:
                                pass

                    if override_context:
                        with bpy.context.temp_override(**override_context):
                            if depsgraph is not None:
                                depsgraph.update()
                            else:
                                temp.view_layers[0].update()

                    if len(new_objects) > 0:
                        for obj in list(new_objects):
                            obj.use_fake_user = False

                        for obj in list(new_objects):
                            data = obj.data
                            bpy.data.objects.remove(obj, do_unlink=True)
                            if data is not None and data.users == 0:
                                try:
                                    bpy.data.meshes.remove(data)
                                except Exception:
                                    pass

                    bpy.data.scenes.remove(temp)
                    bpy.data.orphans_purge(do_recursive=True)
                except Exception as e:
                    logger.error(
                        "Failed to cleanup temp scene '%s': %s",
                        getattr(temp, "name", "<unknown>"),
                        e,
                    )
            else:
                logger.debug(
                    "Debug mode: keeping temp scene '%s' with %d objects",
                    temp.name,
                    len(new_objects),
                )

    def _make_temp_scene_context(self, scene: bpy.types.Scene) -> dict:
        """Build a valid Blender override context for temp scene operations."""
        view_layer: bpy.types.ViewLayer = scene.view_layers[0]
        context = {
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
        except Exception:
            return context

        if wm is None:
            return context

        context["window_manager"] = wm
        try:
            window = wm.windows[0] if len(wm.windows) > 0 else None
        except Exception:
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
            region = next(
                (r for r in area.regions if r.type == "WINDOW"), area.regions[0]
            )
            if region is not None:
                context["region"] = region

        try:
            workspace = window.workspace
        except Exception:
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
        objects = (
            list(src.all_objects) if isinstance(src, bpy.types.Collection) else src
        )

        object_set = set(objects)
        roots = [
            obj for obj in objects if obj.parent is None or obj.parent not in object_set
        ]

        new_objects: list[bpy.types.Object] = []

        def copy_tree(obj: bpy.types.Object, parent: bpy.types.Object | None = None):
            new_obj = obj.copy()
            if new_obj.data is not None:
                try:
                    new_obj.data = obj.data.copy()
                except Exception as e:
                    logger.warning(
                        "Failed to copy data for object '%s': %s", obj.name, e
                    )

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
