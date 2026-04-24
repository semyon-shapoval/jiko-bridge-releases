from jb_api import JB_API
from jb_logger import get_logger
from jb_utils import confirm
from scene.jb_scene import JBScene
from jb_asset_model import AssetInfo, AssetModel, AssetFile

logger = get_logger(__name__)


class JB_AssetImporter:
    def __init__(self):
        self.api = JB_API()
        self.scene = JBScene()

    def import_assets(self) -> None:
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

        if not confirm(
            f"Reimport existing assets?\n{len(asset_containers)} asset(s) will be reimported"
        ):
            return []

        assets = []
        for container in asset_containers:
            self.scene.clear_container(container)
            assetInfo = AssetInfo.get_asset_info(container)
            if not assetInfo:
                continue
            asset = self.api.get_asset(
                assetInfo.pack_name,
                assetInfo.asset_name,
                assetInfo.database_name,
                [assetInfo.asset_type],
            )
            if asset:
                assets.append(asset)
        return assets

    def _collect_active_asset(self) -> list:
        asset = self.api.get_active_asset()
        return [asset] if asset else []

    def _import_single(self, asset: AssetModel) -> None:
        for file in asset.files:
            match file.bridge_type:
                case "model":
                    layout_container = self._create_model(asset, file)
                    self._convert_to_instances(layout_container)
                case "material":
                    self.scene.import_material(asset, file)
                case _:
                    logger.warning("Unsupported bridge type: %s", file.bridge_type)

    def _create_model(self, asset: AssetModel, file: AssetFile):
        container, exists = self.scene.get_or_create_asset_container(
            asset, file
        )
        if exists:
            self.scene.create_instance(container, asset.asset_name)
        else:
            self.scene.import_with_temp(file.file_path, container)
        return container

    def _convert_to_instances(self, layout_container) -> None:
        for p in self.scene.extract_placeholders(layout_container):
            child_asset = self.api.get_asset(p["pack_name"], p["asset_name"])
            if not child_asset:
                continue

            asset_container, exists = self.scene.get_or_create_asset_container(
                child_asset
            )
            if not exists:
                model_file = next(
                    (f for f in child_asset.files if f.bridge_type == "model"), None
                )
                if model_file:
                    self.scene.import_with_temp(model_file.file_path, asset_container)

            instance = self.scene.create_instance(
                asset_container, child_asset.asset_name
            )
            self.scene.set_instance_transform(instance, p["matrix"])
            self.scene.add_instance_to_container(instance, layout_container)

        self.scene.cleanup_empty_objects(layout_container)
