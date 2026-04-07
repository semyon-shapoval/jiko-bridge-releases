from __future__ import annotations

import bmesh
import bpy

from .jb_asset_model import AssetModel
from .jb_logger import get_logger
from .jb_scene_select import JBSceneSelect

logger = get_logger(__name__)


class JBSceneInstance(JBSceneSelect):
    """Instance and placeholder management for Blender.

    Inherits selection helpers from JBSceneSelect and implements the
    instance / placeholder group of JBSceneBase.
    """

    # ------------------------------------------------------------------
    # Instance management
    # ------------------------------------------------------------------

    def has_instances(self, objects: list) -> bool:
        return any(obj.instance_type == "COLLECTION" for obj in objects)

    def create_instance(self, asset_container, name: str) -> bpy.types.Object:
        empty = bpy.data.objects.new(f"Instance_{name}", None)
        empty.instance_type = "COLLECTION"
        empty.instance_collection = asset_container
        empty["jb_pack_name"] = asset_container.get("jb_pack_name", "")
        empty["jb_asset_name"] = asset_container.get("jb_asset_name", "")
        empty["jb_asset_type"] = asset_container.get("jb_asset_type", "")
        empty["jb_database_name"] = asset_container.get("jb_database_name", "")
        bpy.context.scene.collection.objects.link(empty)
        return empty

    def set_instance_transform(self, instance, matrix) -> None:
        instance.matrix_world = matrix

    def add_instance_to_container(self, instance, container) -> None:
        try:
            bpy.context.scene.collection.objects.unlink(instance)
        except RuntimeError:
            pass
        container.objects.link(instance)

    # ------------------------------------------------------------------
    # Placeholder extraction
    # ------------------------------------------------------------------

    def extract_placeholders(self, container) -> list:
        result = []
        for obj in list(container.objects):
            pack = obj.get("jb_placeholder_pack")
            asset = obj.get("jb_placeholder_asset")

            if not (pack and asset):
                mat_name = (
                    next((m.name for m in obj.data.materials if m), None)
                    if obj.data and hasattr(obj.data, "materials")
                    else None
                )
                info = AssetModel.from_placeholder_name(mat_name or obj.name)
                if not info:
                    continue
                pack = info["pack_name"]
                asset = info["asset_name"]

            result.append(
                {
                    "pack_name": pack,
                    "asset_name": asset,
                    "matrix": obj.matrix_world.copy(),
                }
            )
            container.objects.unlink(obj)
            bpy.data.objects.remove(obj, do_unlink=True)

        return result

    # ------------------------------------------------------------------
    # Internal — placeholder creation / instance replacement
    # ------------------------------------------------------------------

    def _replace_instances_with_placeholders(
        self, objects: list, scene: bpy.types.Scene
    ) -> list:
        result = []
        for obj in objects:
            if obj.instance_type == "COLLECTION" and obj.instance_collection:
                info = AssetModel.from_collection(obj.instance_collection)
                if info and info.pack_name and info.asset_name:
                    placeholder = self._create_placeholder(
                        info.pack_name, info.asset_name, obj.matrix_world.copy(), scene
                    )
                    scene.collection.objects.unlink(obj)
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
        scene.collection.objects.link(obj)
        return obj
