"""
Instance managament and placeholder extraction for Blender.
Code by Semyon Shapoval, 2026
"""

from __future__ import annotations

import bpy
import bmesh
from ..jb_types import AssetModel, JbObject
from .jb_scene_container import JbSceneContainer
from ..jb_protocols import JbPlaceholderInfo


class JbSceneInstance(JbSceneContainer):
    """Instance and placeholder management for Blender."""

    def create_instance(self, container, name) -> JbObject:
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

    def create_placeholder(self, placeholder_info, source) -> JbObject:
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
        col = source.collection
        if col is not None:
            col.objects.link(obj)
        return obj

    def extract_placeholders(self, container) -> list[JbPlaceholderInfo]:
        """Extracts placeholder objects from the container and returns their info."""
        result = []
        for obj in list(container.objects):
            if not isinstance(obj, bpy.types.Object):
                continue

            data = obj.data
            if (
                data is None
                or not isinstance(data, bpy.types.Mesh)
                or not hasattr(obj.data, "materials")
                or len(data.vertices) != 4
            ):
                continue

            mat_name = next((m.name for m in data.materials if m), None)
            asset_model = AssetModel.from_string(mat_name or obj.name)
            if not asset_model:
                continue

            result.append(
                JbPlaceholderInfo(
                    asset=asset_model,
                    transform=obj.matrix_world.copy(),
                )
            )
            container.objects.unlink(obj)
            bpy.data.objects.remove(obj, do_unlink=True)

        return result

    def replace_instances_with_placeholders(self, objects, source) -> list[JbObject]:
        result = []
        for obj in objects:
            if obj.instance_type == "COLLECTION" and obj.instance_collection:
                info = self.get_asset_data_from_container(obj.instance_collection)
                if info and info.pack_name and info.asset_name:
                    placeholder = self.create_placeholder(
                        JbPlaceholderInfo(
                            asset=info,
                            transform=obj.matrix_world.copy(),
                        ),
                        source,
                    )
                    col = source.collection
                    if col is not None:
                        col.objects.unlink(obj)
                    bpy.data.objects.remove(obj, do_unlink=True)
                    result.append(placeholder)
                    continue
            result.append(obj)
        return result
