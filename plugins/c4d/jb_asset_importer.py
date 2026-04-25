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
        objects = self.scene.get_selection()
        assets = (
            self._collect_materials_from_meshes(objects)
            or self._collect_assets_for_reimport(objects)
            or self._collect_active_asset(objects)
        )

        if not assets:
            logger.warning("No active asset found in selection or database.")
            return

        for asset in assets:
            self._import_single(asset)

    def _collect_assets_for_reimport(self, objects: list) -> list:

        asset_containers = self.scene.filter_container_from_objects(objects)
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
                assetInfo.packName,
                assetInfo.assetName,
                assetInfo.databaseName,
                [AssetFile(assetType=assetInfo.assetType)],
            )
            if asset:
                assets.append(asset)
        return assets

    def _collect_active_asset(self, objects: list) -> list:
        if objects:
            return []

        asset = self.api.get_active_asset()
        return [asset] if asset else []

    def _collect_materials_from_meshes(self, objects: list) -> list:
        materials = self.scene.get_materials_from_objects(objects)
        if not materials:
            return []

        assets: list[AssetModel] = []
        seen: set[tuple[str, str, str | None]] = set()

        for material in materials:
            matName = material.GetName()
            asset_info = AssetInfo.from_placeholder_name(matName)
            asset = None

            if asset_info is not None:
                key = (
                    asset_info.packName,
                    asset_info.assetName,
                    asset_info.databaseName,
                )
                if key in seen:
                    continue

                seen.add(key)
                asset = self.api.get_asset(
                    asset_info.packName,
                    asset_info.assetName,
                    asset_info.databaseName,
                )
            else:
                asset = self.api.get_asset_by_search(matName)

            if asset:
                assets.append(asset)
                material.SetName(f"{asset.packName}__{asset.assetName}")

        if assets:
            logger.info("Found %d material asset(s) on selected meshes", len(assets))

        return assets

    def _import_single(self, asset: AssetModel) -> None:
        for file in asset.files:
            match file.bridgeType:
                case "model":
                    layout_container = self._create_model(asset, file)
                    self._convert_to_instances(layout_container)
                case "material":
                    self.scene.import_material(asset, file)
                case _:
                    logger.warning("Unsupported bridge type: %s", file.bridgeType)

    def _create_model(self, asset: AssetModel, file: AssetFile):
        container, exists = self.scene.get_or_create_asset_container(asset, file)
        if exists:
            self.scene.create_instance(container, asset.assetName)
        else:
            self.scene.import_with_temp(file.filepath, container)
        return container

    def _convert_to_instances(self, layout_container) -> None:
        for p in self.scene.extract_placeholders(layout_container):
            child_asset = self.api.get_asset(p["packName"], p["assetName"])
            if not child_asset:
                continue

            asset_container, exists = self.scene.get_or_create_asset_container(
                child_asset
            )
            if not exists:
                model_file = next(
                    (f for f in child_asset.files if f.bridgeType == "model"), None
                )
                if model_file:
                    self.scene.import_with_temp(model_file.filepath, asset_container)

            instance = self.scene.create_instance(
                asset_container, child_asset.assetName
            )
            self.scene.set_instance_transform(instance, p["matrix"])
            self.scene.add_instance_to_container(instance, layout_container)

        self.scene.cleanup_empty_objects(layout_container)
