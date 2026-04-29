"""
Instance managament and placeholder extraction for Blender.
Code by Semyon Shapoval, 2026
"""

from __future__ import annotations

import bpy
import bmesh
from ..jb_types import AssetInfo
from .jb_scene_container import JbSceneContainer
from ..jb_utils import get_logger

logger = get_logger(__name__)


class JBSceneInstance(JbSceneContainer):
    """Instance and placeholder management for Blender."""

    def create_instance(self, asset_container: bpy.types.Collection, name: str) -> bpy.types.Object:
        """Creates an instance of the given asset collection."""
        empty = bpy.data.objects.new(f"Instance_{name}", None)
        empty.instance_type = "COLLECTION"
        empty.instance_collection = asset_container
        empty["jb_pack_name"] = asset_container.get("jb_pack_name", "")
        empty["jb_asset_name"] = asset_container.get("jb_asset_name", "")
        empty["jb_asset_type"] = asset_container.get("jb_asset_type", "")
        empty["jb_database_name"] = asset_container.get("jb_database_name", "")
        scene = self.source().scene
        if scene is not None and scene.collection is not None:
            scene.collection.objects.link(empty)
        return empty


    def add_instance_to_container(
        self, instance: bpy.types.Object, container: bpy.types.Collection
    ) -> None:
        """Adds the instance to the asset container collection."""
        scene = self.source().scene
        if scene is not None and scene.collection is not None:
            try:
                scene.collection.objects.unlink(instance)
            except RuntimeError:
                pass
        container.objects.link(instance)

    def extract_placeholders(self, container: bpy.types.Collection) -> list[dict]:
        """Extracts placeholder objects from the container and returns their info."""
        result = []
        for obj in list(container.objects):
            if obj.type != "MESH" or not obj.data or len(obj.data.vertices) != 4:
                continue

            pack = obj.get("jb_placeholder_pack")
            asset = obj.get("jb_placeholder_asset")

            if not (pack and asset):
                mat_name = (
                    next((m.name for m in obj.data.materials if m), None)
                    if obj.data and hasattr(obj.data, "materials")
                    else None
                )
                info = AssetInfo.from_string(mat_name or obj.name)
                if not info:
                    continue
                pack = info.pack_name
                asset = info.asset_name

            result.append(
                {
                    "packName": pack,
                    "assetName": asset,
                    "matrix": obj.matrix_world.copy(),
                }
            )
            container.objects.unlink(obj)
            bpy.data.objects.remove(obj, do_unlink=True)

        return result

    def _replace_instances_with_placeholders(
        self, objects: list[bpy.types.Object], scene: bpy.types.Scene
    ) -> list[bpy.types.Object]:
        result = []
        for obj in objects:
            if obj.instance_type == "COLLECTION" and obj.instance_collection:
                info = self.get_asset_from_user_data(obj.instance_collection)
                if info and info.pack_name and info.asset_name:
                    placeholder = self._create_placeholder(
                        info.pack_name, info.asset_name, obj.matrix_world.copy(), scene
                    )
                    col = scene.collection
                    if col is not None:
                        col.objects.unlink(obj)
                    bpy.data.objects.remove(obj, do_unlink=True)
                    result.append(placeholder)
                    continue
            result.append(obj)
        return result

    def _create_placeholder(
        self,
        pack_name: str,
        asset_name: str,
        matrix_world,
        scene: bpy.types.Scene,
    ) -> bpy.types.Object:
        mesh = bpy.data.meshes.new(f"{pack_name}__{asset_name}")
        bm = bmesh.new()
        bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=0.5)
        bm.to_mesh(mesh)
        bm.free()
        obj = bpy.data.objects.new(f"{pack_name}__{asset_name}", mesh)
        obj["jb_placeholder_pack"] = pack_name
        obj["jb_placeholder_asset"] = asset_name
        obj.matrix_world = matrix_world
        col = scene.collection
        if col is not None:
            col.objects.link(obj)
        return obj
