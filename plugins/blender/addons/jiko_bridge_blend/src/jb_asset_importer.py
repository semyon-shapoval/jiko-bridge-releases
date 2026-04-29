"""
Importer from Jiko Bridge
Code by Semyon Shapoval, 2026
"""

from .jb_api import JbAPI
from .scene.jb_scene import JbScene
from .jb_types import AssetFile, AssetInfo, AssetModel, JbContainer, JbObject, JbSource
from .jb_utils import confirm, get_logger

logger = get_logger(__name__)


class JbAssetImporter:
    """Handles importing assets from Jiko Bridge into scene."""

    def __init__(self, source: JbSource):
        self.api = JbAPI()
        self.scene = JbScene(source)

    def import_assets(self) -> None:
        """Imports assets by selection."""
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

    def _collect_materials(self, objects: list[JbObject]) -> list:
        materials = list(self.scene.get_materials_from_objects(objects)) + list(
            self.scene.get_selection("materials")
        )

        if not materials:
            return []

        assets: list[AssetModel] = []
        seen: set[tuple[str, str, str | None]] = set()

        for material in materials:
            mat_name = material.name
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
                asset = self.api.get_asset_by_info(asset_info)
            else:
                asset = self.api.get_asset_by_search(mat_name)

            if asset:
                assets.append(asset)
                material.name = f"{asset.pack_name}__{asset.asset_name}"

        if assets:
            logger.info("Found %d material asset(s) on selected meshes", len(assets))

        return assets

    def _collect_assets_for_reimport(self, objects: list[JbObject]) -> list:

        asset_containers = self.scene.filter_containers_from_objects(objects)
        if not asset_containers:
            return []

        if not confirm(
            f"Reimport existing assets?\n{len(asset_containers)} asset(s) will be reimported"
        ):
            return []

        assets = []
        for container in asset_containers:
            self.scene.clear_container(container)
            asset_info = self.scene.get_asset_from_user_data(container)
            if not asset_info:
                continue
            asset = self.api.get_asset_by_info(asset_info)
            if asset:
                assets.append(asset)
        return assets

    def _collect_active_asset(self, objects: list[JbObject]) -> list:
        if objects:
            return []

        asset = self.api.get_active_asset()
        return [asset] if asset else []

    def _import_single(self, asset: AssetModel) -> None:
        for file in asset.files:
            match file.bridge_type:
                case "model":
                    if not file.filepath:
                        logger.error(
                            "Model file is missing filepath for asset '%s'",
                            asset.asset_name or "<unknown>",
                        )
                        continue
                    if not asset.asset_name:
                        logger.error("Asset name missing for model import. Skipping file.")
                        continue
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

            asset_container, exists = self.scene.get_or_create_asset_container(child_asset)
            if not exists:
                for file in child_asset.files:
                    self.scene.import_with_temp(file.filepath, asset_container)

            instance = self.scene.create_instance(asset_container, child_asset.asset_name)
            self.scene.set_object_transform(instance, p["matrix"])
            self.scene.add_instance_to_container(instance, layout_container)

        self.scene.cleanup_empty_objects(layout_container)
