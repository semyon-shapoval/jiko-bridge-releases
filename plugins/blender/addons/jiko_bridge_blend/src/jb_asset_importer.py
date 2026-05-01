"""
Importer from Jiko Bridge
Code by Semyon Shapoval, 2026
"""

from .jb_api import JbAPI
from .scene.jb_scene import JbScene
from .jb_protocols import JbAssetImporterProtocol
from .materials.jb_material_importer import JbMaterialImporter
from .jb_types import AssetModel, JbContainer, JbSource, JbMaterial
from .jb_utils import get_logger

logger = get_logger(__name__)


class JbAssetImporter(JbAssetImporterProtocol):
    """Handles importing assets from Jiko Bridge into scene."""

    def __init__(self, source: JbSource):
        self.api = JbAPI()
        self.scene = JbScene(source)
        self.materials = JbMaterialImporter()

    def import_assets(self) -> None:
        assets = self._collect_assets()

        for asset in assets:
            self._import_single(asset)

    def import_message(self) -> str:
        materials, containers = self._collect_data()

        if materials:
            return (
                "Import assets for materials?\n"
                f"{len(materials)} material(s) with asset info found in selection."
            )
        if containers:
            return (
                "Import assets for asset containers?\n"
                f"{len(containers)} asset container(s) found in selection."
            )
        return "Import active asset from Jiko Bridge."

    def _collect_data(self) -> tuple[list[JbMaterial], list[JbContainer]]:
        objects = self.scene.get_selection()

        materials = self.scene.get_materials_from_objects(objects)
        containers = self.scene.get_containers_from_objects(objects)

        return materials, containers

    def _collect_assets(self) -> list[AssetModel]:
        assets: list[AssetModel] = []
        materials, containers = self._collect_data()

        if materials:
            for mat in materials:
                mat_name = mat.name
                asset_model = AssetModel.from_string(mat_name)
                if asset_model:
                    asset = self.api.get_asset_by_model(asset_model)
                    if asset:
                        assets.append(asset)
                else:
                    asset = self.api.get_asset_by_search(mat_name)
                    if asset:
                        assets.append(asset)
                        mat.name = f"{asset.pack_name}__{asset.asset_name}"
            return list(assets)

        if containers:
            for container in containers:
                self.scene.clear_container(container)
                asset_model = self.scene.get_asset_data_from_container(container)
                if not asset_model:
                    continue
                asset = self.api.get_asset_by_model(asset_model)
                if asset:
                    assets.append(asset)
            return list(assets)

        if not materials and not containers:
            asset = self.api.get_active_asset()
            if asset:
                assets.append(asset)
            return list(assets)

        return []

    def _import_single(self, asset: AssetModel) -> None:
        if not asset.files:
            logger.warning("Asset '%s' has no files to import.", asset.asset_name)
            return

        for file in asset.files:
            match file.bridge_type:
                case "model":
                    layout_container = self._create_model(asset, file)
                    self._convert_to_instances(layout_container)
                case "material":
                    self.materials.import_material(asset, file)
                case _:
                    logger.warning("Unsupported bridge type: %s", file.bridge_type)

    def _create_model(self, asset, file):
        container, exists = self.scene.get_or_create_asset_container(asset, file)
        if exists:
            self.scene.create_instance(container, asset.asset_name)
        else:
            self.scene.import_with_temp(file.filepath, container)
        return container

    def _convert_to_instances(self, layout_container: JbContainer) -> None:
        for p in self.scene.extract_placeholders(layout_container):
            child_asset = self.api.get_asset_by_model(p["asset"])
            if not child_asset or not child_asset.files:
                continue

            asset_container, exists = self.scene.get_or_create_asset_container(child_asset)

            if not exists:
                for file in child_asset.files:
                    self.scene.import_with_temp(file.filepath, asset_container)

            instance = self.scene.create_instance(asset_container, child_asset.asset_name)
            self.scene.set_object_transform(instance, p["transform"])
            self.scene.move_objects_to_container([instance], layout_container)

        self.scene.cleanup_empty_objects(layout_container)
