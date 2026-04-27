from .jb_api import JB_API
from .jb_asset_model import AssetModel
from .jb_logger import get_logger

from ..scene.jb_scene import JBScene

logger = get_logger(__name__)


class JB_AssetImporter:
    def __init__(self):
        self.api = JB_API()
        self.scene = JBScene()

    def import_assets(self) -> None:
        objects = self.scene.get_selected_objects()
        assets = self._collect_assets_for_reimport() or self._collect_active_asset()

        if not assets:
            logger.warning("No active asset found in selection or database.")
            return

        for asset in assets:
            self._import_single(asset)

    def _collect_assets_for_reimport(self) -> list:
        asset_containers = self.scene.get_selected_asset_containers()
        if not asset_containers:
            return []

        if not self.scene.confirm(
            f"Reimport existing assets?\n{len(asset_containers)} asset(s) will be reimported"
        ):
            return []

        assets = []
        for container in asset_containers:
            self.scene.clear_container(container)
            info = self.scene.get_asset_info(container)
            if not info:
                continue
            asset = self.api.get_asset(
                info.packName, info.assetName, info.databaseName, info.assetType
            )
            if asset:
                assets.append(asset)
        return assets

    def _collect_active_asset(self) -> list:
        asset = self.api.get_active_asset()
        return [asset] if asset else []

    def _import_single(self, asset: AssetModel) -> None:
        match asset.bridgeType:
            case "model":
                layout_container = self._create_model(asset)
                self._convert_to_instances(layout_container)
            case "material":
                self.material_importer.import_material(asset)
            case _:
                logger.warning("Unsupported bridge type: %s", asset.bridgeType)

    def _create_model(self, asset: AssetModel):
        container, exists = self.scene.get_or_create_container(asset)
        if exists:
            self.scene.create_instance(container, asset.assetName)
        else:
            self.scene.import_with_temp(asset.assetPath, container)
        return container

    def _convert_to_instances(self, layout_container) -> None:
        for p in self.scene.extract_placeholders(layout_container):
            child_asset = self.api.get_asset(p["pack_name"], p["asset_name"])
            if not child_asset:
                continue

            asset_container, exists = self.scene.get_or_create_container(child_asset)
            if not exists:
                self.scene.import_with_temp(child_asset.asset_path, asset_container)

            instance = self.scene.create_instance(
                asset_container, child_asset.asset_name
            )
            self.scene.set_instance_transform(instance, p["matrix"])
            self.scene.add_instance_to_container(instance, layout_container)

        self.scene.cleanup_empty_objects(layout_container)
