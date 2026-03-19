import re

import bpy

from .jb_api import JB_API
from .jb_asset_model import AssetModel
from .jb_scene_manager import JBSceneManager
from .jb_material_importer import JBMaterialImporter
from .jb_file_io import JBFileImporter
from .jb_logger import get_logger

logger = get_logger(__name__)


class JB_AssetImporter:
    def __init__(self):
        self.api = JB_API()
        self.scene = JBSceneManager()
        self.material_importer = JBMaterialImporter()
        self.file_importer = JBFileImporter()

    def import_assets(self) -> None:
        assets = self._collect_assets_for_reimport() or self._collect_active_asset()

        if not assets:
            logger.warning("No active asset found in selection or database.")
            return

        for asset in assets:
            self._import_single(asset)

    def _collect_assets_for_reimport(self) -> list:
        """Возвращает ассеты для переимпорта из выбранных коллекций, или пустой список."""
        selected = [
            obj
            for obj in bpy.context.selected_objects
            if obj.instance_type == "COLLECTION" and obj.instance_collection
        ]
        asset_collections = [
            obj.instance_collection
            for obj in selected
            if AssetModel.from_collection(obj.instance_collection)
        ]

        if not asset_collections:
            return []

        result = (
            bpy.ops.wm.invoke_confirm(
                message=(
                    f"Reimport existing assets?\n{len(asset_collections)} asset(s) will be reimported"
                )
            )
            if hasattr(bpy.ops.wm, "invoke_confirm")
            else True
        )

        # Используем встроенный диалог через оператор — в execute()-контексте используем простой bool
        assets = []
        for col in asset_collections:
            # Очищаем объекты внутри коллекции
            for obj in list(col.objects):
                col.objects.unlink(obj)
                bpy.data.objects.remove(obj, do_unlink=True)

            info = AssetModel.from_collection(col)
            if not info:
                continue

            asset = self.api.get_asset(
                info.pack_name,
                info.asset_name,
                info.database_name,
                info.asset_type,
            )
            if asset:
                assets.append(asset)

        return assets

    def _collect_active_asset(self) -> list:
        asset = self.api.get_active_asset()
        return [asset] if asset else []

    def _import_single(self, asset: AssetModel) -> None:
        match asset.bridge_type:
            case "layout":
                layout_col = self._create_model(asset)
                self._convert_to_instances(layout_col)
            case "model":
                self._create_model(asset)
            case "material":
                mat = self.material_importer.import_material(asset)
                if mat:
                    logger.info("Material '%s' imported.", mat.name)
            case _:
                logger.warning("Unsupported bridge type: %s", asset.bridge_type)

    def _import_file(
        self, asset: AssetModel, target_collection: bpy.types.Collection
    ) -> None:
        objects = self.file_importer.import_file(asset.asset_path)
        if not objects:
            logger.warning("No objects imported for asset: %s", asset.asset_name)
            return
        self.scene.move_objects_to_collection(objects, target_collection)

    def _create_model(self, asset: AssetModel) -> bpy.types.Collection:
        asset_col, exists = self.scene.get_or_create_asset_collection(asset)

        if exists:
            self._create_instance(asset_col, asset.asset_name)
        else:
            self._import_file(asset, asset_col)

        return asset_col

    def _convert_to_instances(self, layout_col: bpy.types.Collection) -> None:
        for p in self._extract_instances(layout_col):
            child_asset = self.api.get_asset(p["pack_name"], p["asset_name"])
            if not child_asset:
                continue

            asset_col, exists = self.scene.get_or_create_asset_collection(child_asset)
            if not exists:
                self._import_file(child_asset, asset_col)

            instance = self._create_instance(
                asset_col, child_asset.asset_name, parent_collection=layout_col
            )
            instance.matrix_world = p["matrix"]

        self.scene.remove_empty_from_collection(layout_col)

    def _create_instance(
        self,
        asset_collection: bpy.types.Collection,
        name: str,
        parent_collection: bpy.types.Collection = None,
    ) -> bpy.types.Object:
        """Создаёт Empty-объект с инстансингом коллекции."""
        empty = bpy.data.objects.new(f"Instance_{name}", None)
        empty.instance_type = "COLLECTION"
        empty.instance_collection = asset_collection
        empty["jb_pack_name"] = asset_collection.get("jb_pack_name", "")
        empty["jb_asset_name"] = asset_collection.get("jb_asset_name", "")
        empty["jb_asset_type"] = asset_collection.get("jb_asset_type", "")
        empty["jb_database_name"] = asset_collection.get("jb_database_name", "")

        target_col = parent_collection or bpy.context.scene.collection
        target_col.objects.link(empty)
        return empty

    def _extract_instances(self, layout_col: bpy.types.Collection) -> list:
        """Извлекает плейсхолдеры из layout-коллекции и возвращает список dict."""
        patterns = [
            re.compile(r"(?P<pack>.+?)_pack_(?P<asset>.+?)_asset$"),
            re.compile(r"(?P<pack>.+?)__(?P<asset>.+?)$"),
        ]
        result = []

        for obj in list(layout_col.objects):
            pack = obj.get("jb_placeholder_pack")
            asset = obj.get("jb_placeholder_asset")

            if not (pack and asset):
                # Пробуем извлечь из имени материала
                mat_name = (
                    next(
                        (m.name for m in obj.data.materials if m),
                        None,
                    )
                    if obj.data and hasattr(obj.data, "materials")
                    else None
                )

                if mat_name:
                    match = next(
                        (m for p in patterns if (m := p.match(mat_name))),
                        None,
                    )
                else:
                    # Fallback на имя объекта
                    match = next(
                        (m for p in patterns if (m := p.match(obj.name))),
                        None,
                    )

                if not match:
                    continue

                pack = match.group("pack")
                asset = match.group("asset")

            result.append(
                {
                    "pack_name": pack,
                    "asset_name": asset,
                    "matrix": obj.matrix_world.copy(),
                }
            )
            layout_col.objects.unlink(obj)
            bpy.data.objects.remove(obj, do_unlink=True)

        return result


class JB_OT_AssetImport(bpy.types.Operator):
    bl_idname = "jiko_bridge.asset_import"
    bl_label = "Import Asset"
    bl_description = "Import active asset from Jiko Bridge"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        importer = JB_AssetImporter()
        importer.import_assets()
        return {"FINISHED"}
