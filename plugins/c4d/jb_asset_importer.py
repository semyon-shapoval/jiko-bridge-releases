from contextlib import contextmanager
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

    def get_active_asset(self) -> Optional[AssetModel]:
        """Tries to get the active asset based on the current selection or database."""
        selected_objects = self.doc.GetActiveObjects(c4d.GETACTIVEOBJECTFLAGS_0)
        for obj in selected_objects:
            if obj.CheckType(c4d.Onull):
                asset = AssetModel.from_c4d_object(obj)
                if asset:
                    logger.debug("Active asset found from selection: %r", asset)
                    return asset

        asset = self.api.get_active_asset()
        if asset:
            logger.debug("Active asset fetched from database: %r", asset)
            return asset

        logger.warning("No active asset found in selection.")
        return None

    def import_asset(self, asset: Optional[AssetModel] = None) -> bool:
        """Imports an asset from the database. If asset is None, tries to get active asset."""
        if not asset:
            asset = self.get_active_asset()
            if not asset:
                logger.warning("No active asset found in database.")
                return False

        if asset.bridge_type == "layout":
            return self.create_layout(asset)
        elif asset.bridge_type == "model":
            success, _ = self.create_model(asset)
            return success
        elif asset.bridge_type == "material":
            return self.material_import.import_material(asset)
        else:
            logger.warning("Unsupported bridge type: %s", asset.bridge_type)

        return False

    def override_model(self, obj):
        """Overrides the model under the given object with the asset from the database."""
        asset_info = AssetModel.from_c4d_object(obj)
        if not asset_info:
            return None

        asset = self.api.get_asset(
            asset_info.pack_name,
            asset_info.asset_name,
            asset_info.asset_type,
        )

        if not asset:
            logger.warning("Asset not found in database. Cannot override.")
            return None

        self.scene.set_selection([])
        for obj in self.scene.get_children(obj):
            obj.Remove()

        self.import_asset(asset)
        return asset

    def create_model(self, asset: AssetModel) -> tuple[bool, bool]:
        doc = self.doc
        self.scene.set_selection(doc, [])
        asset_null, asset_exists = self.scene.get_or_create_asset(doc, asset)

        if not asset_null:
            logger.error("Failed to create asset null")
            return False, False

        if asset_exists:
            self.scene.create_instance(doc, asset_null, asset.asset_name)
            return True, False

        with self.scene.temp_doc() as tmp_doc:
            if not self.file_importer.import_file(tmp_doc, asset.asset_path):
                return False, False

            root_objects = self.scene.get_top_objects(tmp_doc)
            if not root_objects:
                logger.warning(
                    "No new objects were imported for asset: %s", asset.asset_name
                )
                return True, False

            self.scene.transfer_from_doc(tmp_doc, doc, root_objects, asset_null)

        return True, True

    def create_layout(self, asset: AssetModel) -> bool:
        """Import an asset as a layout."""
        success, imported = self.create_model(asset)

        if not success:
            return False

        if not imported:
            return True

        doc = self.doc

        asset_null, _ = self.scene.get_or_create_asset(doc, asset)
        placeholders = self.scene.extract_layout_placeholders(asset_null)
        imported: set[str] = set()

        for p in placeholders:
            asset = self.api.get_asset(p["pack_name"], p["asset_name"])
            if not asset:
                continue
            asset_null, _ = self.scene.get_or_create_asset(doc, asset)
            instance = self.scene.create_instance(doc, asset_null, asset.asset_name)
            instance.SetMg(p["matrix"])
            instance.InsertUnder(asset_null)
            key = f"{p['pack_name']}/{p['asset_name']}"
            if key not in imported:
                imported.add(key)
                self.import_asset(asset)
