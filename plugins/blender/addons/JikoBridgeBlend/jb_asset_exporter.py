import bpy
import bmesh
import time
from typing import Optional

from .jb_api import JB_API
from .jb_asset_model import AssetModel
from .jb_scene_manager import JBSceneManager
from .jb_file_io import JBFileExporter
from .jb_logger import get_logger

logger = get_logger(__name__)


class JB_AssetExporter:
    def __init__(self):
        self.api = JB_API()
        self.scene = JBSceneManager()
        self.file_exporter = JBFileExporter()

    def export_asset(self) -> None:
        selected_collections = self._get_selected_asset_collections()

        if self._is_single_asset_collection(selected_collections):
            self._update_asset(selected_collections[0])
        else:
            selected_objects = list(bpy.context.selected_objects)
            self._create_new_asset(selected_objects)

    def _get_selected_asset_collections(self) -> list:
        """Возвращает список коллекций-ассетов, чьи инстансы выбраны."""
        result = []
        for obj in bpy.context.selected_objects:
            if obj.instance_type == "COLLECTION" and obj.instance_collection:
                info = AssetModel.from_collection(obj.instance_collection)
                if info:
                    result.append(obj.instance_collection)
        return result

    def _is_single_asset_collection(self, collections: list) -> bool:
        return len(collections) == 1

    def _update_asset(self, col: bpy.types.Collection) -> None:
        asset = AssetModel.from_collection(col)
        if not asset:
            logger.error("Invalid asset information on collection: %s", col.name)
            return

        objects = list(col.objects)
        ext = self._detect_ext(objects)
        filepath = self.export_with_placeholder(objects, ext)
        if not filepath:
            return

        if self.api.update_asset(
            filepath,
            asset.pack_name,
            asset.asset_name,
            asset.asset_type,
            asset.database_name,
        ):
            logger.info("Asset '%s' updated successfully.", asset.asset_name)
        else:
            logger.error("Failed to update asset '%s'.", asset.asset_name)

    def _create_new_asset(self, objects: list) -> None:
        ext = self._detect_ext(objects)
        filepath = self.export_with_placeholder(objects, ext)

        if not filepath:
            logger.error("Export failed.")
            return

        asset = self.api.create_asset(filepath)
        if not asset:
            logger.error("Failed to create asset for '%s'.", filepath)
            return

        col, _ = self.scene.get_or_create_asset_collection(asset)
        self.scene.move_objects_to_collection(objects, col)
        logger.info("Asset collection '%s' created.", col.name)

    def export_with_placeholder(self, objects: list, ext: str) -> Optional[str]:
        """
        Аналог C4D export_with_placeholder:
        — копирует объекты во временную сцену,
        — заменяет collection-инстансы на mesh-плейсхолдеры,
        — экспортирует,
        — временная сцена полностью удаляется без показа пользователю.
        """
        with self.scene.temp_scene() as temp:
            copies = self._copy_objects_to_scene(objects, temp)
            export_objects = self._replace_instances_with_placeholders(copies, temp)
            return self.file_exporter.export_file(export_objects, ext)

    def _copy_objects_to_scene(self, objects: list, scene: bpy.types.Scene) -> list:
        """Глубоко копирует объекты в указанную сцену."""
        copies = []
        for obj in objects:
            copy = obj.copy()
            if obj.data:
                copy.data = obj.data.copy()
            scene.collection.objects.link(copy)
            copies.append(copy)
        return copies

    def _replace_instances_with_placeholders(
        self, objects: list, scene: bpy.types.Scene
    ) -> list:
        """
        Заменяет Empty-инстансы коллекций на меш-плейсхолдеры с именем
        {pack_name}__{asset_name} — аналог C4D _replace_instances_with_placeholders.
        """
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

    def _has_instances(self, objects: list) -> bool:
        return any(obj.instance_type == "COLLECTION" for obj in objects)

    def _detect_ext(self, objects: list) -> str:
        return ".abc" if self._has_instances(objects) else ".fbx"


class JB_OT_AssetExport(bpy.types.Operator):
    bl_idname = "jiko_bridge.asset_export"
    bl_label = "Export Asset"
    bl_description = "Export selected objects as a new asset or update existing"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        exporter = JB_AssetExporter()
        exporter.export_asset()
        return {"FINISHED"}
