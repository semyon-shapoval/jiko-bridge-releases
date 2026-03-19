import re

import c4d

from jb_logger import get_logger
from jb_scene_manager import JBSceneManager
from jb_api import JB_API
from jb_material_importer import JBMaterialImporter
from jb_file_io import JBFileImporter
from jb_asset_model import AssetModel
from jb_utils import confirm

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
            obj
            for obj in selected
            if obj.CheckType(c4d.Onull) and AssetModel.from_c4d_object(obj)
        ]

        if not asset_nulls:
            return []

        if not confirm(
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
                info.pack_name,
                info.asset_name,
                info.database_name,
                info.asset_type,
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
            
            self.scene.copy_objects_from_doc(tmp_doc, doc, root_objects, target)

    def _create_model(self, asset: AssetModel) -> c4d.BaseObject:
        asset_null, exists = self.scene.get_or_create_asset(self.doc, asset)

        if exists and asset_null.GetChildren():
            self._create_instance(self.doc, asset_null, asset.asset_name)
        else:
            self._import_file(asset, asset_null)

        return asset_null

    def _convert_to_instances(self, layout_null: c4d.BaseObject) -> None:
        doc = self.doc

        for i in self._extract_instances(layout_null):
            child_asset = self.api.get_asset(i["pack_name"], i["asset_name"])
            if not child_asset:
                continue

            asset_null, exists = self.scene.get_or_create_asset(doc, child_asset)
            if not exists:
                self._import_file(child_asset, asset_null)

            instance = self._create_instance(doc, asset_null, child_asset.asset_name)
            instance.SetMg(i["matrix"])
            instance.InsertUnder(layout_null)

        self.scene.remove_empty_nulls(layout_null)

    def _extract_instances(self, layout_null: c4d.BaseObject) -> list[dict]:
        objs = self.scene.tree.get_children(layout_null)
        patterns = [
            re.compile(r"(?P<pack>.+?)_pack_(?P<asset>.+?)_asset$"),
            re.compile(r"(?P<pack>.+?)__(?P<asset>.+?)$"),
        ]
        result = []

        for obj in objs:
            match = next(
                (
                    m
                    for t in obj.GetTags()
                    for p in patterns
                    if (m := p.match(t.GetName()))
                ),
                None,
            )
            if not match:
                continue

            result.append(
                {
                    "pack_name": match.group("pack"),
                    "asset_name": match.group("asset"),
                    "matrix": obj.GetMg(),
                }
            )
            obj.Remove()

        return result

    def _create_instance(
        self,
        doc: c4d.documents.BaseDocument,
        link: c4d.BaseObject,
        name: str,
        parent: c4d.BaseObject = None,
    ) -> c4d.BaseObject:
        """Создаёт Oinstance, вставляет в сцену и опционально под parent."""
        instance = c4d.BaseObject(c4d.Oinstance)
        instance.SetName(f"Instance_{name}")
        instance[c4d.INSTANCEOBJECT_LINK] = link
        instance[c4d.INSTANCEOBJECT_RENDERINSTANCE_MODE] = 1

        for key, bc in link.GetUserDataContainer():
            self.scene.set_user_data(instance, bc[c4d.DESC_NAME], link[key])

        doc.InsertObject(instance)
        if parent:
            instance.InsertUnder(parent)
        instance.SetBit(c4d.BIT_ACTIVE)
        return instance
