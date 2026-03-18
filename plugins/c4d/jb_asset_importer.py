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
        return c4d.documents.GetActiveDocument()

    def import_assets(self) -> None:
        assets = self._collect_assets_for_reimport() or self._collect_active_asset()

        if not assets:
            logger.warning("No active asset found in selection or database.")
            return

        for asset in assets:
            self._import_single(asset)


    def _collect_assets_for_reimport(self) -> list[AssetModel]:
        """Returns reimported assets after user confirmation, or empty list."""
        selected = self.doc.GetActiveObjects(c4d.GETACTIVEOBJECTFLAGS_0)
        asset_nulls = [
            obj for obj in selected
            if obj.CheckType(c4d.Onull) and AssetModel.from_c4d_object(obj)
        ]

        if not asset_nulls:
            return []

        if not c4d.gui.QuestionDialog(
            f"Reimport existing assets?\n{len(asset_nulls)} asset(s) will be reimported"
        ):
            return []

        assets = []
        for null in asset_nulls:
            for child in null.GetChildren():
                child.Remove()

            info = AssetModel.from_c4d_object(null)
            if not info:
                continue

            asset = self.api.get_asset(
                info.pack_name, info.asset_name,
                info.database_name, info.asset_type,
            )
            if asset:
                assets.append(asset)

        return assets

    def _collect_active_asset(self) -> list[AssetModel]:
        asset = self.api.get_active_asset()
        return [asset] if asset else []

    def _import_single(self, asset: AssetModel) -> None:
        match asset.bridge_type:
            case "layout":
                layout_null = self._create_model(asset)
                self._convert_to_instances(layout_null)
            case "model":
                self._create_model(asset)
            case "material":
                self.material_import.import_material(asset)
            case _:
                logger.warning("Unsupported bridge type: %s", asset.bridge_type)

    def _import_file(self, asset: AssetModel, target: c4d.BaseObject) -> None:
        doc = self.doc

        with self.scene.temp_doc() as tmp_doc:
            if not self.file_importer.import_file(tmp_doc, asset.asset_path):
                return

            root_objects = self.scene.tree.get_top_objects(tmp_doc)
            if not root_objects:
                logger.warning("No objects imported for asset: %s", asset.asset_name)
                return

            self.scene.transfer_from_doc(tmp_doc, doc, root_objects, target)

    def _create_model(self, asset: AssetModel) -> c4d.BaseObject:
        asset_null, exists = self.scene.get_or_create_asset(self.doc, asset)

        if exists and asset_null.GetChildren():
            self.scene.create_instance(self.doc, asset_null, asset.asset_name)
        else:
            self._import_file(asset, asset_null)

        return asset_null

    def _convert_to_instances(self, layout_null: c4d.BaseObject) -> None:
        doc = self.doc

        for p in self.scene.extract_layout_placeholders(doc, layout_null):
            child_asset = self.api.get_asset(p["pack_name"], p["asset_name"])
            if not child_asset:
                continue

            asset_null, exists = self.scene.get_or_create_asset(doc, child_asset)
            if not exists:
                self._import_file(child_asset, asset_null)

            instance = self.scene.create_instance(doc, asset_null, child_asset.asset_name)
            instance.SetMg(p["matrix"])
            instance.InsertUnder(layout_null)

        self.scene.remove_empty_nulls(layout_null)