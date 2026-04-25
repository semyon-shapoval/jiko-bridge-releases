import os

from jb_api import JB_API
from jb_utils import confirm
from jb_logger import get_logger
from scene.jb_scene import JBScene
from jb_asset_model import AssetFile, AssetFile, AssetInfo

logger = get_logger(__name__)


class JB_AssetExporter:
    def __init__(self):
        self.api = JB_API()
        self.scene = JBScene()

    def export_asset(self) -> None:
        asset_container = self.scene.get_selected_asset_container()
        if asset_container:
            self._update_asset(asset_container)
        else:
            self._create_new_asset(self.scene.get_selection())

    def _update_asset(self, container) -> None:
        assetInfo = AssetInfo.get_asset_info(container)
        if not assetInfo:
            logger.error(
                "Invalid asset information on container: %s", container.GetName()
            )
            return

        if not confirm(
            f"Update asset '{assetInfo.assetName}'?\nThis will overwrite the existing file."
        ):
            return

        objects = self.scene.get_objects_recursive(container)
        if not objects:
            logger.error(
                "Container '%s' has no objects for export.", container.GetName()
            )
            return

        asset = self.api.get_asset(
            assetInfo.packName,
            assetInfo.assetName,
            assetInfo.databaseName,
            [AssetFile(assetType=assetInfo.assetType)],
        )
        if not asset or not asset.files:
            logger.error("Failed to fetch asset '%s'.", assetInfo.assetName)
            return
        
        for file in asset.files:
            ext = os.path.splitext(file.filepath)[1]
            if not ext:
                logger.error(
                    "Unable to determine export extension from filepath '%s' for '%s'.",
                    file.filepath,
                    assetInfo.assetName,
                )
                continue

            filepath = self.scene.export_with_temp(objects, ext)
            if not filepath:
                continue

            if self.api.update_asset(
                asset.packName,
                asset.assetName,
                asset.databaseName,
                [AssetFile(filepath=filepath, assetType=file.assetType)],
            ):
                logger.info("Asset '%s' updated successfully.", assetInfo.assetName)
            else:
                logger.error("Failed to update asset '%s'.", assetInfo.assetName)

    def _create_new_asset(self, objects: list) -> None:
        if not confirm(
            "Create new asset from selected objects? Go to Jiko Bridge app to finish setup."
        ):
            return

        filepath = self.scene.export_with_temp(objects, ".fbx")
        if not filepath:
            logger.error("Export failed.")
            return

        asset = self.api.create_asset([AssetFile(filepath=filepath, assetType=None)])

        if not asset or not asset.files:
            logger.error("No asset found for filepath '%s'", filepath)
            return

        for file in asset.files:
            container, _ = self.scene.get_or_create_asset_container(asset, file)
            self.scene.move_objects_to_container(objects, container)
            logger.info("Asset '%s' created with type '%s'.", asset.assetName, file.assetType)
