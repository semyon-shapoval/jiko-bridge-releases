import bpy
from typing import Optional

from ..jb_asset_model import AssetModel
from .jb_scene_temp import JBSceneTemp


JB_ASSETS_COLLECTION = "Assets"
COLOR_TAG = 'COLOR_04'


class JBSceneContainer(JBSceneTemp):
    """Container and asset management: collections, metadata."""

    # ------------------------------------------------------------------
    # Root collection
    # ------------------------------------------------------------------

    def get_or_create_root_collection(self) -> bpy.types.Collection:
        """Return or create the root JB_Assets collection."""
        col = bpy.data.collections.get(JB_ASSETS_COLLECTION)
        if not col:
            col = bpy.data.collections.new(JB_ASSETS_COLLECTION)
            bpy.context.scene.collection.children.link(col)
            col.color_tag = COLOR_TAG

        return col

    # ------------------------------------------------------------------
    # Asset metadata
    # ------------------------------------------------------------------

    def _set_asset_metadata(self, col: bpy.types.Collection, asset: AssetModel) -> None:
        col["jb_pack_name"] = asset.pack_name or ""
        col["jb_asset_name"] = asset.asset_name or ""
        col["jb_asset_type"] = asset.asset_type or ""
        col["jb_database_name"] = asset.database_name or ""

    # ------------------------------------------------------------------
    # Unified API
    # ------------------------------------------------------------------

    def get_or_create_container(
        self,
        asset: AssetModel,
        target: bpy.types.Collection = None,
    ) -> tuple[bpy.types.Collection, bool]:
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
        col.color_tag = COLOR_TAG
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

    def get_objects_recursive(self, container) -> list:
        """Unified API: all objects in collection tree."""
        return self.get_children(container)

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

    def move_objects_to_container(self, objects: list, container) -> None:
        """Unified API: move objects into target collection."""
        for obj in objects:
            for col in list(obj.users_collection):
                col.objects.unlink(obj)
            container.objects.link(obj)
