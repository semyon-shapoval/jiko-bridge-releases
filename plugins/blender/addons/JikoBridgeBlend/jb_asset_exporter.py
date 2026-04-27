import os

import bpy

from .jb_api import JB_API
from .jb_logger import get_logger

from .scene.jb_scene import JBScene

logger = get_logger(__name__)


class JB_AssetExporter:
    def __init__(self):
        self.api = JB_API()
        self.scene = JBScene()

    def export_asset(self, context=None) -> None:
        asset_container = self.scene.get_selected_asset_container(context)
        if asset_container:
            self._update_asset(asset_container)
        else:
            self._create_new_asset(self.scene.get_selected_objects(context, child=True))

    def _update_asset(self, container) -> None:
        assetInfo = self.scene.get_asset_info(container)
        if not assetInfo:
            logger.error("Invalid asset information on container: %s", container.name)
            return

        if not self.scene.confirm(
            f"Update asset '{assetInfo.asset_name}'?\nThis will overwrite the existing file."
        ):
            return

        objects = self.scene.get_objects_recursive(container)
        if not objects:
            logger.error("Container '%s' has no objects for export.", container.name)
            return

        asset = self.api.get_asset(
            assetInfo.pack_name,
            assetInfo.asset_name,
            assetInfo.database_name,
            assetInfo.asset_type,
        )
        if not asset or not asset.asset_path:
            logger.error(
                "Unable to determine export extension: missing asset_path for '%s'.",
                assetInfo.asset_name,
            )
            return

        ext = os.path.splitext(asset.asset_path)[1]
        if not ext:
            logger.error(
                "Unable to determine export extension from asset_path '%s' for '%s'.",
                asset.asset_path,
                assetInfo.asset_name,
            )
            return

        filepath = self.scene.export_with_temp(container, ext)
        if not filepath:
            return

        if self.api.update_asset(
            filepath,
            asset.pack_name,
            asset.asset_name,
            asset.asset_type,
            asset.database_name,
        ):
            logger.info("Asset '%s' updated successfully.", asset.asset_name)
        else:
            logger.error("Failed to update asset '%s'.", asset.asset_name)

    def _create_new_asset(self, objects: list) -> None:
        if not self.scene.confirm(
            "Create new asset from selected objects? Go to Jiko Bridge app to finish setup."
        ):
            return

        filepath = self.scene.export_with_temp(objects, ".fbx")
        if not filepath:
            logger.error("Export failed.")
            return

        asset = self.api.create_asset(filepath)
        if not asset:
            logger.error("Failed to create asset.")
            return

        container, _ = self.scene.get_or_create_container(asset)
        self.scene.move_objects_to_container(objects, container)
        logger.info("Asset '%s' created.", asset.asset_name)
