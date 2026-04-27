"""
Asset importer from Jiko Bridge to C4D
Code by Semyon Shapoval, 2026
"""

from src import (
    JbAPI,
    JbScene,
    AssetFile,
    AssetInfo,
    AssetModel,
    JbContainer,
    JbObject,
    confirm,
    get_logger,
)

logger = get_logger(__name__)


class JbAssetImporter:
    """Class responsible for importing assets into the Blender scene."""

    def __init__(self):
        self.api = JbAPI()
        self.scene = JbScene()

    def import_assets(self) -> None:
        """Main entry for importing assets"""
        objects = self.scene.get_selection()

        assets = (
            self._collect_materials(objects)
            or self._collect_assets_for_reimport(objects)
            or self._collect_active_asset(objects)
        )

        if not assets:
            logger.warning("No active asset found in selection or database.")
            return

        for asset in assets:
            self._import_single(asset)

    def _collect_assets_for_reimport(self, objects: list[JbObject]) -> list:

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
            asset_info = AssetInfo.from_user_data(container)
            if not asset_info:
                continue
            asset = self.api.get_asset(
                asset_info.pack_name,
                asset_info.asset_name,
                asset_info.database_name,
                [AssetFile(asset_type=asset_info.asset_type)],
            )
            if asset:
                assets.append(asset)
        return assets

    def _collect_active_asset(self, objects: list[JbObject]) -> list:
        if objects:
            return []

        asset = self.api.get_active_asset()
        return [asset] if asset else []

    def _collect_materials(self, objects: list[JbObject]) -> list:
        materials = list(self.scene.get_materials_from_objects(objects)) + list(
            self.scene.get_selection_mateials()
        )

        if not materials:
            return []

        assets: list[AssetModel] = []
        seen: set[tuple[str, str, str | None]] = set()

        for material in materials:
            mat_name = material.GetName()
            asset_info = AssetInfo.from_string(mat_name)
            asset = None

            if asset_info is not None:
                key = (
                    asset_info.pack_name,
                    asset_info.asset_name,
                    asset_info.database_name,
                )
                if key in seen:
                    continue

                seen.add(key)
                asset = self.api.get_asset(
                    asset_info.pack_name,
                    asset_info.asset_name,
                    asset_info.database_name,
                )
            else:
                asset = self.api.get_asset_by_search(mat_name)

            if asset:
                assets.append(asset)
                material.SetName(f"{asset.pack_name}__{asset.asset_name}")

        if assets:
            logger.info("Found %d material asset(s) on selected meshes", len(assets))

        return assets

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
        container, exists = self.scene.get_or_create_asset_container(asset, file)
        if exists:
            self.scene.create_instance(container, asset.asset_name)
        else:
            self.scene.import_with_temp(file.filepath, container)
        return container

    def _convert_to_instances(self, layout_container: JbContainer) -> None:
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
                asset_container, child_asset.asset_name
            )
            self.scene.set_instance_transform(instance, p["matrix"])
            self.scene.add_instance_to_container(instance, layout_container)

        self.scene.cleanup_empty_objects(layout_container)
