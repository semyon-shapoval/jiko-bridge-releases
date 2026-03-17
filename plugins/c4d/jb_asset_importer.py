from typing import Optional

import c4d

from jb_logger import get_logger
from jb_scene_manager import JBSceneManager
from jb_api import JB_API
from jb_material_importer import JBMaterialImporter
from jb_file_importer import JBFileImporter
from jb_asset_model import AssetModel


logger = get_logger(__name__)


class JB_AssetImporter:
    def __init__(self):
        self.api = JB_API()
        self.scene = JBSceneManager()
        self.material_import = JBMaterialImporter()
        self.file_importer = JBFileImporter()

    @property
    def doc(self) -> c4d.documents.BaseDocument:
        """Returns the active Cinema 4D document."""
        return c4d.documents.GetActiveDocument()

    def reimport_assets(self) -> list[AssetModel]:
        """Reimports assets from the database based on the current selection."""
        selected_objects = self.doc.GetActiveObjects(c4d.GETACTIVEOBJECTFLAGS_0)
        asset_nulls = []
        assets: list[AssetModel] = []

        for obj in selected_objects:
            if obj.CheckType(c4d.Onull):
                assetInfo = AssetModel.from_c4d_object(obj)
                if assetInfo:
                    asset_nulls.append(obj)

        if len(asset_nulls) > 0:
            confirmed = c4d.gui.QuestionDialog(
                f"Reimport existing assets?\n {len(asset_nulls)} asset(s) will be reimported"
            )
            if confirmed:
                for asset_null in asset_nulls:
                    for child in asset_null.GetChildren():
                        child.Remove()
                    asset_info = AssetModel.from_c4d_object(asset_null)
                    if asset_info:
                        asset = self.api.get_asset(
                            asset_info.pack_name,
                            asset_info.asset_name,
                            asset_info.database_name,
                            asset_info.asset_type,
                        )
                        if asset:
                            assets.append(asset)
        return assets

    def import_assets(self, assets: list[AssetModel] = []) -> None:
        """Imports an asset from the database. If asset is None, tries to get active asset."""
        assets = self.reimport_assets()

        if len(assets) == 0:
            asset = self.api.get_active_asset()
            if asset:
                assets.append(asset)

        if len(assets) == 0:
            logger.warning("No active asset found in selection or database.")
            return

        for asset in assets:
            if asset.bridge_type == "layout":
                return self.convert_to_instances(asset)
            elif asset.bridge_type == "model":
                return self.create_model(asset)
            elif asset.bridge_type == "material":
                return self.material_import.import_material(asset)
            else:
                logger.warning("Unsupported bridge type: %s", asset.bridge_type)
            continue

    def import_file(self, asset: AssetModel, target: c4d.BaseObject) -> None:
        """Гарантирует что ассет импортирован. Возвращает asset_null или None при ошибке."""
        doc = self.doc

        with self.scene.temp_doc() as tmp_doc:
            if not self.file_importer.import_file(tmp_doc, asset.asset_path):
                return

            root_objects = self.scene.get_top_objects(tmp_doc)
            if not root_objects:
                logger.warning(
                    "No new objects were imported for asset: %s", asset.asset_name
                )
                return

            self.scene.transfer_from_doc(tmp_doc, doc, root_objects, target)

    def create_model(self, asset: AssetModel) -> c4d.BaseObject:
        asset_null, asset_exists = self.scene.get_or_create_asset(self.doc, asset)

        if asset_exists and len(asset_null.GetChildren()) > 0:
            self.scene.create_instance(self.doc, asset_null, asset.asset_name)
        else:
            self.import_file(asset, asset_null)

        return asset_null 


    def convert_to_instances(self, asset: AssetModel) -> None:
        layout_null = self.create_model(asset) 

        layout_null_children = layout_null.GetChildren()
        if len(layout_null_children) > 0 and layout_null_children[0].CheckType(c4d.Oinstance):
            return

        doc = self.doc
        placeholders = self.scene.extract_layout_placeholders(doc, layout_null)

        for p in placeholders:
            child_asset = self.api.get_asset(p["pack_name"], p["asset_name"])
            if not child_asset:
                continue

            asset_null, asset_exists = self.scene.get_or_create_asset(doc, child_asset)
            if not asset_exists:
                self.import_file(child_asset, asset_null)

            instance = self.scene.create_instance(doc, asset_null, child_asset.asset_name)
            instance.SetMg(p["matrix"])
            instance.InsertUnder(layout_null)

        self.scene.remove_empty_nulls(layout_null)