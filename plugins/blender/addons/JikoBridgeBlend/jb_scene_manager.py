import bpy
from contextlib import contextmanager
from typing import Optional

from .jb_asset_model import AssetModel
from .jb_scene_file_io import JBSceneFileIO
from .jb_logger import get_logger

# TODO: Port C4D scene utilities from plugins/c4d/jb_scene_manager.py
# - support recursive editable conversion / modifier application like C4D make_editable_recursive
# - preserve instance and placeholder cleanup semantics for nested hierarchies

logger = get_logger(__name__)

JB_ASSETS_COLLECTION = "Assets"


class JBSceneManager(JBSceneFileIO):
    """Manages objects, collections and instances in a Blender scene.

    Public API mirrors C4D's JBSceneManager so that jb_asset_importer and
    jb_asset_exporter contain DCC-agnostic code only.
    """

    # ------------------------------------------------------------------
    # Temp scene (analogous to temp_doc in C4D)
    # ------------------------------------------------------------------

    @contextmanager
    def temp_scene(self):
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
    def isolated_scene(self, objects: list, unit_scale: float = 1.0):
        """Create an isolated temp scene containing deep copies of *objects*.

        Analogous to C4D's ``isolated_doc`` / ``IsolateObjects``:
        - All objects are copied (``obj.copy()`` + ``obj.data.copy()``).
        - Parent–child relationships are reconstructed for pairs whose
          parent is present in *objects*.  Objects with external parents have
          their world transform baked so placement is preserved.
        - Materials are shared by reference (same IDs) — exporters include
          them automatically, no explicit copy needed.
        - All created data is freed on context exit.

        Usage::

            with self.isolated_scene(objects) as temp:
                ...
                self.file_exporter.export_file(ext)
        """
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
            # Remove all objects linked to the scene (includes any added during yield).
            for obj in list(scene.collection.all_objects):
                bpy.data.objects.remove(obj, do_unlink=True)
            for mesh in [m for m in bpy.data.meshes if m.users == 0]:
                bpy.data.meshes.remove(mesh)
            bpy.data.scenes.remove(scene)

    # ------------------------------------------------------------------
    # Asset container (collection) management
    # ------------------------------------------------------------------

    def get_or_create_root_collection(self) -> bpy.types.Collection:
        """Return or create the root JB_Assets collection."""
        col = bpy.data.collections.get(JB_ASSETS_COLLECTION)
        if not col:
            col = bpy.data.collections.new(JB_ASSETS_COLLECTION)
            bpy.context.scene.collection.children.link(col)
        return col

    def get_or_create_asset_container(
        self,
        asset: AssetModel,
        target=None,
    ) -> tuple:
        """Return (collection, existed).

        Unified API — mirrors C4D get_or_create_asset_container.
        If *target* is provided it is renamed/tagged instead of creating a new one.
        """
        root = self.get_or_create_root_collection()
        name = f"Asset_{asset.pack_name}_{asset.asset_name}"

        if target:
            col = target
            existed = col.name in bpy.data.collections
        else:
            col = bpy.data.collections.get(name)
            existed = col is not None
            if not col:
                col = bpy.data.collections.new(name)

        col.name = name
        self._set_asset_metadata(col, asset)

        if name not in [c.name for c in root.children]:
            try:
                root.children.link(col)
            except RuntimeError:
                pass

        if len(col.objects) == 0:
            existed = False

        return col, existed

    def get_asset_info(self, container) -> Optional[AssetModel]:
        """Unified API: read AssetModel from collection custom properties."""
        return AssetModel.from_collection(container)

    def _set_asset_metadata(self, col: bpy.types.Collection, asset: AssetModel) -> None:
        col["jb_pack_name"] = asset.pack_name or ""
        col["jb_asset_name"] = asset.asset_name or ""
        col["jb_asset_type"] = asset.asset_type or ""
        col["jb_database_name"] = asset.database_name or ""

    def clear_container(self, container) -> None:
        """Unified API: remove all objects from collection."""
        for obj in list(container.objects):
            container.objects.unlink(obj)
            bpy.data.objects.remove(obj, do_unlink=True)

    def cleanup_empty_objects(self, container) -> None:
        """Unified API: remove non-instance Empty objects from collection tree."""
        for obj in list(container.objects):
            if obj.type == "EMPTY" and obj.instance_type != "COLLECTION":
                bpy.data.objects.remove(obj, do_unlink=True)
        for child in container.children:
            self.cleanup_empty_objects(child)

    # ------------------------------------------------------------------
    # Object management
    # ------------------------------------------------------------------

    def get_objects_recursive(self, container) -> list:
        """Unified API: all objects in collection tree."""
        return self.get_children(container)

    def move_objects_to_container(self, objects: list, container) -> None:
        """Unified API: move objects into target collection."""
        for obj in objects:
            for col in list(obj.users_collection):
                col.objects.unlink(obj)
            container.objects.link(obj)

    # ------------------------------------------------------------------
    # File import / export
    # ------------------------------------------------------------------

    def import_file_to_container(self, file_path: str, container) -> None:
        """Unified API: import file and place objects into collection."""
        objects = self.import_file(file_path)
        if not objects:
            logger.warning("No objects imported for file: %s", file_path)
            return
        self.move_objects_to_container(objects, container)

    def export_to_temp_file(self, objects: list, ext: str) -> Optional[str]:
        """Unified API: copy objects to isolated scene, replace instances, export."""
        with self.isolated_scene(objects) as temp:
            copies = list(temp.collection.objects)
            self._replace_instances_with_placeholders(copies, temp)
            return self.export_file(ext)
