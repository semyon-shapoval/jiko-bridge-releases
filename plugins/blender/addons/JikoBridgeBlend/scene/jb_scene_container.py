import bpy
from contextlib import contextmanager

from .jb_scene_file_io import JBSceneFileIO


class JBSceneContainer(JBSceneFileIO):
    """Scene-level operations: temporary scene contexts.

    TODO: Port C4D scene utilities:
    - project_scale / geometry scale transforms
    - make_editable_recursive (apply modifiers / convert to mesh)
    """

    # ------------------------------------------------------------------
    # Temporary scene contexts
    # ------------------------------------------------------------------

    @contextmanager
    def temp_container(self):
        """Create a temporary Blender scene for export preparation.

        Deleted (with all its objects/meshes) on context exit.
        """
        temp: bpy.types.Scene = bpy.data.scenes.new("_jb_temp_export")
        temp.unit_settings.system = "METRIC"
        temp.unit_settings.scale_length = 1.0
        window = bpy.context.window_manager.windows[0]
        view_layer = temp.view_layers[0]
        try:
            with bpy.context.temp_override(
                window=window, scene=temp, view_layer=view_layer
            ):
                yield temp
        finally:
            for obj in list(temp.collection.all_objects):
                bpy.data.objects.remove(obj, do_unlink=True)
            for mesh in [m for m in bpy.data.meshes if m.users == 0]:
                bpy.data.meshes.remove(mesh)
            bpy.data.scenes.remove(temp)

    @contextmanager
    def isolated_container(
        self, objects: list[bpy.types.Object], unit_scale: float = 1.0
    ):
        """Create an isolated temp scene containing deep copies of *objects*."""
        scene: bpy.types.Scene = bpy.data.scenes.new("_jb_isolated")
        scene.unit_settings.system = "METRIC"
        scene.unit_settings.scale_length = unit_scale

        objects_set = set(objects)
        original_to_copy: dict = {}

        # Pass 1: create shallow copies and register in the temp scene.
        for orig in objects:
            copy = orig.copy()
            if orig.data:
                copy.data = orig.data.copy()
            scene.collection.objects.link(copy)
            original_to_copy[orig] = copy

        # Pass 2: restore parent hierarchy inside the copied set.
        for orig, copy in original_to_copy.items():
            if orig.parent in objects_set:
                copy.parent = original_to_copy[orig.parent]
                copy.matrix_parent_inverse = orig.matrix_parent_inverse.copy()
            else:
                # Parent is outside the set — detach and bake world transform.
                copy.parent = None
                copy.matrix_world = orig.matrix_world.copy()

        try:
            yield scene
        finally:
            for obj in list(scene.collection.all_objects):
                bpy.data.objects.remove(obj, do_unlink=True)
            for mesh in [m for m in bpy.data.meshes if m.users == 0]:
                bpy.data.meshes.remove(mesh)
            bpy.data.scenes.remove(scene)
