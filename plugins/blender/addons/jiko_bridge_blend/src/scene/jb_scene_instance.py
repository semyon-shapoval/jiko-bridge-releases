"""
Instance managament and placeholder extraction for Blender.
Code by Semyon Shapoval, 2026
"""

from __future__ import annotations

import bpy
import bmesh
from ..jb_types import AssetInfo, JbObject
from .jb_scene_container import JbSceneContainer
from ..jb_protocols import JbPlaceholderInfo


class JbSceneInstance(JbSceneContainer):
    """Instance and placeholder management for Blender."""

    def create_instance(self, container, name) -> bpy.types.Object:
        empty = bpy.data.objects.new(f"Instance_{name}", None)
        empty.instance_type = "COLLECTION"
        empty.instance_collection = container
        empty["jb_pack_name"] = container.get("jb_pack_name", "")
        empty["jb_asset_name"] = container.get("jb_asset_name", "")
        empty["jb_asset_type"] = container.get("jb_asset_type", "")
        empty["jb_database_name"] = container.get("jb_database_name", "")
        scene = self.source.scene
        if scene is not None and scene.collection is not None:
            scene.collection.objects.link(empty)
        return empty

    def add_instance_to_container(self, instance, container) -> None:
        """Adds the instance to the asset container collection."""
        scene = self.source.scene
        if scene is not None and scene.collection is not None:
            try:
                scene.collection.objects.unlink(instance)
            except RuntimeError:
                pass
        container.objects.link(instance)

    def extract_placeholders(self, container) -> list[JbPlaceholderInfo]:
        """Extracts placeholder objects from the container and returns their info."""
        result = []
        for obj in list(container.objects):
            if not isinstance(obj, bpy.types.Object):
                continue

            data = obj.data
            if data is None or not isinstance(data, bpy.types.Mesh) or len(data.vertices) != 4:
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
                JbPlaceholderInfo(
                    pack=pack,
                    asset=asset,
                    transform=obj.matrix_world.copy(),
                )
            )
            container.objects.unlink(obj)
            bpy.data.objects.remove(obj, do_unlink=True)

        return result

    def replace_instances_with_placeholders(self, objects, scene) -> list[JbObject]:
        result = []
        for obj in objects:
            if obj.instance_type == "COLLECTION" and obj.instance_collection:
                info = self.get_asset_data_from_container(obj.instance_collection)
                if info and info.pack_name and info.asset_name:
                    placeholder = self.create_placeholder(
                        JbPlaceholderInfo(
                            pack=info.pack_name,
                            asset=info.asset_name,
                            transform=obj.matrix_world.copy(),
                        ),
                        scene,
                    )
                    col = scene.collection
                    if col is not None:
                        col.objects.unlink(obj)
                    bpy.data.objects.remove(obj, do_unlink=True)
                    result.append(placeholder)
                    continue
            result.append(obj)
        return result

    def create_placeholder(self, placeholder_info, scene) -> JbObject:
        pack_name = placeholder_info["pack"]
        asset_name = placeholder_info["asset"]
        transform = placeholder_info["transform"]

        mesh = bpy.data.meshes.new(f"{pack_name}__{asset_name}")
        bm = bmesh.new()
        bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=0.5)
        bm.to_mesh(mesh)
        bm.free()
        obj = bpy.data.objects.new(f"{pack_name}__{asset_name}", mesh)

        obj["jb_placeholder_pack"] = pack_name
        obj["jb_placeholder_asset"] = asset_name
        obj.matrix_world = transform
        col = scene.collection
        if col is not None:
            col.objects.link(obj)
        return obj
