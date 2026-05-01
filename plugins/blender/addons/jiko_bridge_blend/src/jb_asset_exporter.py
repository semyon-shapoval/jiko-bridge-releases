"""
Asset exporter for Jiko Bridge
Code by Semyon Shapoval, 2026
"""

from pathlib import Path

from .jb_api import JbAPI
from .jb_types import AssetFile, JbMaterial, JbObject, JbSource, JbContainer
from .scene.jb_scene import JbScene
from .jb_utils import get_logger
from .jb_protocols import JbAssetExporterProtocol

logger = get_logger(__name__)


class JbAssetExporter(JbAssetExporterProtocol):
    """Export asset class"""

    def __init__(self, source: JbSource):
        self.api = JbAPI()
        self.scene = JbScene(source)

    def export_asset(self) -> None:
        """Export the selected asset or create a new one."""
        selected_objects, asset_containers = self._collect_data()
        if asset_containers:
            for container in asset_containers:
                self._update_asset(container)
        else:
            self._create_new_asset(selected_objects)

    def export_message(self) -> str:
        selected_objects, asset_containers = self._collect_data()
        if asset_containers:
            return "Update existing assets?\n" f"{len(asset_containers)} asset(s) will be updated"

        if selected_objects:
            return (
                "No asset containers found in selection. "
                f"Create new asset with {len(selected_objects)} object(s)?"
            )

        return "Export Blender project."

    def _collect_data(self) -> tuple[list[JbContainer | JbObject | JbMaterial], list[JbContainer]]:
        selected_objects = self.scene.get_selection()
        asset_containers = self.scene.get_containers_from_objects(selected_objects)
        return selected_objects, asset_containers

    def _update_asset(self, container) -> None:
        asset_info = self.scene.get_asset_data_from_container(container)
        if not asset_info:
            logger.error("Invalid asset information")
            return

        objects = self.scene.get_objects(container)
        if not objects:
            logger.error("Container '%s' has no objects for export.", asset_info.asset_name)
            return

        asset = self.api.get_asset_by_model(asset_info)
        if not asset or not asset.files:
            logger.error("Failed to fetch asset '%s'.", asset_info.asset_name)
            return

        for file in asset.files:
            if not file.filepath:
                logger.error(
                    "Filepath missing for asset '%s'. Cannot export.",
                    asset_info.asset_name,
                )
                continue
            ext = Path(file.filepath.lower()).suffix
            if not ext:
                logger.error(
                    "Unable to determine export extension from filepath '%s' for '%s'.",
                    file.filepath,
                    asset_info.asset_name,
                )
                continue

            filepath = self.scene.export_with_temp(objects, ext)

            if not filepath or not asset:
                continue

            if not asset.pack_name or not asset.asset_name:
                logger.error(
                    "Asset information incomplete for '%s'. Cannot update asset.",
                    asset_info.asset_name,
                )
                continue

            if self.api.update_asset(
                asset.pack_name,
                asset.asset_name,
                asset.database_name,
                [AssetFile(filepath=filepath, asset_type=file.asset_type)],
            ):
                logger.info("Asset '%s' updated successfully.", asset_info.asset_name)
            else:
                logger.error("Failed to update asset '%s'.", asset_info.asset_name)

    def _create_new_asset(self, objects) -> None:
        filepath = self.scene.export_with_temp(objects, ".fbx")
        if not filepath:
            logger.error("Export failed.")
            return

        asset = self.api.create_asset([AssetFile(filepath=filepath, asset_type=None)])

        if not asset or not asset.files:
            logger.error("No asset found for filepath '%s'", filepath)
            return

        for file in asset.files:
            container, _ = self.scene.get_or_create_asset_container(asset, file)
            self.scene.move_objects_to_container(objects, container)
            logger.info("Asset '%s' created with type '%s'.", asset.asset_name, file.asset_type)
