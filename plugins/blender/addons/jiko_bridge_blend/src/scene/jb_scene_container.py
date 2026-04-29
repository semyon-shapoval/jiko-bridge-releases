"""
Scene container management for Blender
Code by Semyon Shapoval, 2026
"""

from typing import Optional

import bpy

from ..jb_types import AssetFile, AssetModel, AssetInfo, JbContainer
from .jb_scene_objects import JbSceneObjects

JB_ASSETS_COLLECTION = "Assets"
COLOR_TAG = "COLOR_04"


class JbSceneContainer(JbSceneObjects):
    """Container and asset management: collections, metadata."""

    def get_or_create_container(
        self, col_name: str, parent: bpy.types.Collection | None = None
    ) -> JbContainer:
        """Return or create the root JB_Assets collection."""
        ctx = self.source()
        col = bpy.data.collections.get(col_name)
        if not col:
            col = bpy.data.collections.new(col_name)
            if parent is not None:
                parent.children.link(col)
            else:
                scene = ctx.scene
                if scene:
                    root_col = scene.collection
                    if root_col is not None:
                        root_col.children.link(col)

            col.color_tag = COLOR_TAG

        return col

    def get_or_create_asset_container(
        self,
        asset: AssetModel,
        file: AssetFile | None = None,
    ) -> tuple[JbContainer, bool]:
        """Return (collection, existed). Mirrors C4D get_or_create_asset_container."""
        root = self.get_or_create_container("Assets")
        name = f"Asset_{asset.pack_name}_{asset.asset_name}"

        col = self.get_or_create_container(name, parent=root)
        self._set_user_data(col, asset, file)

        if name not in [c.name for c in root.children]:
            try:
                root.children.link(col)
            except RuntimeError:
                pass

        existed = True
        if len(col.objects) == 0:
            existed = False

        return col, existed

    def filter_containers_from_objects(self, objects: list[bpy.types.Object]) -> list[JbContainer]:
        """Return asset containers found among the given objects (via instance Empties)."""
        containers: list[JbContainer] = []
        seen: set = set()
        for obj in objects:
            if obj.instance_type == "COLLECTION" and obj.instance_collection:
                col = obj.instance_collection
                if id(col) not in seen and self.get_asset_from_user_data(col):
                    seen.add(id(col))
                    containers.append(col)
        return containers

    def _set_user_data(
        self, col: JbContainer, asset: AssetModel, file: AssetFile | None = None
    ) -> None:
        col["jb_pack_name"] = asset.pack_name or ""
        col["jb_asset_name"] = asset.asset_name or ""
        col["jb_asset_type"] = file.asset_type or "" if file else ""
        col["jb_database_name"] = asset.database_name or ""

    def get_asset_from_user_data(self, container: JbContainer) -> Optional[AssetInfo]:
        """Parse asset info from a container's user data."""
        pack_name = container.get("jb_pack_name", None)
        asset_name = container.get("jb_asset_name", None)
        asset_type = container.get("jb_asset_type", None)
        database_name = container.get("jb_database_name", None)
        if not (pack_name and asset_name):
            return None
        return AssetInfo(
            pack_name=pack_name,
            asset_name=asset_name,
            asset_type=asset_type,
            database_name=database_name,
        )

    def clear_container(self, container: JbContainer) -> None:
        """Remove all objects from collection."""
        for obj in list(container.objects):
            container.objects.unlink(obj)
            bpy.data.objects.remove(obj, do_unlink=True)

    def cleanup_empty_objects(self, container: JbContainer) -> None:
        """Remove non-instance Empty objects from collection tree."""
        for obj in list(container.objects):
            if obj.type == "EMPTY" and obj.instance_type != "COLLECTION":
                bpy.data.objects.remove(obj, do_unlink=True)
        for child in container.children:
            self.cleanup_empty_objects(child)

    def move_objects_to_container(self, objects: list, container: JbContainer) -> None:
        """Move objects into target collection."""
        for obj in objects:
            for col in list(obj.users_collection):
                col.objects.unlink(obj)
            container.objects.link(obj)
