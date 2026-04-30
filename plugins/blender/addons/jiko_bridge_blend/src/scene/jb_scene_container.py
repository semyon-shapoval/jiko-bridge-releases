"""
Scene container management for Blender
Code by Semyon Shapoval, 2026
"""

from typing import Optional

import bpy


from .jb_scene_objects import JbSceneObjects
from ..jb_types import AssetInfo, JbContainer


class JbSceneContainer(JbSceneObjects):
    """Container and asset management: collections, metadata."""

    def get_or_create_container(self, name, parent=None) -> JbContainer:
        ctx = self.source
        col = bpy.data.collections.get(name)
        if not col:
            col = bpy.data.collections.new(name)
            if parent is not None:
                parent.children.link(col)
            else:
                scene = ctx.scene
                if scene:
                    root_col = scene.collection
                    if root_col is not None:
                        root_col.children.link(col)

            col.color_tag = "COLOR_04"

        return col

    def get_or_create_asset_container(self, asset, file=None) -> tuple[JbContainer, bool]:
        root = self.get_or_create_container("Assets")
        name = f"Asset_{asset.pack_name}_{asset.asset_name}"

        col = self.get_or_create_container(name, parent=root)
        self.set_asset_data(col, asset, file)

        if name not in [c.name for c in root.children]:
            try:
                root.children.link(col)
            except RuntimeError:
                pass

        existed = True
        if len(col.objects) == 0:
            existed = False

        return col, existed

    def filter_containers_from_objects(self, objects) -> list[JbContainer]:
        containers: list[JbContainer] = []
        seen: set = set()
        for obj in objects:
            if obj.instance_type == "COLLECTION" and obj.instance_collection:
                col = obj.instance_collection
                if id(col) not in seen and self.get_asset_data_from_container(col):
                    seen.add(id(col))
                    containers.append(col)
        return containers

    def set_asset_data(self, col, asset, file=None) -> None:
        col["jb_pack_name"] = asset.pack_name or ""
        col["jb_asset_name"] = asset.asset_name or ""
        col["jb_asset_type"] = file.asset_type or "" if file else ""
        col["jb_database_name"] = asset.database_name or ""

    def get_asset_data_from_container(self, container) -> Optional[AssetInfo]:
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

    def copy_asset_data(self, src, dst) -> None:
        for key in ("jb_pack_name", "jb_asset_name", "jb_asset_type", "jb_database_name"):
            if key in src:
                dst[key] = src[key]

    def clear_container(self, container) -> None:
        for obj in list(container.objects):
            container.objects.unlink(obj)
            bpy.data.objects.remove(obj, do_unlink=True)

    def cleanup_empty_objects(self, container) -> None:
        for obj in list(container.objects):
            if obj.type == "EMPTY" and obj.instance_type != "COLLECTION":
                bpy.data.objects.remove(obj, do_unlink=True)
        for child in container.children:
            self.cleanup_empty_objects(child)

    def move_objects_to_container(self, objects, container) -> None:
        for obj in objects:
            for col in list(obj.users_collection):
                col.objects.unlink(obj)
            container.objects.link(obj)
