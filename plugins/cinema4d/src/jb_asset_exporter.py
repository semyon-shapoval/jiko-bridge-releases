"""
Asset exporter from C4D to Jiko Bridge
Code by Semyon Shapoval, 2026
"""

import os

from src.jb_api import JbAPI
from src.jb_types import AssetFile, JbContainer
from src.jb_logger import get_logger
from src.jb_utils import confirm
from src.scene.jb_scene import JbScene

logger = get_logger(__name__)


class JbAssetExporter:
    """Export asset class"""

    def __init__(self):
        self.api = JbAPI()
        self.scene = JbScene()

    def export_asset(self) -> None:
        """Export the selected asset or create a new one if no asset container is selected."""
        selected_objects = self.scene.get_selection()
        asset_container = self.scene.filter_container_from_objects(selected_objects)
        if asset_container:
            self._update_asset(asset_container)
        else:
            self._create_new_asset(selected_objects)

    def _update_asset(self, container: JbContainer) -> None:
        asset_info = self.scene.get_asset_from_user_data(container)
        if not asset_info:
            logger.error("Invalid asset information on container: %s", container.GetName())
            return

        if not confirm(
            f"Update asset '{asset_info.asset_name}'?\nThis will overwrite the existing file."
        ):
            return

        objects = self.scene.get_objects_recursive(container)
        if not objects:
            logger.error("Container '%s' has no objects for export.", container.GetName())
            return

        asset = self.api.get_asset_by_info(asset_info)
        if not asset or not asset.files:
            logger.error("Failed to fetch asset '%s'.", asset_info.asset_name)
            return

        for file in asset.files:
            ext = os.path.splitext(file.filepath)[1]
            if not ext:
                logger.error(
                    "Unable to determine export extension from filepath '%s' for '%s'.",
                    file.filepath,
                    asset_info.asset_name,
                )
                continue

            filepath = self.scene.export_with_temp(objects, ext)
            if not filepath:
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

    def _create_new_asset(self, objects: list) -> None:
        if not confirm(
            "Create new asset from selected objects? Go to Jiko Bridge app to finish setup."
        ):
            return

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
