"""
Importer from Jiko Bridge
Code by Semyon Shapoval, 2026
"""

from src.jb_api import JbAPI
from src.scene.jb_scene import JbScene
from src.materials.jb_material_importer import JbMaterialImporter
from src.jb_types import AssetModel, JbSource, JbContainer, JbMaterial
from src.jb_utils import get_logger
from src.jb_protocols import JbAssetImporterProtocol

logger = get_logger(__name__)


class JbAssetImporter(JbAssetImporterProtocol):
    """Handles importing assets from Jiko Bridge into scene."""

    def __init__(self, source: JbSource):
        self.api = JbAPI()
        self.scene = JbScene(source)
        self.materials = JbMaterialImporter(source)

    def import_assets(self):
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
                mat_name = self.materials.get_material_name(mat)
                asset_model = AssetModel.from_string(mat_name)
                if asset_model:
                    asset = self.api.get_asset(asset_model)
                    if asset:
                        assets.append(asset)
                else:
                    asset = self.api.get_asset_by_search(mat_name)
                    if asset:
                        assets.append(asset)
                        self.materials.set_material_name(
                            mat, f"{asset.pack_name}__{asset.asset_name}"
                        )
            return list(assets)

        if containers:
            for container in containers:
                self.scene.clear_container(container)
                asset_model = self.scene.get_asset_data_from_container(container)
                if not asset_model:
                    continue
                asset = self.api.get_asset(asset_model)
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
        for file in asset.files:
            match file.bridge_type:
                case "model":
                    container = self._create_model(asset, file)
                    self._convert_to_instances(container)
                case "material":
                    mat = self.materials.import_material(asset, file)
                    if mat:
                        self.scene.merge_duplicates_materials(mat)
                case _:
                    logger.warning("Unsupported bridge type: %s", file.bridge_type)

    def _create_model(self, asset, file):
        container, exists = self.scene.get_or_create_asset_container(asset, file)
        if exists:
            self.scene.create_instance(container, asset.asset_name)
        else:
            self.scene.import_with_temp(file.filepath, container)
        return container

    def _convert_to_instances(self, container) -> None:
        objects = self.scene.walk([container])
        for obj in objects:
            if asset_model := self.scene.get_asset_from_placeholder(obj):
                asset_container = self.scene.get_container(asset_model)

                if not asset_container:
                    remote_asset = self.api.get_asset(asset_model)
                    if not remote_asset or not remote_asset.files:
                        continue

                    asset_container, exists = self.scene.get_or_create_asset_container(remote_asset)
                    if not exists:
                        for file in remote_asset.files:
                            self.scene.import_with_temp(file.filepath, asset_container)

                instance = self.scene.create_instance(asset_container, asset_model.asset_name)
                self.scene.copy_object_transform(instance, obj)
                self.scene.move_objects_to_container([instance], container)
                self.scene.remove_object(obj)

        self.scene.cleanup_container(container)
